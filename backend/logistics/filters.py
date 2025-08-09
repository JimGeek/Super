import django_filters
from django.db import models
from django.contrib.gis.measure import Distance
from django.contrib.gis.geos import Point
from .models import Delivery, DeliveryPartner, DeliveryZone, DeliveryRoute


class DeliveryFilter(django_filters.FilterSet):
    """Filter for Delivery model"""
    
    status = django_filters.MultipleChoiceFilter(
        choices=Delivery.STATUS_CHOICES,
        help_text="Filter by delivery status (multiple values supported)"
    )
    
    priority = django_filters.MultipleChoiceFilter(
        choices=Delivery.PRIORITY_CHOICES,
        help_text="Filter by delivery priority"
    )
    
    delivery_partner = django_filters.UUIDFilter(
        field_name='delivery_partner__id',
        help_text="Filter by delivery partner ID"
    )
    
    delivery_zone = django_filters.UUIDFilter(
        field_name='delivery_zone__id',
        help_text="Filter by delivery zone ID"
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter deliveries created after this datetime"
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter deliveries created before this datetime"
    )
    
    assigned_after = django_filters.DateTimeFilter(
        field_name='assigned_at',
        lookup_expr='gte',
        help_text="Filter deliveries assigned after this datetime"
    )
    
    assigned_before = django_filters.DateTimeFilter(
        field_name='assigned_at',
        lookup_expr='lte',
        help_text="Filter deliveries assigned before this datetime"
    )
    
    estimated_delivery_after = django_filters.DateTimeFilter(
        field_name='estimated_delivery_time',
        lookup_expr='gte',
        help_text="Filter by estimated delivery time after"
    )
    
    estimated_delivery_before = django_filters.DateTimeFilter(
        field_name='estimated_delivery_time',
        lookup_expr='lte',
        help_text="Filter by estimated delivery time before"
    )
    
    min_distance = django_filters.NumberFilter(
        field_name='distance',
        lookup_expr='gte',
        help_text="Minimum delivery distance in km"
    )
    
    max_distance = django_filters.NumberFilter(
        field_name='distance',
        lookup_expr='lte',
        help_text="Maximum delivery distance in km"
    )
    
    min_delivery_fee = django_filters.NumberFilter(
        field_name='delivery_fee',
        lookup_expr='gte',
        help_text="Minimum delivery fee"
    )
    
    max_delivery_fee = django_filters.NumberFilter(
        field_name='delivery_fee',
        lookup_expr='lte',
        help_text="Maximum delivery fee"
    )
    
    customer_rating = django_filters.RangeFilter(
        field_name='customer_rating',
        help_text="Filter by customer rating range (e.g., min=1&max=5)"
    )
    
    has_tracking = django_filters.BooleanFilter(
        method='filter_has_tracking',
        help_text="Filter deliveries with/without tracking data"
    )
    
    is_overdue = django_filters.BooleanFilter(
        method='filter_is_overdue',
        help_text="Filter overdue deliveries"
    )
    
    near_location = django_filters.CharFilter(
        method='filter_near_location',
        help_text="Filter deliveries near location (format: lat,lng,radius_km)"
    )
    
    order_number = django_filters.CharFilter(
        field_name='order__order_number',
        lookup_expr='icontains',
        help_text="Filter by order number (partial match)"
    )
    
    merchant_name = django_filters.CharFilter(
        field_name='order__merchant__business_name',
        lookup_expr='icontains',
        help_text="Filter by merchant business name"
    )
    
    customer_name = django_filters.CharFilter(
        field_name='order__customer__full_name',
        lookup_expr='icontains',
        help_text="Filter by customer name"
    )
    
    customer_phone = django_filters.CharFilter(
        field_name='order__customer__phone_number',
        lookup_expr='icontains',
        help_text="Filter by customer phone number"
    )
    
    class Meta:
        model = Delivery
        fields = []
    
    def filter_has_tracking(self, queryset, name, value):
        if value is True:
            return queryset.filter(tracking_data__isnull=False).distinct()
        elif value is False:
            return queryset.filter(tracking_data__isnull=True)
        return queryset
    
    def filter_is_overdue(self, queryset, name, value):
        from django.utils import timezone
        
        if value is True:
            return queryset.filter(
                estimated_delivery_time__lt=timezone.now(),
                status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
            )
        elif value is False:
            return queryset.exclude(
                estimated_delivery_time__lt=timezone.now(),
                status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
            )
        return queryset
    
    def filter_near_location(self, queryset, name, value):
        try:
            parts = value.split(',')
            if len(parts) != 3:
                return queryset
            
            lat = float(parts[0])
            lng = float(parts[1])
            radius_km = float(parts[2])
            
            center = Point(lng, lat, srid=4326)
            
            # Filter by pickup or delivery address within radius
            return queryset.filter(
                models.Q(
                    # This would require a custom lookup for JSON fields with coordinates
                    # For now, we'll skip the actual implementation
                    id__isnull=False
                )
            )
        except (ValueError, IndexError):
            return queryset


