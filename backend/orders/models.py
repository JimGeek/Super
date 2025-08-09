"""
Order management models for SUPER platform
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
from decimal import Decimal

User = get_user_model()


class Order(models.Model):
    """
    Main order model for all verticals
    """
    ORDER_TYPES = [
        ('delivery', 'Delivery'),
        ('pickup', 'Pickup'),
        ('at_home_service', 'At-Home Service'),
        ('in_store_appointment', 'In-Store Appointment'),
    ]
    
    ORDER_STATUS = [
        ('draft', 'Draft'),
        ('placed', 'Placed'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    VERTICALS = [
        ('kirana', 'Kirana Store'),
        ('barber', 'Barber/Salon'),
        ('garage', 'Auto Service'),
        ('water_purifier', 'Water Purifier'),
        ('pharmacy', 'Pharmacy'),
        ('restaurant', 'Restaurant'),
        ('grocery', 'Grocery'),
        ('electronics', 'Electronics'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Order Details
    order_number = models.CharField(max_length=50, unique=True)
    vertical = models.CharField(max_length=20, choices=VERTICALS)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='draft')
    
    # Associated Entities
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='orders'
    )
    merchant = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    
    # Flow Configuration
    flow = models.ForeignKey(
        'flows.Flow',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='orders'
    )
    flow_data = models.JSONField(default=dict, help_text="Flow-specific data")
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('prepaid', 'Prepaid'),
            ('cod', 'Cash on Delivery'),
            ('postpaid', 'Pay After Service'),
        ],
        default='prepaid'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('partial', 'Partially Paid'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    
    # Addresses
    delivery_address = models.JSONField(blank=True, null=True)
    billing_address = models.JSONField(blank=True, null=True)
    
    # Scheduling
    scheduled_for = models.DateTimeField(blank=True, null=True)
    estimated_completion = models.DateTimeField(blank=True, null=True)
    
    # Service Details (for service-based verticals)
    service_location = gis_models.PointField(blank=True, null=True)
    service_staff = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='assigned_orders'
    )
    
    # Special Instructions
    customer_notes = models.TextField(blank=True)
    merchant_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    # Ratings & Reviews
    customer_rating = models.IntegerField(blank=True, null=True)
    customer_review = models.TextField(blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    placed_at = models.DateTimeField(blank=True, null=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['vertical', 'status']),
            models.Index(fields=['order_type', 'scheduled_for']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.merchant.name}"


class OrderItem(models.Model):
    """
    Items within an order
    """
    ITEM_TYPES = [
        ('product', 'Product'),
        ('service', 'Service'),
        ('addon', 'Add-on'),
        ('combo', 'Combo'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Item Details
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='product')
    catalog_item = models.ForeignKey(
        'catalog.CatalogItem',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='order_items'
    )
    
    # Item Info (stored separately for consistency)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, blank=True)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('1.000'))
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Customizations
    customizations = models.JSONField(
        default=dict, 
        help_text="Item-specific customizations (size, color, etc.)"
    )
    
    # Service-specific fields
    duration_minutes = models.IntegerField(blank=True, null=True)
    service_staff = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='service_items'
    )
    
    # Status tracking
    item_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('preparing', 'Preparing'),
            ('ready', 'Ready'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_items'
    
    def __str__(self):
        return f"{self.name} x {self.quantity}"


class OrderStatusHistory(models.Model):
    """
    Track order status changes
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='order_status_changes'
    )
    
    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    # Location tracking
    location = gis_models.PointField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order.order_number}: {self.from_status} → {self.to_status}"


class OrderCoupon(models.Model):
    """
    Coupons applied to orders
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='applied_coupons')
    
    # Coupon Details
    coupon_code = models.CharField(max_length=50)
    coupon_name = models.CharField(max_length=255)
    
    # Discount
    discount_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', 'Percentage'),
            ('fixed', 'Fixed Amount'),
        ]
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Constraints
    minimum_order_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    maximum_discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    
    applied_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_coupons'
    
    def __str__(self):
        return f"{self.coupon_code} - ₹{self.discount_amount}"


class OrderDocument(models.Model):
    """
    Documents related to orders (invoices, warranties, etc.)
    """
    DOCUMENT_TYPES = [
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('warranty_card', 'Warranty Card'),
        ('service_report', 'Service Report'),
        ('prescription', 'Prescription'),
        ('estimate', 'Estimate'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='documents')
    
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=100, blank=True)
    
    title = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_url = models.URLField()
    
    # Metadata
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='generated_documents'
    )
    
    is_customer_visible = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_documents'
    
    def __str__(self):
        return f"{self.document_type} - {self.order.order_number}"


class OrderTimeline(models.Model):
    """
    Timeline events for orders
    """
    EVENT_TYPES = [
        ('order_placed', 'Order Placed'),
        ('payment_received', 'Payment Received'),
        ('order_confirmed', 'Order Confirmed'),
        ('preparing_started', 'Preparation Started'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('rider_assigned', 'Rider Assigned'),
        ('pickup_completed', 'Pickup Completed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('service_started', 'Service Started'),
        ('service_completed', 'Service Completed'),
        ('order_cancelled', 'Order Cancelled'),
        ('refund_initiated', 'Refund Initiated'),
        ('customer_feedback', 'Customer Feedback'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='timeline')
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Associated user/actor
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='order_timeline_events'
    )
    
    # Location if applicable
    location = gis_models.PointField(blank=True, null=True)
    
    # Additional data
    metadata = models.JSONField(default=dict)
    
    # Visibility
    is_customer_visible = models.BooleanField(default=True)
    is_merchant_visible = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_timeline'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number}: {self.event_type}"


class Subscription(models.Model):
    """
    Recurring orders/subscriptions
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Subscription Details
    subscription_number = models.CharField(max_length=50, unique=True)
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    merchant = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    
    # Template Order
    template_order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    
    # Schedule
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    frequency_count = models.IntegerField(default=1, help_text="Every N days/weeks/months")
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    next_order_date = models.DateField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Billing
    mandate = models.ForeignKey(
        'payments_upi.UPIMandate',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='subscriptions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
        indexes = [
            models.Index(fields=['status', 'next_order_date']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['merchant', 'status']),
        ]
    
    def __str__(self):
        return f"Subscription {self.subscription_number} - {self.customer.get_full_name()}"