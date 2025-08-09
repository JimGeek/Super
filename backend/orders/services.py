"""
Order management services and business logic
"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import (
    Order, OrderItem, OrderStatusHistory, OrderCoupon,
    OrderTimeline, Subscription
)
from accounts.models import Organization
from settlements.models import LedgerAccount, LedgerEntry

User = get_user_model()


class OrderService:
    """Main service for order management"""
    
    def __init__(self):
        self.tax_rate = Decimal('0.18')  # 18% GST
    
    @transaction.atomic
    def create_order(self, customer, order_data):
        """Create a new order"""
        
        # Get merchant
        merchant = Organization.objects.get(id=order_data['merchant_id'])
        
        # Generate order number
        order_number = self._generate_order_number(merchant)
        
        # Calculate pricing
        items_data = order_data['items']
        subtotal = self._calculate_subtotal(items_data)
        
        # Apply coupons if provided
        discount_amount = Decimal('0.00')
        applied_coupons = []
        
        if 'coupon_codes' in order_data and order_data['coupon_codes']:
            discount_result = self._apply_coupons(
                merchant, 
                order_data['coupon_codes'], 
                subtotal
            )
            discount_amount = discount_result['total_discount']
            applied_coupons = discount_result['applied_coupons']
        
        # Calculate delivery/service fee
        delivery_fee = self._calculate_delivery_fee(
            merchant, 
            order_data['order_type'],
            order_data.get('delivery_address')
        )
        
        # Calculate tax
        taxable_amount = subtotal - discount_amount + delivery_fee
        tax_amount = taxable_amount * self.tax_rate
        
        # Calculate total
        total_amount = subtotal - discount_amount + delivery_fee + tax_amount
        
        # Create order
        order = Order.objects.create(
            order_number=order_number,
            customer=customer,
            merchant=merchant,
            vertical=order_data['vertical'],
            order_type=order_data['order_type'],
            subtotal=subtotal,
            discount_amount=discount_amount,
            delivery_fee=delivery_fee,
            tax_amount=tax_amount,
            total_amount=total_amount,
            payment_method=order_data.get('payment_method', 'prepaid'),
            delivery_address=order_data.get('delivery_address'),
            billing_address=order_data.get('billing_address'),
            scheduled_for=order_data.get('scheduled_for'),
            customer_notes=order_data.get('customer_notes', ''),
            flow_data=order_data.get('flow_data', {})
        )
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(
                order=order,
                item_type=item_data.get('item_type', 'product'),
                name=item_data['name'],
                description=item_data.get('description', ''),
                sku=item_data.get('sku', ''),
                unit_price=Decimal(str(item_data['unit_price'])),
                quantity=Decimal(str(item_data['quantity'])),
                total_price=Decimal(str(item_data['unit_price'])) * Decimal(str(item_data['quantity'])),
                customizations=item_data.get('customizations', {}),
                duration_minutes=item_data.get('duration_minutes')
            )
        
        # Apply coupons
        for coupon_data in applied_coupons:
            OrderCoupon.objects.create(
                order=order,
                **coupon_data
            )
        
        # Create initial timeline event
        OrderTimeline.objects.create(
            order=order,
            event_type='order_placed',
            title='Order Placed',
            description=f'Order placed by {customer.get_full_name()}',
            actor=customer,
            is_customer_visible=True,
            is_merchant_visible=True
        )
        
        return order
    
    @transaction.atomic
    def update_order_status(self, order_id, new_status, user=None, reason='', notes='', location=None):
        """Update order status with proper tracking"""
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise ValueError("Order not found")
        
        old_status = order.status
        
        # Validate status transition
        if not self._is_valid_status_transition(old_status, new_status):
            raise ValueError(f"Invalid status transition from {old_status} to {new_status}")
        
        # Update order
        order.status = new_status
        
        # Update timing fields
        if new_status == 'placed':
            order.placed_at = timezone.now()
        elif new_status == 'confirmed':
            order.confirmed_at = timezone.now()
        elif new_status in ['completed', 'delivered']:
            order.completed_at = timezone.now()
        
        order.save()
        
        # Record status history
        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            reason=reason,
            notes=notes,
            location=location
        )
        
        # Create timeline event
        timeline_event = self._get_timeline_event_for_status(new_status)
        if timeline_event:
            OrderTimeline.objects.create(
                order=order,
                event_type=timeline_event['event_type'],
                title=timeline_event['title'],
                description=timeline_event['description'],
                actor=user,
                location=location,
                is_customer_visible=timeline_event.get('customer_visible', True),
                is_merchant_visible=timeline_event.get('merchant_visible', True)
            )
        
        # Trigger side effects
        self._handle_status_change_effects(order, old_status, new_status)
        
        return order
    
    def calculate_order_totals(self, items, coupons=None, delivery_address=None, merchant=None):
        """Calculate order totals without creating the order"""
        
        subtotal = sum(
            Decimal(str(item['unit_price'])) * Decimal(str(item['quantity']))
            for item in items
        )
        
        # Apply coupons
        discount_amount = Decimal('0.00')
        if coupons and merchant:
            discount_result = self._apply_coupons(merchant, coupons, subtotal)
            discount_amount = discount_result['total_discount']
        
        # Calculate delivery fee
        delivery_fee = Decimal('0.00')
        if merchant and delivery_address:
            delivery_fee = self._calculate_delivery_fee(
                merchant, 
                'delivery', 
                delivery_address
            )
        
        # Calculate tax
        taxable_amount = subtotal - discount_amount + delivery_fee
        tax_amount = taxable_amount * self.tax_rate
        
        # Calculate total
        total_amount = subtotal - discount_amount + delivery_fee + tax_amount
        
        return {
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'delivery_fee': delivery_fee,
            'tax_amount': tax_amount,
            'total_amount': total_amount
        }
    
    @transaction.atomic
    def cancel_order(self, order_id, user, reason):
        """Cancel an order"""
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise ValueError("Order not found")
        
        if order.status in ['completed', 'delivered', 'cancelled']:
            raise ValueError("Cannot cancel order in current status")
        
        # Update order status
        self.update_order_status(
            order_id, 
            'cancelled', 
            user=user, 
            reason=reason
        )
        
        # Handle refunds if payment was made
        if order.payment_status == 'paid':
            self._initiate_refund(order, user)
        
        return order
    
    def create_subscription(self, customer, subscription_data):
        """Create a recurring subscription"""
        
        template_order = Order.objects.get(id=subscription_data['template_order_id'])
        
        if template_order.customer != customer:
            raise ValueError("Template order must belong to the customer")
        
        # Generate subscription number
        subscription_number = f"SUB_{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate next order date
        next_order_date = subscription_data['start_date']
        
        subscription = Subscription.objects.create(
            subscription_number=subscription_number,
            customer=customer,
            merchant=template_order.merchant,
            template_order=template_order,
            frequency=subscription_data['frequency'],
            frequency_count=subscription_data.get('frequency_count', 1),
            start_date=subscription_data['start_date'],
            end_date=subscription_data.get('end_date'),
            next_order_date=next_order_date
        )
        
        return subscription
    
    def _generate_order_number(self, merchant):
        """Generate unique order number"""
        today = timezone.now().strftime('%Y%m%d')
        prefix = merchant.business_type[:3].upper()
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"{prefix}{today}{unique_id}"
    
    def _calculate_subtotal(self, items):
        """Calculate order subtotal"""
        return sum(
            Decimal(str(item['unit_price'])) * Decimal(str(item['quantity']))
            for item in items
        )
    
    def _calculate_delivery_fee(self, merchant, order_type, delivery_address=None):
        """Calculate delivery fee based on distance and merchant settings"""
        
        if order_type != 'delivery':
            return Decimal('0.00')
        
        # Basic delivery fee calculation
        # In production, this would use actual distance calculation
        base_fee = Decimal('30.00')  # ₹30 base delivery fee
        
        # Get merchant's delivery radius and fees from settings
        # This would be more sophisticated in production
        
        return base_fee
    
    def _apply_coupons(self, merchant, coupon_codes, subtotal):
        """Apply coupons and calculate discount"""
        
        # Placeholder coupon logic
        # In production, this would validate against a coupons database
        
        total_discount = Decimal('0.00')
        applied_coupons = []
        
        for code in coupon_codes:
            # Mock coupon validation
            if code == 'SAVE10':
                discount_amount = subtotal * Decimal('0.10')  # 10% discount
                applied_coupons.append({
                    'coupon_code': code,
                    'coupon_name': 'Save 10%',
                    'discount_type': 'percentage',
                    'discount_value': Decimal('10.00'),
                    'discount_amount': discount_amount
                })
                total_discount += discount_amount
            elif code == 'FLAT50':
                discount_amount = min(Decimal('50.00'), subtotal)
                applied_coupons.append({
                    'coupon_code': code,
                    'coupon_name': 'Flat ₹50 Off',
                    'discount_type': 'fixed',
                    'discount_value': Decimal('50.00'),
                    'discount_amount': discount_amount
                })
                total_discount += discount_amount
        
        return {
            'total_discount': total_discount,
            'applied_coupons': applied_coupons
        }
    
    def _is_valid_status_transition(self, from_status, to_status):
        """Validate if status transition is allowed"""
        
        valid_transitions = {
            'draft': ['placed', 'cancelled'],
            'placed': ['confirmed', 'cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['ready', 'cancelled'],
            'ready': ['picked_up', 'delivered', 'cancelled'],
            'picked_up': ['in_transit', 'delivered'],
            'in_transit': ['delivered'],
            'delivered': ['completed'],
            'completed': [],
            'cancelled': [],
            'refunded': []
        }
        
        return to_status in valid_transitions.get(from_status, [])
    
    def _get_timeline_event_for_status(self, status):
        """Get timeline event configuration for status"""
        
        events = {
            'placed': {
                'event_type': 'order_placed',
                'title': 'Order Placed',
                'description': 'Your order has been placed successfully'
            },
            'confirmed': {
                'event_type': 'order_confirmed',
                'title': 'Order Confirmed',
                'description': 'Your order has been confirmed by the merchant'
            },
            'preparing': {
                'event_type': 'preparing_started',
                'title': 'Preparation Started',
                'description': 'Your order is being prepared'
            },
            'ready': {
                'event_type': 'ready_for_pickup',
                'title': 'Ready for Pickup',
                'description': 'Your order is ready for pickup'
            },
            'picked_up': {
                'event_type': 'pickup_completed',
                'title': 'Picked Up',
                'description': 'Your order has been picked up by our delivery partner'
            },
            'in_transit': {
                'event_type': 'in_transit',
                'title': 'In Transit',
                'description': 'Your order is on the way'
            },
            'delivered': {
                'event_type': 'delivered',
                'title': 'Delivered',
                'description': 'Your order has been delivered'
            },
            'completed': {
                'event_type': 'service_completed',
                'title': 'Service Completed',
                'description': 'Your service has been completed'
            },
            'cancelled': {
                'event_type': 'order_cancelled',
                'title': 'Order Cancelled',
                'description': 'Your order has been cancelled'
            }
        }
        
        return events.get(status)
    
    def _handle_status_change_effects(self, order, old_status, new_status):
        """Handle side effects of status changes"""
        
        if new_status == 'confirmed':
            # Reserve inventory, create ledger entries, etc.
            self._handle_order_confirmation(order)
        
        elif new_status == 'delivered' or new_status == 'completed':
            # Update payment status, create settlement entries
            self._handle_order_completion(order)
        
        elif new_status == 'cancelled':
            # Release inventory, handle refunds
            self._handle_order_cancellation(order)
    
    def _handle_order_confirmation(self, order):
        """Handle order confirmation effects"""
        # Reserve inventory, notify merchant, etc.
        pass
    
    def _handle_order_completion(self, order):
        """Handle order completion effects"""
        # Create ledger entries for settlement
        # This would integrate with the settlements app
        pass
    
    def _handle_order_cancellation(self, order):
        """Handle order cancellation effects"""
        # Release reservations, process refunds
        pass
    
    def _initiate_refund(self, order, user):
        """Initiate refund for cancelled order"""
        from payments_upi.services import UPIPaymentService
        
        # Get the original payment transaction
        payment_transaction = order.upi_transactions.filter(
            status='success',
            transaction_type='payment'
        ).first()
        
        if payment_transaction:
            try:
                upi_service = UPIPaymentService()
                upi_service.initiate_refund(
                    transaction_id=payment_transaction.id,
                    refund_amount=order.total_amount,
                    reason="Order cancellation"
                )
                
                # Update payment status
                order.payment_status = 'refunded'
                order.save()
                
                # Add timeline event
                OrderTimeline.objects.create(
                    order=order,
                    event_type='refund_initiated',
                    title='Refund Initiated',
                    description='Refund has been initiated for your cancelled order',
                    actor=user,
                    is_customer_visible=True,
                    is_merchant_visible=True
                )
                
            except Exception as e:
                # Handle refund failure
                pass


class OrderAnalyticsService:
    """Service for order analytics and reporting"""
    
    def get_order_summary(self, merchant=None, customer=None, date_from=None, date_to=None):
        """Get order summary statistics"""
        
        queryset = Order.objects.all()
        
        if merchant:
            queryset = queryset.filter(merchant=merchant)
        if customer:
            queryset = queryset.filter(customer=customer)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lt=date_to)
        
        from django.db.models import Count, Sum, Avg
        
        summary = queryset.aggregate(
            total_orders=Count('id'),
            pending_orders=Count('id', filter=models.Q(status__in=['placed', 'confirmed', 'preparing'])),
            completed_orders=Count('id', filter=models.Q(status__in=['completed', 'delivered'])),
            cancelled_orders=Count('id', filter=models.Q(status='cancelled')),
            total_revenue=Sum('total_amount', filter=models.Q(status__in=['completed', 'delivered'])),
            average_order_value=Avg('total_amount')
        )
        
        # Handle None values
        for key, value in summary.items():
            if value is None:
                summary[key] = 0 if 'revenue' in key or 'value' in key else 0
        
        return summary
    
    def get_popular_items(self, merchant=None, limit=10):
        """Get popular items by quantity sold"""
        
        from django.db.models import Sum
        
        queryset = OrderItem.objects.select_related('order')
        
        if merchant:
            queryset = queryset.filter(order__merchant=merchant)
        
        queryset = queryset.filter(
            order__status__in=['completed', 'delivered']
        )
        
        popular_items = queryset.values('name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_quantity')[:limit]
        
        return list(popular_items)