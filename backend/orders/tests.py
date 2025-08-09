"""
Comprehensive tests for orders app
"""
import json
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, Mock

from accounts.models import Organization
from .models import (
    Order, OrderItem, OrderStatusHistory, OrderCoupon,
    OrderTimeline, Subscription
)
from .services import OrderService, OrderAnalyticsService

User = get_user_model()


class OrderModelTests(TestCase):
    """Test order models"""
    
    def setUp(self):
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Restaurant",
            business_type="restaurant",
            email="restaurant@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        # Create test users
        self.customer = User.objects.create_user(
            email="customer@test.com",
            phone="+919876543211",
            first_name="Test",
            last_name="Customer",
            password="testpass123"
        )
        
        self.merchant_owner = User.objects.create_user(
            email="owner@test.com",
            phone="+919876543212",
            first_name="Merchant",
            last_name="Owner",
            password="testpass123",
            organization=self.organization,
            role="merchant_owner"
        )
    
    def test_order_creation(self):
        """Test order model creation"""
        order = Order.objects.create(
            order_number="REST20241201ABC123",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="delivery",
            subtotal=Decimal('150.00'),
            tax_amount=Decimal('27.00'),
            total_amount=Decimal('177.00'),
            delivery_address={'address': 'Test Delivery Address'},
            scheduled_for=timezone.now() + timedelta(hours=1)
        )
        
        self.assertEqual(str(order), f"Order {order.order_number} - {self.organization.name}")
        self.assertEqual(order.status, 'draft')
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.vertical, 'restaurant')
        self.assertEqual(order.order_type, 'delivery')
    
    def test_order_item_creation(self):
        """Test order item model"""
        order = Order.objects.create(
            order_number="REST20241201ABC123",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="delivery",
            subtotal=Decimal('100.00'),
            total_amount=Decimal('118.00')
        )
        
        item = OrderItem.objects.create(
            order=order,
            name="Margherita Pizza",
            description="Classic tomato and mozzarella pizza",
            unit_price=Decimal('250.00'),
            quantity=Decimal('2.000'),
            total_price=Decimal('500.00'),
            customizations={'size': 'large', 'extra_cheese': True}
        )
        
        self.assertEqual(str(item), "Margherita Pizza x 2.000")
        self.assertEqual(item.item_type, 'product')
        self.assertEqual(item.total_price, Decimal('500.00'))
    
    def test_order_timeline_creation(self):
        """Test order timeline tracking"""
        order = Order.objects.create(
            order_number="REST20241201ABC123",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="delivery",
            subtotal=Decimal('100.00'),
            total_amount=Decimal('118.00')
        )
        
        timeline = OrderTimeline.objects.create(
            order=order,
            event_type='order_placed',
            title='Order Placed',
            description='Order placed by customer',
            actor=self.customer,
            metadata={'location': 'Mumbai'}
        )
        
        self.assertEqual(str(timeline), f"{order.order_number}: order_placed")
        self.assertTrue(timeline.is_customer_visible)
        self.assertTrue(timeline.is_merchant_visible)
    
    def test_subscription_creation(self):
        """Test subscription model"""
        # Create template order
        template_order = Order.objects.create(
            order_number="TEMPLATE123",
            customer=self.customer,
            merchant=self.organization,
            vertical="kirana",
            order_type="delivery",
            subtotal=Decimal('500.00'),
            total_amount=Decimal('590.00'),
            status='completed'
        )
        
        subscription = Subscription.objects.create(
            subscription_number="SUB12345",
            customer=self.customer,
            merchant=self.organization,
            template_order=template_order,
            frequency='weekly',
            frequency_count=1,
            start_date=timezone.now().date(),
            next_order_date=timezone.now().date() + timedelta(days=7)
        )
        
        self.assertEqual(str(subscription), f"Subscription {subscription.subscription_number} - {self.customer.get_full_name()}")
        self.assertEqual(subscription.status, 'active')


