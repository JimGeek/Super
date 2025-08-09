"""
Serializers for orders app
"""
from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import (
    Order, OrderItem, OrderStatusHistory, OrderCoupon,
    OrderDocument, OrderTimeline, Subscription
)


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for Order Items"""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'item_type', 'name', 'description', 'sku',
            'unit_price', 'quantity', 'total_price', 'customizations',
            'duration_minutes', 'service_staff', 'item_status'
        ]
        read_only_fields = ['id', 'total_price']
    
    def validate(self, attrs):
        # Calculate total price
        attrs['total_price'] = attrs['unit_price'] * attrs['quantity']
        return attrs


class OrderCouponSerializer(serializers.ModelSerializer):
    """Serializer for Order Coupons"""
    
    class Meta:
        model = OrderCoupon
        fields = [
            'id', 'coupon_code', 'coupon_name', 'discount_type',
            'discount_value', 'discount_amount', 'minimum_order_value',
            'maximum_discount'
        ]
        read_only_fields = ['id', 'discount_amount']


class OrderTimelineSerializer(serializers.ModelSerializer):
    """Serializer for Order Timeline"""
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)
    
    class Meta:
        model = OrderTimeline
        fields = [
            'id', 'event_type', 'title', 'description', 'actor', 'actor_name',
            'location', 'metadata', 'is_customer_visible', 'is_merchant_visible',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OrderDocumentSerializer(serializers.ModelSerializer):
    """Serializer for Order Documents"""
    
    class Meta:
        model = OrderDocument
        fields = [
            'id', 'document_type', 'document_number', 'title',
            'file_url', 'is_customer_visible', 'created_at'
        ]
        read_only_fields = ['id', 'file_url', 'created_at']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for Order Status History"""
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'from_status', 'to_status', 'changed_by', 'changed_by_name',
            'reason', 'notes', 'location', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """Main Order serializer"""
    items = OrderItemSerializer(many=True, read_only=True)
    applied_coupons = OrderCouponSerializer(many=True, read_only=True)
    timeline = OrderTimelineSerializer(many=True, read_only=True)
    documents = OrderDocumentSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    merchant_name = serializers.CharField(source='merchant.name', read_only=True)
    service_staff_name = serializers.CharField(source='service_staff.get_full_name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'vertical', 'order_type', 'status',
            'customer', 'customer_name', 'merchant', 'merchant_name',
            'flow', 'flow_data', 'subtotal', 'tax_amount', 'discount_amount',
            'delivery_fee', 'service_fee', 'total_amount', 'payment_method',
            'payment_status', 'delivery_address', 'billing_address',
            'scheduled_for', 'estimated_completion', 'service_location',
            'service_staff', 'service_staff_name', 'customer_notes',
            'merchant_notes', 'customer_rating', 'customer_review',
            'created_at', 'updated_at', 'placed_at', 'confirmed_at',
            'completed_at', 'items', 'applied_coupons', 'timeline',
            'documents', 'status_history'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at',
            'placed_at', 'confirmed_at', 'completed_at'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    merchant_id = serializers.UUIDField()
    vertical = serializers.ChoiceField(choices=Order.VERTICALS)
    order_type = serializers.ChoiceField(choices=Order.ORDER_TYPES)
    
    # Items
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of order items"
    )
    
    # Addresses
    delivery_address = serializers.JSONField(required=False)
    billing_address = serializers.JSONField(required=False)
    
    # Scheduling
    scheduled_for = serializers.DateTimeField(required=False)
    
    # Payment
    payment_method = serializers.ChoiceField(
        choices=[choice[0] for choice in Order._meta.get_field('payment_method').choices],
        default='prepaid'
    )
    
    # Coupons
    coupon_codes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of coupon codes to apply"
    )
    
    # Notes
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_merchant_id(self, value):
        from accounts.models import Organization
        try:
            Organization.objects.get(id=value, status='active')
            return value
        except Organization.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive merchant")
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")
        
        for item in value:
            required_fields = ['name', 'unit_price', 'quantity']
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(f"Item missing required field: {field}")
                    
            # Validate quantities and prices
            if Decimal(str(item['unit_price'])) <= 0:
                raise serializers.ValidationError("Item unit price must be positive")
            if Decimal(str(item['quantity'])) <= 0:
                raise serializers.ValidationError("Item quantity must be positive")
        
        return value
    
    def validate(self, attrs):
        # Validate delivery address for delivery orders
        if attrs['order_type'] == 'delivery' and not attrs.get('delivery_address'):
            raise serializers.ValidationError("Delivery address is required for delivery orders")
        
        # Validate scheduling for appointment-based orders
        if attrs['order_type'] in ['at_home_service', 'in_store_appointment']:
            if not attrs.get('scheduled_for'):
                raise serializers.ValidationError("Scheduled time is required for service orders")
            if attrs.get('scheduled_for') <= timezone.now():
                raise serializers.ValidationError("Scheduled time must be in the future")
        
        return attrs


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders"""
    
    class Meta:
        model = Order
        fields = [
            'status', 'scheduled_for', 'estimated_completion',
            'service_staff', 'merchant_notes', 'internal_notes'
        ]
    
    def validate_status(self, value):
        instance = self.instance
        if instance and instance.status == 'cancelled':
            raise serializers.ValidationError("Cannot update cancelled order")
        return value


class OrderRatingSerializer(serializers.Serializer):
    """Serializer for order rating and review"""
    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscriptions"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    merchant_name = serializers.CharField(source='merchant.name', read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'subscription_number', 'customer', 'customer_name',
            'merchant', 'merchant_name', 'template_order', 'frequency',
            'frequency_count', 'start_date', 'end_date', 'next_order_date',
            'status', 'mandate', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'subscription_number', 'created_at', 'updated_at'
        ]


class SubscriptionCreateSerializer(serializers.Serializer):
    """Serializer for creating subscriptions"""
    template_order_id = serializers.UUIDField()
    frequency = serializers.ChoiceField(choices=Subscription.FREQUENCY_CHOICES)
    frequency_count = serializers.IntegerField(min_value=1, default=1)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False)
    
    def validate_template_order_id(self, value):
        try:
            Order.objects.get(id=value, status='completed')
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Template order must exist and be completed")
    
    def validate(self, attrs):
        if attrs.get('end_date') and attrs['end_date'] <= attrs['start_date']:
            raise serializers.ValidationError("End date must be after start date")
        return attrs


class OrderSummarySerializer(serializers.Serializer):
    """Serializer for order summary/statistics"""
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderSearchSerializer(serializers.Serializer):
    """Serializer for order search parameters"""
    q = serializers.CharField(required=False, help_text="Search query")
    status = serializers.MultipleChoiceField(
        choices=Order.ORDER_STATUS,
        required=False,
        help_text="Filter by status"
    )
    vertical = serializers.MultipleChoiceField(
        choices=Order.VERTICALS,
        required=False,
        help_text="Filter by vertical"
    )
    order_type = serializers.MultipleChoiceField(
        choices=Order.ORDER_TYPES,
        required=False,
        help_text="Filter by order type"
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    min_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)