class DeliveryPartnerFilter(django_filters.FilterSet):
    """Filter for DeliveryPartner model"""
    
    status = django_filters.MultipleChoiceFilter(
        choices=DeliveryPartner.STATUS_CHOICES,
        help_text="Filter by partner status"
    )
    
    vehicle_type = django_filters.MultipleChoiceFilter(
        choices=DeliveryPartner.VEHICLE_CHOICES,
        help_text="Filter by vehicle type"
    )
    
    is_available = django_filters.BooleanFilter(
        method='filter_is_available',
        help_text="Filter available partners"
    )
    
    delivery_zone = django_filters.UUIDFilter(
        field_name='delivery_zones__id',
        help_text="Filter partners by delivery zone"
    )
    
    min_rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='gte',
        help_text="Minimum partner rating"
    )
    
    max_rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='lte',
        help_text="Maximum partner rating"
    )
    
    min_success_rate = django_filters.NumberFilter(
        method='filter_min_success_rate',
        help_text="Minimum success rate percentage"
    )
    
    max_capacity = django_filters.NumberFilter(
        field_name='max_capacity',
        lookup_expr='lte',
        help_text="Maximum capacity filter"
    )
    
    min_capacity = django_filters.NumberFilter(
        field_name='max_capacity',
        lookup_expr='gte',
        help_text="Minimum capacity filter"
    )
    
    has_current_deliveries = django_filters.BooleanFilter(
        method='filter_has_current_deliveries',
        help_text="Filter partners with/without current deliveries"
    )
    
    near_location = django_filters.CharFilter(
        method='filter_near_location',
        help_text="Filter partners near location (format: lat,lng,radius_km)"
    )
    
    phone_number = django_filters.CharFilter(
        field_name='phone_number',
        lookup_expr='icontains',
        help_text="Filter by phone number"
    )
    
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        help_text="Filter by partner name"
    )
    
    joined_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter partners joined after this date"
    )
    
    joined_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter partners joined before this date"
    )
    
    class Meta:
        model = DeliveryPartner
        fields = []
    
    def filter_is_available(self, queryset, name, value):
        if value is True:
            from django.utils import timezone
            return queryset.filter(
                status='active',
                current_location__isnull=False,
                last_location_update__gte=timezone.now() - timezone.timedelta(minutes=10)
            )
        elif value is False:
            from django.utils import timezone
            return queryset.exclude(
                status='active',
                current_location__isnull=False,
                last_location_update__gte=timezone.now() - timezone.timedelta(minutes=10)
            )
        return queryset
    
    def filter_min_success_rate(self, queryset, name, value):
        try:
            min_rate = float(value)
            return queryset.extra(
                where=[
                    "CASE WHEN total_deliveries = 0 THEN 100.0 ELSE (successful_deliveries::float / total_deliveries::float) * 100.0 END >= %s"
                ],
                params=[min_rate]
            )
        except (ValueError, TypeError):
            return queryset
    
    def filter_has_current_deliveries(self, queryset, name, value):
        if value is True:
            return queryset.filter(
                deliveries__status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
            ).distinct()
        elif value is False:
            return queryset.exclude(
                deliveries__status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
            ).distinct()
        return queryset
    
    def filter_near_location(self, queryset, name, value):
        try:
            parts = value.split(',')
            if len(parts) != 3:
                return queryset
            
            lat = float(parts[0])
            lng = float(parts[1])
            radius_km = float(parts[2])
            
            center = Point(lng, lat, srid=4326)
            distance = Distance(km=radius_km)
            
            return queryset.filter(
                current_location__distance_lte=(center, distance)
            )
        except (ValueError, IndexError):
            return queryset