class OrderServiceTests(TestCase):
    """Test order service layer"""
    
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Kirana",
            business_type="kirana",
            email="kirana@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        self.customer = User.objects.create_user(
            email="customer@test.com",
            phone="+919876543211",
            first_name="Test",
            last_name="Customer",
            password="testpass123"
        )
        
        self.service = OrderService()
    
    def test_create_order(self):
        """Test order creation service"""
        order_data = {
            'merchant_id': self.organization.id,
            'vertical': 'kirana',
            'order_type': 'delivery',
            'items': [
                {
                    'name': 'Rice',
                    'description': '1kg Basmati Rice',
                    'unit_price': '100.00',
                    'quantity': '2'
                },
                {
                    'name': 'Dal',
                    'description': '500g Toor Dal',
                    'unit_price': '80.00',
                    'quantity': '1'
                }
            ],
            'delivery_address': {
                'address_line1': 'Test Delivery Address',
                'city': 'Mumbai',
                'pincode': '400001'
            },
            'customer_notes': 'Please call before delivery'
        }
        
        order = self.service.create_order(self.customer, order_data)
        
        self.assertIsNotNone(order.id)
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.merchant, self.organization)
        self.assertEqual(order.vertical, 'kirana')
        self.assertEqual(order.order_type, 'delivery')
        self.assertEqual(order.subtotal, Decimal('280.00'))  # 200 + 80
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.timeline.count(), 1)  # order_placed event
        
        # Check items
        rice_item = order.items.get(name='Rice')
        self.assertEqual(rice_item.quantity, Decimal('2.000'))
        self.assertEqual(rice_item.total_price, Decimal('200.00'))
    
    def test_create_order_with_coupons(self):
        """Test order creation with coupon application"""
        order_data = {
            'merchant_id': self.organization.id,
            'vertical': 'kirana',
            'order_type': 'delivery',
            'items': [
                {
                    'name': 'Rice',
                    'unit_price': '200.00',
                    'quantity': '1'
                }
            ],
            'coupon_codes': ['SAVE10'],
            'delivery_address': {
                'address_line1': 'Test Address',
                'city': 'Mumbai'
            }
        }
        
        order = self.service.create_order(self.customer, order_data)
        
        self.assertEqual(order.discount_amount, Decimal('20.00'))  # 10% of 200
        self.assertEqual(order.applied_coupons.count(), 1)
        
        coupon = order.applied_coupons.first()
        self.assertEqual(coupon.coupon_code, 'SAVE10')
        self.assertEqual(coupon.discount_amount, Decimal('20.00'))
    
    def test_update_order_status(self):
        """Test order status updates"""
        # Create order
        order_data = {
            'merchant_id': self.organization.id,
            'vertical': 'kirana',
            'order_type': 'delivery',
            'items': [{'name': 'Test Item', 'unit_price': '100.00', 'quantity': '1'}],
            'delivery_address': {'address_line1': 'Test Address'}
        }
        
        order = self.service.create_order(self.customer, order_data)
        
        # Update to placed
        updated_order = self.service.update_order_status(
            order.id,
            'placed',
            user=self.customer,
            reason='Customer placed order'
        )
        
        self.assertEqual(updated_order.status, 'placed')
        self.assertIsNotNone(updated_order.placed_at)
        self.assertEqual(updated_order.status_history.count(), 1)
        
        # Check timeline event was created
        timeline_events = updated_order.timeline.filter(event_type='order_placed')
        self.assertEqual(timeline_events.count(), 2)  # Initial + status change
    
    def test_invalid_status_transition(self):
        """Test invalid status transitions are rejected"""
        order_data = {
            'merchant_id': self.organization.id,
            'vertical': 'kirana',
            'order_type': 'delivery',
            'items': [{'name': 'Test Item', 'unit_price': '100.00', 'quantity': '1'}]
        }
        
        order = self.service.create_order(self.customer, order_data)
        
        # Try invalid transition from draft to delivered
        with self.assertRaises(ValueError):
            self.service.update_order_status(order.id, 'delivered')
    
    def test_calculate_order_totals(self):
        """Test order total calculations"""
        items = [
            {'unit_price': '100.00', 'quantity': '2'},
            {'unit_price': '50.00', 'quantity': '1'}
        ]
        
        totals = self.service.calculate_order_totals(
            items,
            coupons=['FLAT50'],
            merchant=self.organization
        )
        
        self.assertEqual(totals['subtotal'], Decimal('250.00'))
        self.assertEqual(totals['discount_amount'], Decimal('50.00'))
        self.assertTrue(totals['tax_amount'] > 0)
        self.assertTrue(totals['total_amount'] > 0)
    
    def test_cancel_order(self):
        """Test order cancellation"""
        order_data = {
            'merchant_id': self.organization.id,
            'vertical': 'kirana',
            'order_type': 'delivery',
            'items': [{'name': 'Test Item', 'unit_price': '100.00', 'quantity': '1'}]
        }
        
        order = self.service.create_order(self.customer, order_data)
        
        # Place the order first
        self.service.update_order_status(order.id, 'placed')
        
        # Cancel the order
        cancelled_order = self.service.cancel_order(
            order.id,
            self.customer,
            "Customer requested cancellation"
        )
        
        self.assertEqual(cancelled_order.status, 'cancelled')
        
        # Check timeline event
        cancel_events = cancelled_order.timeline.filter(event_type='order_cancelled')
        self.assertEqual(cancel_events.count(), 1)
    
    def test_create_subscription(self):
        """Test subscription creation"""
        # Create completed order first
        order_data = {
            'merchant_id': self.organization.id,
            'vertical': 'kirana',
            'order_type': 'delivery',
            'items': [{'name': 'Weekly Groceries', 'unit_price': '500.00', 'quantity': '1'}]
        }
        
        template_order = self.service.create_order(self.customer, order_data)
        template_order.status = 'completed'
        template_order.save()
        
        subscription_data = {
            'template_order_id': template_order.id,
            'frequency': 'weekly',
            'frequency_count': 1,
            'start_date': timezone.now().date()
        }
        
        subscription = self.service.create_subscription(self.customer, subscription_data)
        
        self.assertIsNotNone(subscription.subscription_number)
        self.assertEqual(subscription.customer, self.customer)
        self.assertEqual(subscription.merchant, self.organization)
        self.assertEqual(subscription.frequency, 'weekly')
        self.assertEqual(subscription.status, 'active')


