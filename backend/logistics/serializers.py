from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.contrib.gis.geos import Point
from .models import (
    DeliveryZone, DeliveryPartner, DeliveryRoute, Delivery, 
    DeliveryTracking, RouteOptimizationJob, DeliveryAnalytics
)


class DeliveryZoneSerializer(GeoFeatureModelSerializer):
    """Serializer for DeliveryZone model"""
    
    class Meta:
        model = DeliveryZone
        geo_field = 'boundary'
        fields = [
            'id', 'name', 'description', 'boundary', 'center_point',
            'is_active', 'max_delivery_distance', 'base_delivery_fee',
            'per_km_rate', 'operating_hours', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DeliveryPartnerSerializer(serializers.ModelSerializer):
    """Serializer for DeliveryPartner model"""
    
    current_location = serializers.SerializerMethodField()
    success_rate = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()
    delivery_zones_data = DeliveryZoneSerializer(source='delivery_zones', many=True, read_only=True)
    
    class Meta:
        model = DeliveryPartner
        fields = [
            'id', 'name', 'phone_number', 'email', 'profile_image',
            'id_proof', 'license_details', 'vehicle_details',
            'status', 'vehicle_type', 'max_capacity', 'max_weight',
            'current_location', 'last_location_update', 'delivery_zones_data',
            'rating', 'total_deliveries', 'successful_deliveries',
            'average_delivery_time', 'success_rate', 'is_available',
            'commission_rate', 'total_earnings', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'rating', 'total_deliveries', 'successful_deliveries',
            'average_delivery_time', 'total_earnings', 'success_rate',
            'is_available', 'created_at', 'updated_at'
        ]
    
    def get_current_location(self, obj):
        if obj.current_location:
            return {
                'latitude': obj.current_location.y,
                'longitude': obj.current_location.x
            }
        return None


class DeliveryPartnerLocationUpdateSerializer(serializers.Serializer):
    """Serializer for updating delivery partner location"""
    
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    accuracy = serializers.FloatField(min_value=0, default=0.0)
    speed = serializers.FloatField(min_value=0, default=0.0)
    bearing = serializers.FloatField(min_value=0, max_value=360, required=False)
    battery_level = serializers.IntegerField(min_value=0, max_value=100, required=False)
    network_quality = serializers.CharField(max_length=20, required=False)


class DeliveryRouteSerializer(serializers.ModelSerializer):
    """Serializer for DeliveryRoute model"""
    
    delivery_partner_data = DeliveryPartnerSerializer(source='delivery_partner', read_only=True)
    start_location = serializers.SerializerMethodField()
    end_location = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryRoute
        fields = [
            'id', 'delivery_partner_data', 'route_name', 'status',
            'start_location', 'end_location', 'waypoints',
            'osrm_route_data', 'total_distance', 'estimated_duration',
            'started_at', 'completed_at', 'actual_distance', 'actual_duration',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'osrm_route_data', 'started_at', 'completed_at',
            'actual_distance', 'actual_duration', 'created_at', 'updated_at'
        ]
    
    def get_start_location(self, obj):
        if obj.start_location:
            return {
                'latitude': obj.start_location.y,
                'longitude': obj.start_location.x
            }
        return None
    
    def get_end_location(self, obj):
        if obj.end_location:
            return {
                'latitude': obj.end_location.y,
                'longitude': obj.end_location.x
            }
        return None


class DeliverySerializer(serializers.ModelSerializer):
    """Serializer for Delivery model"""
    
    delivery_partner_data = DeliveryPartnerSerializer(source='delivery_partner', read_only=True)
    delivery_route_data = DeliveryRouteSerializer(source='delivery_route', read_only=True)
    delivery_zone_data = DeliveryZoneSerializer(source='delivery_zone', read_only=True)
    order_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Delivery
        fields = [
            'id', 'order_data', 'delivery_partner_data', 'delivery_route_data',
            'delivery_zone_data', 'status', 'priority', 'pickup_address',
            'delivery_address', 'distance', 'delivery_fee', 'partner_commission',
            'estimated_pickup_time', 'estimated_delivery_time',
            'actual_pickup_time', 'actual_delivery_time',
            'pickup_instructions', 'delivery_instructions', 'customer_notes',
            'delivery_otp', 'proof_of_delivery', 'customer_rating',
            'customer_feedback', 'failure_reason', 'return_reason',
            'retry_count', 'assigned_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'distance', 'delivery_fee', 'partner_commission',
            'delivery_otp', 'assigned_at', 'created_at', 'updated_at'
        ]
    
    def get_order_data(self, obj):
        return {
            'id': str(obj.order.id),
            'order_number': obj.order.order_number,
            'total_amount': obj.order.total_amount,
            'merchant': {
                'id': str(obj.order.merchant.id),
                'name': obj.order.merchant.business_name,
                'phone': obj.order.merchant.phone_number
            },
            'customer': {
                'id': str(obj.order.customer.id),
                'name': obj.order.customer.full_name,
                'phone': obj.order.customer.phone_number
            }
        }


class DeliveryStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating delivery status"""
    
    STATUS_CHOICES = [
        'accepted', 'picked_up', 'in_transit', 'delivered', 'failed', 'cancelled'
    ]
    
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    notes = serializers.CharField(max_length=500, required=False)
    proof_images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        max_length=5
    )
    customer_signature = serializers.URLField(required=False)
    failure_reason = serializers.CharField(max_length=500, required=False)
    otp = serializers.CharField(max_length=6, required=False)
    
    def validate(self, attrs):
        status = attrs.get('status')
        
        if status == 'delivered':
            if not attrs.get('otp') and not attrs.get('customer_signature'):
                raise serializers.ValidationError(
                    "Either OTP or customer signature is required for delivery completion"
                )
        
        if status == 'failed' and not attrs.get('failure_reason'):
            raise serializers.ValidationError(
                "Failure reason is required when marking delivery as failed"
            )
        
        return attrs


class DeliveryTrackingSerializer(serializers.ModelSerializer):
    """Serializer for DeliveryTracking model"""
    
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryTracking
        fields = [
            'id', 'location', 'accuracy', 'speed', 'bearing',
            'status', 'battery_level', 'network_quality',
            'recorded_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_location(self, obj):
        return {
            'latitude': obj.location.y,
            'longitude': obj.location.x
        }


class RouteOptimizationJobSerializer(serializers.ModelSerializer):
    """Serializer for RouteOptimizationJob model"""
    
    class Meta:
        model = RouteOptimizationJob
        fields = [
            'id', 'job_type', 'status', 'priority', 'input_data',
            'result_data', 'execution_time', 'error_message',
            'scheduled_at', 'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'status', 'result_data', 'execution_time',
            'error_message', 'started_at', 'completed_at', 'created_at'
        ]


class DeliveryAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for DeliveryAnalytics model"""
    
    success_rate = serializers.SerializerMethodField()
    cancellation_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = DeliveryAnalytics
        fields = [
            'id', 'delivery_partner', 'delivery_zone', 'period_type',
            'period_start', 'period_end', 'total_deliveries',
            'successful_deliveries', 'failed_deliveries', 'cancelled_deliveries',
            'success_rate', 'cancellation_rate', 'average_delivery_time',
            'average_distance', 'total_distance', 'total_delivery_fees',
            'total_commissions', 'average_rating', 'total_ratings',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_success_rate(self, obj):
        if obj.total_deliveries == 0:
            return 100.0
        return (obj.successful_deliveries / obj.total_deliveries) * 100
    
    def get_cancellation_rate(self, obj):
        if obj.total_deliveries == 0:
            return 0.0
        return (obj.cancelled_deliveries / obj.total_deliveries) * 100


# Utility serializers
class RouteOptimizationRequestSerializer(serializers.Serializer):
    """Serializer for route optimization requests"""
    
    partner_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Specific partners to optimize. If not provided, optimizes all active partners."
    )
    priority = serializers.IntegerField(default=0, min_value=0, max_value=10)
    schedule_time = serializers.DateTimeField(required=False)


class DeliveryAssignmentRequestSerializer(serializers.Serializer):
    """Serializer for manual delivery assignment requests"""
    
    delivery_id = serializers.UUIDField()
    partner_id = serializers.UUIDField()
    force_assign = serializers.BooleanField(default=False)
    
    def validate(self, attrs):
        try:
            delivery = Delivery.objects.get(id=attrs['delivery_id'])
            partner = DeliveryPartner.objects.get(id=attrs['partner_id'])
            
            if delivery.status not in ['pending', 'assigned']:
                raise serializers.ValidationError(
                    "Can only assign pending or previously assigned deliveries"
                )
            
            if partner.status != 'active':
                raise serializers.ValidationError("Partner must be active")
            
            # Check if partner is at capacity
            current_load = partner.deliveries.filter(
                status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
            ).count()
            
            if current_load >= partner.max_capacity and not attrs.get('force_assign'):
                raise serializers.ValidationError(
                    f"Partner is at capacity ({current_load}/{partner.max_capacity}). "
                    "Use force_assign=true to override."
                )
            
            attrs['delivery'] = delivery
            attrs['partner'] = partner
            
        except (Delivery.DoesNotExist, DeliveryPartner.DoesNotExist) as e:
            raise serializers.ValidationError(str(e))
        
        return attrs


class DeliveryETARequestSerializer(serializers.Serializer):
    """Serializer for ETA calculation requests"""
    
    delivery_ids = serializers.ListField(
        child=serializers.UUIDField(),
        max_length=50,
        help_text="List of delivery IDs to calculate ETA for"
    )
    
    def validate_delivery_ids(self, value):
        # Check if all deliveries exist and are valid
        existing_deliveries = Delivery.objects.filter(id__in=value).count()
        if existing_deliveries != len(value):
            raise serializers.ValidationError("One or more delivery IDs are invalid")
        return value


class DeliveryETAResponseSerializer(serializers.Serializer):
    """Serializer for ETA calculation responses"""
    
    delivery_id = serializers.UUIDField()
    current_eta = serializers.DateTimeField(allow_null=True)
    original_eta = serializers.DateTimeField(allow_null=True)
    delay_minutes = serializers.IntegerField(allow_null=True)
    partner_location = serializers.DictField(allow_null=True)


class DeliveryStatsSerializer(serializers.Serializer):
    """Serializer for delivery statistics"""
    
    total_deliveries = serializers.IntegerField()
    pending_deliveries = serializers.IntegerField()
    active_deliveries = serializers.IntegerField()
    completed_deliveries = serializers.IntegerField()
    failed_deliveries = serializers.IntegerField()
    cancelled_deliveries = serializers.IntegerField()
    success_rate = serializers.FloatField()
    average_delivery_time = serializers.FloatField()
    total_distance = serializers.FloatField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_partners = serializers.IntegerField()
    average_rating = serializers.FloatField()