class DeliveryZoneFilter(django_filters.FilterSet):
    """Filter for DeliveryZone model"""
    
    is_active = django_filters.BooleanFilter(
        field_name='is_active',
        help_text="Filter by active status"
    )
    
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        help_text="Filter by zone name"
    )
    
    min_delivery_distance = django_filters.NumberFilter(
        field_name='max_delivery_distance',
        lookup_expr='gte',
        help_text="Minimum max delivery distance"
    )
    
    max_delivery_distance = django_filters.NumberFilter(
        field_name='max_delivery_distance',
        lookup_expr='lte',
        help_text="Maximum max delivery distance"
    )
    
    min_base_fee = django_filters.NumberFilter(
        field_name='base_delivery_fee',
        lookup_expr='gte',
        help_text="Minimum base delivery fee"
    )
    
    max_base_fee = django_filters.NumberFilter(
        field_name='base_delivery_fee',
        lookup_expr='lte',
        help_text="Maximum base delivery fee"
    )
    
    contains_point = django_filters.CharFilter(
        method='filter_contains_point',
        help_text="Filter zones containing point (format: lat,lng)"
    )
    
    intersects_bounds = django_filters.CharFilter(
        method='filter_intersects_bounds',
        help_text="Filter zones intersecting bounds (format: sw_lat,sw_lng,ne_lat,ne_lng)"
    )
    
    class Meta:
        model = DeliveryZone
        fields = []
    
    def filter_contains_point(self, queryset, name, value):
        try:
            parts = value.split(',')
            if len(parts) != 2:
                return queryset
            
            lat = float(parts[0])
            lng = float(parts[1])
            
            point = Point(lng, lat, srid=4326)
            return queryset.filter(boundary__contains=point)
        except (ValueError, IndexError):
            return queryset
    
    def filter_intersects_bounds(self, queryset, name, value):
        try:
            parts = value.split(',')
            if len(parts) != 4:
                return queryset
            
            sw_lat = float(parts[0])
            sw_lng = float(parts[1])
            ne_lat = float(parts[2])
            ne_lng = float(parts[3])
            
            # Create bounding box polygon
            from django.contrib.gis.geos import Polygon
            
            bbox = Polygon.from_bbox((sw_lng, sw_lat, ne_lng, ne_lat))
            return queryset.filter(boundary__intersects=bbox)
        except (ValueError, IndexError):
            return queryset


class DeliveryRouteFilter(django_filters.FilterSet):
    """Filter for DeliveryRoute model"""
    
    status = django_filters.MultipleChoiceFilter(
        choices=DeliveryRoute.ROUTE_STATUS_CHOICES,
        help_text="Filter by route status"
    )
    
    delivery_partner = django_filters.UUIDFilter(
        field_name='delivery_partner__id',
        help_text="Filter by delivery partner ID"
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter routes created after this datetime"
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter routes created before this datetime"
    )
    
    started_after = django_filters.DateTimeFilter(
        field_name='started_at',
        lookup_expr='gte',
        help_text="Filter routes started after this datetime"
    )
    
    started_before = django_filters.DateTimeFilter(
        field_name='started_at',
        lookup_expr='lte',
        help_text="Filter routes started before this datetime"
    )
    
    min_distance = django_filters.NumberFilter(
        field_name='total_distance',
        lookup_expr='gte',
        help_text="Minimum total distance"
    )
    
    max_distance = django_filters.NumberFilter(
        field_name='total_distance',
        lookup_expr='lte',
        help_text="Maximum total distance"
    )
    
    min_duration = django_filters.NumberFilter(
        field_name='estimated_duration',
        lookup_expr='gte',
        help_text="Minimum estimated duration in minutes"
    )
    
    max_duration = django_filters.NumberFilter(
        field_name='estimated_duration',
        lookup_expr='lte',
        help_text="Maximum estimated duration in minutes"
    )
    
    route_name = django_filters.CharFilter(
        field_name='route_name',
        lookup_expr='icontains',
        help_text="Filter by route name"
    )
    
    class Meta:
        model = DeliveryRoute
        fields = []