class OrderAnalyticsServiceTests(TestCase):
    """Test order analytics service"""
    
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Store",
            business_type="kirana",
            email="store@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        self.customer = User.objects.create_user(
            email="customer@test.com",
            phone="+919876543211",
            first_name="Test",
            last_name="Customer",
            password="testpass123"
        )
        
        self.analytics_service = OrderAnalyticsService()
    
    def test_order_summary(self):
        """Test order summary statistics"""
        # Create test orders
        Order.objects.create(
            order_number="ORD001",
            customer=self.customer,
            merchant=self.organization,
            vertical="kirana",
            order_type="delivery",
            subtotal=Decimal('100.00'),
            total_amount=Decimal('118.00'),
            status='completed'
        )
        
        Order.objects.create(
            order_number="ORD002",
            customer=self.customer,
            merchant=self.organization,
            vertical="kirana",
            order_type="delivery",
            subtotal=Decimal('200.00'),
            total_amount=Decimal('236.00'),
            status='placed'
        )
        
        Order.objects.create(
            order_number="ORD003",
            customer=self.customer,
            merchant=self.organization,
            vertical="kirana",
            order_type="delivery",
            subtotal=Decimal('150.00'),
            total_amount=Decimal('177.00'),
            status='cancelled'
        )
        
        summary = self.analytics_service.get_order_summary(merchant=self.organization)
        
        self.assertEqual(summary['total_orders'], 3)
        self.assertEqual(summary['completed_orders'], 1)
        self.assertEqual(summary['pending_orders'], 1)
        self.assertEqual(summary['cancelled_orders'], 1)
        self.assertEqual(summary['total_revenue'], Decimal('118.00'))


