from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from accounts.models import Organization
from orders.models import Order


class DeliveryZone(models.Model):
    """Geographic zones for delivery coverage"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='delivery_zones')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Geographic boundary
    boundary = gis_models.PolygonField(srid=4326)
    center_point = gis_models.PointField(srid=4326)
    
    # Zone configuration
    is_active = models.BooleanField(default=True)
    max_delivery_distance = models.FloatField(default=10.0, help_text="Maximum delivery distance in km")
    base_delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    per_km_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('5.00'))
    
    # Operational hours
    operating_hours = models.JSONField(default=dict, help_text="Operating hours per day")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'logistics_delivery_zones'
        indexes = [
            models.Index(fields=['organization', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.organization.name}"


class DeliveryPartner(models.Model):
    """Delivery partners/riders"""
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    
    VEHICLE_CHOICES = [
        ('bicycle', 'Bicycle'),
        ('motorbike', 'Motorbike'),
        ('car', 'Car'),
        ('van', 'Van'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='delivery_partners')
    
    # Personal information
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True)
    profile_image = models.URLField(blank=True)
    
    # Verification documents
    id_proof = models.JSONField(default=dict, help_text="ID proof details")
    license_details = models.JSONField(default=dict, help_text="License details")
    vehicle_details = models.JSONField(default=dict, help_text="Vehicle registration details")
    
    # Status and preferences
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_CHOICES, default='motorbike')
    max_capacity = models.IntegerField(default=10, help_text="Maximum number of orders")
    max_weight = models.FloatField(default=25.0, help_text="Maximum weight capacity in kg")
    
    # Location and availability
    current_location = gis_models.PointField(srid=4326, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    delivery_zones = models.ManyToManyField(DeliveryZone, blank=True)
    
    # Performance metrics
    rating = models.FloatField(default=5.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    average_delivery_time = models.FloatField(default=30.0, help_text="Average delivery time in minutes")
    
    # Financial
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('15.00'))
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'logistics_delivery_partners'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['phone_number']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
    
    @property
    def success_rate(self):
        if self.total_deliveries == 0:
            return 100.0
        return (self.successful_deliveries / self.total_deliveries) * 100
    
    @property
    def is_available(self):
        return (
            self.status == 'active' and 
            self.current_location is not None and
            timezone.now() - self.last_location_update < timezone.timedelta(minutes=10)
        )


class DeliveryRoute(models.Model):
    """Optimized delivery routes"""
    ROUTE_STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='delivery_routes')
    delivery_partner = models.ForeignKey(DeliveryPartner, on_delete=models.CASCADE, related_name='routes')
    
    # Route details
    route_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=ROUTE_STATUS_CHOICES, default='planned')
    
    # Route optimization data
    start_location = gis_models.PointField(srid=4326)
    end_location = gis_models.PointField(srid=4326, null=True, blank=True)
    waypoints = models.JSONField(default=list, help_text="Ordered list of delivery waypoints")
    
    # OSRM route data
    osrm_route_data = models.JSONField(default=dict, help_text="OSRM route optimization response")
    total_distance = models.FloatField(default=0.0, help_text="Total route distance in km")
    estimated_duration = models.IntegerField(default=0, help_text="Estimated duration in minutes")
    
    # Route execution
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    actual_distance = models.FloatField(null=True, blank=True)
    actual_duration = models.IntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'logistics_delivery_routes'
        indexes = [
            models.Index(fields=['organization', 'delivery_partner']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.route_name} - {self.delivery_partner.name}"


class Delivery(models.Model):
    """Individual delivery instances"""
    STATUS_CHOICES = [
        ('pending', 'Pending Assignment'),
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='deliveries')
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery')
    
    # Assignment details
    delivery_partner = models.ForeignKey(DeliveryPartner, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    delivery_route = models.ForeignKey(DeliveryRoute, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    delivery_zone = models.ForeignKey(DeliveryZone, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Delivery details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Addresses
    pickup_address = models.JSONField(help_text="Pickup address with coordinates")
    delivery_address = models.JSONField(help_text="Delivery address with coordinates")
    
    # Distance and fees
    distance = models.FloatField(default=0.0, help_text="Distance in km")
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    partner_commission = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # Timing
    estimated_pickup_time = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_pickup_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Special instructions
    pickup_instructions = models.TextField(blank=True)
    delivery_instructions = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)
    
    # Proof of delivery
    delivery_otp = models.CharField(max_length=6, blank=True)
    proof_of_delivery = models.JSONField(default=dict, help_text="Photos, signatures, etc.")
    customer_rating = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    customer_feedback = models.TextField(blank=True)
    
    # Failure/return details
    failure_reason = models.TextField(blank=True)
    return_reason = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Timestamps
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'logistics_deliveries'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['delivery_partner', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Delivery {self.order.order_number} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Generate OTP for delivery verification
        if not self.delivery_otp and self.status in ['assigned', 'accepted']:
            import random
            self.delivery_otp = str(random.randint(100000, 999999))
        
        super().save(*args, **kwargs)


class DeliveryTracking(models.Model):
    """Real-time delivery tracking data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='tracking_data')
    
    # Location data
    location = gis_models.PointField(srid=4326)
    accuracy = models.FloatField(default=0.0, help_text="GPS accuracy in meters")
    speed = models.FloatField(default=0.0, help_text="Speed in km/h")
    bearing = models.FloatField(null=True, blank=True, help_text="Direction in degrees")
    
    # Status and metadata
    status = models.CharField(max_length=50)
    battery_level = models.IntegerField(null=True, blank=True)
    network_quality = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    recorded_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'logistics_delivery_tracking'
        indexes = [
            models.Index(fields=['delivery', '-recorded_at']),
        ]
        ordering = ['-recorded_at']


class RouteOptimizationJob(models.Model):
    """Route optimization job queue"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    # Job details
    job_type = models.CharField(max_length=50, default='route_optimization')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=0)
    
    # Input data
    input_data = models.JSONField(help_text="Deliveries and constraints")
    
    # Results
    result_data = models.JSONField(default=dict, help_text="Optimization results")
    execution_time = models.FloatField(null=True, blank=True, help_text="Execution time in seconds")
    error_message = models.TextField(blank=True)
    
    # Timestamps
    scheduled_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'logistics_route_optimization_jobs'
        indexes = [
            models.Index(fields=['status', 'priority', 'scheduled_at']),
        ]
        ordering = ['-priority', 'scheduled_at']


class DeliveryAnalytics(models.Model):
    """Aggregated delivery analytics"""
    PERIOD_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    delivery_partner = models.ForeignKey(DeliveryPartner, on_delete=models.CASCADE, null=True, blank=True)
    delivery_zone = models.ForeignKey(DeliveryZone, on_delete=models.CASCADE, null=True, blank=True)
    
    # Period
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Metrics
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    failed_deliveries = models.IntegerField(default=0)
    cancelled_deliveries = models.IntegerField(default=0)
    
    # Performance metrics
    average_delivery_time = models.FloatField(default=0.0)
    average_distance = models.FloatField(default=0.0)
    total_distance = models.FloatField(default=0.0)
    
    # Financial metrics
    total_delivery_fees = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_commissions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Customer satisfaction
    average_rating = models.FloatField(default=5.0)
    total_ratings = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'logistics_delivery_analytics'
        indexes = [
            models.Index(fields=['organization', 'period_type', 'period_start']),
            models.Index(fields=['delivery_partner', 'period_start']),
        ]
        unique_together = [
            ['organization', 'delivery_partner', 'delivery_zone', 'period_type', 'period_start']
        ]