class OrderAPITests(APITestCase):
    """Test order API endpoints"""
    
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Restaurant",
            business_type="restaurant",
            email="restaurant@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            status="active"
        )
        
        self.customer = User.objects.create_user(
            email="customer@test.com",
            phone="+919876543211",
            first_name="Test",
            last_name="Customer",
            password="testpass123"
        )
        
        self.merchant_owner = User.objects.create_user(
            email="owner@test.com",
            phone="+919876543212",
            first_name="Merchant",
            last_name="Owner",
            password="testpass123",
            organization=self.organization,
            role="merchant_owner"
        )
        
        self.client = APIClient()
    
    def test_create_order_api(self):
        """Test order creation via API"""
        self.client.force_authenticate(user=self.customer)
        
        url = '/api/v1/orders/'
        data = {
            'merchant_id': str(self.organization.id),
            'vertical': 'restaurant',
            'order_type': 'delivery',
            'items': [
                {
                    'name': 'Margherita Pizza',
                    'unit_price': '299.00',
                    'quantity': '1'
                },
                {
                    'name': 'Garlic Bread',
                    'unit_price': '99.00',
                    'quantity': '2'
                }
            ],
            'delivery_address': {
                'address_line1': '123 Test Street',
                'city': 'Mumbai',
                'pincode': '400001'
            },
            'customer_notes': 'Please ring the bell'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIn('order_number', response.data)
        self.assertEqual(response.data['vertical'], 'restaurant')
        self.assertEqual(response.data['order_type'], 'delivery')
        self.assertEqual(len(response.data['items']), 2)
    
    def test_create_order_validation_errors(self):
        """Test order creation validation"""
        self.client.force_authenticate(user=self.customer)
        
        url = '/api/v1/orders/'
        
        # Missing required fields
        data = {
            'merchant_id': str(self.organization.id),
            'vertical': 'restaurant'
            # Missing items and order_type
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('items', response.data)
        self.assertIn('order_type', response.data)
    
    def test_update_order_status(self):
        """Test order status update via API"""
        # Create order as customer
        self.client.force_authenticate(user=self.customer)
        
        order = Order.objects.create(
            order_number="REST20241201ABC123",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="delivery",
            subtotal=Decimal('100.00'),
            total_amount=Decimal('118.00')
        )
        
        # Switch to merchant to update status
        self.client.force_authenticate(user=self.merchant_owner)
        
        url = f'/api/v1/orders/{order.id}/update_status/'
        data = {
            'status': 'confirmed',
            'merchant_notes': 'Order confirmed, will be ready in 30 minutes'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'confirmed')
        
        # Verify order was updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')
        self.assertIsNotNone(order.confirmed_at)
    
    def test_order_list_filtering(self):
        """Test order list with filtering"""
        self.client.force_authenticate(user=self.customer)
        
        # Create test orders
        Order.objects.create(
            order_number="ORD001",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="delivery",
            subtotal=Decimal('100.00'),
            total_amount=Decimal('118.00'),
            status='completed'
        )
        
        Order.objects.create(
            order_number="ORD002",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="pickup",
            subtotal=Decimal('200.00'),
            total_amount=Decimal('236.00'),
            status='placed'
        )
        
        # Test status filtering
        url = '/api/v1/orders/?status=completed'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'completed')
        
        # Test order type filtering
        url = '/api/v1/orders/?order_type=pickup'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['order_type'], 'pickup')
    
    def test_order_rating(self):
        """Test order rating and review"""
        self.client.force_authenticate(user=self.customer)
        
        order = Order.objects.create(
            order_number="ORD001",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="delivery",
            subtotal=Decimal('100.00'),
            total_amount=Decimal('118.00'),
            status='completed'
        )
        
        url = f'/api/v1/orders/{order.id}/rate/'
        data = {
            'rating': 5,
            'review': 'Excellent food and quick delivery!'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify rating was saved
        order.refresh_from_db()
        self.assertEqual(order.customer_rating, 5)
        self.assertEqual(order.customer_review, 'Excellent food and quick delivery!')
    
    def test_order_summary_api(self):
        """Test order summary endpoint"""
        self.client.force_authenticate(user=self.merchant_owner)
        
        # Create test orders
        Order.objects.create(
            order_number="ORD001",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="delivery",
            subtotal=Decimal('100.00'),
            total_amount=Decimal('118.00'),
            status='completed'
        )
        
        Order.objects.create(
            order_number="ORD002",
            customer=self.customer,
            merchant=self.organization,
            vertical="restaurant",
            order_type="delivery",
            subtotal=Decimal('200.00'),
            total_amount=Decimal('236.00'),
            status='placed'
        )
        
        url = '/api/v1/orders/summary/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_orders', response.data)
        self.assertIn('completed_orders', response.data)
        self.assertIn('total_revenue', response.data)
        self.assertEqual(response.data['total_orders'], 2)
        self.assertEqual(response.data['completed_orders'], 1)


if __name__ == '__main__':
    import unittest
    unittest.main()