from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    DeliveryZone, DeliveryPartner, DeliveryRoute, Delivery,
    DeliveryTracking, RouteOptimizationJob, DeliveryAnalytics
)


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(OSMGeoAdmin):
    list_display = [
        'name', 'organization', 'is_active', 'max_delivery_distance',
        'base_delivery_fee', 'per_km_rate', 'created_at'
    ]
    list_filter = ['is_active', 'organization', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'organization', 'is_active']
        }),
        ('Geographic Coverage', {
            'fields': ['boundary', 'center_point', 'max_delivery_distance']
        }),
        ('Pricing', {
            'fields': ['base_delivery_fee', 'per_km_rate']
        }),
        ('Operations', {
            'fields': ['operating_hours']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


@admin.register(DeliveryPartner)
class DeliveryPartnerAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'phone_number', 'organization', 'status', 'vehicle_type',
        'rating', 'total_deliveries', 'success_rate_display', 'is_available',
        'created_at'
    ]
    list_filter = [
        'status', 'vehicle_type', 'organization', 'created_at',
        'last_location_update'
    ]
    search_fields = ['name', 'phone_number', 'email']
    readonly_fields = [
        'rating', 'total_deliveries', 'successful_deliveries',
        'average_delivery_time', 'total_earnings', 'success_rate_display',
        'is_available', 'created_at', 'updated_at'
    ]
    filter_horizontal = ['delivery_zones']
    
    fieldsets = [
        ('Personal Information', {
            'fields': [
                'name', 'phone_number', 'email', 'profile_image', 'organization'
            ]
        }),
        ('Verification Documents', {
            'fields': ['id_proof', 'license_details', 'vehicle_details'],
            'classes': ['collapse']
        }),
        ('Status & Preferences', {
            'fields': [
                'status', 'vehicle_type', 'max_capacity', 'max_weight',
                'delivery_zones'
            ]
        }),
        ('Location & Availability', {
            'fields': [
                'current_location', 'last_location_update', 'is_available'
            ]
        }),
        ('Performance Metrics', {
            'fields': [
                'rating', 'total_deliveries', 'successful_deliveries',
                'average_delivery_time', 'success_rate_display'
            ],
            'classes': ['collapse']
        }),
        ('Financial', {
            'fields': ['commission_rate', 'total_earnings']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        color = 'green' if rate >= 90 else 'orange' if rate >= 80 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')
    
    actions = ['approve_partners', 'suspend_partners']
    
    def approve_partners(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='active')
        self.message_user(request, f'{updated} partners approved.')
    approve_partners.short_description = 'Approve selected partners'
    
    def suspend_partners(self, request, queryset):
        updated = queryset.filter(status='active').update(status='suspended')
        self.message_user(request, f'{updated} partners suspended.')
    suspend_partners.short_description = 'Suspend selected partners'


@admin.register(DeliveryRoute)
class DeliveryRouteAdmin(admin.ModelAdmin):
    list_display = [
        'route_name', 'delivery_partner', 'organization', 'status',
        'total_distance', 'estimated_duration', 'waypoints_count',
        'created_at'
    ]
    list_filter = ['status', 'organization', 'created_at']
    search_fields = ['route_name', 'delivery_partner__name']
    readonly_fields = [
        'osrm_route_data', 'total_distance', 'estimated_duration',
        'waypoints_count', 'actual_distance', 'actual_duration',
        'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Route Information', {
            'fields': [
                'route_name', 'delivery_partner', 'organization', 'status'
            ]
        }),
        ('Route Planning', {
            'fields': [
                'start_location', 'end_location', 'waypoints', 'waypoints_count'
            ]
        }),
        ('Optimization Data', {
            'fields': [
                'osrm_route_data', 'total_distance', 'estimated_duration'
            ],
            'classes': ['collapse']
        }),
        ('Execution', {
            'fields': [
                'started_at', 'completed_at', 'actual_distance', 'actual_duration'
            ]
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def waypoints_count(self, obj):
        return len(obj.waypoints) if obj.waypoints else 0
    waypoints_count.short_description = 'Waypoints'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'delivery_partner', 'organization'
        )


class DeliveryTrackingInline(admin.TabularInline):
    model = DeliveryTracking
    extra = 0
    readonly_fields = ['recorded_at', 'created_at']
    fields = [
        'location', 'status', 'accuracy', 'speed', 'bearing',
        'battery_level', 'recorded_at'
    ]


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'delivery_partner', 'organization', 'status',
        'priority', 'distance', 'delivery_fee', 'estimated_delivery_time',
        'created_at'
    ]
    list_filter = [
        'status', 'priority', 'organization', 'delivery_partner',
        'delivery_zone', 'created_at', 'estimated_delivery_time'
    ]
    search_fields = [
        'order__order_number', 'delivery_partner__name',
        'delivery_otp'
    ]
    readonly_fields = [
        'distance', 'delivery_fee', 'partner_commission', 'delivery_otp',
        'assigned_at', 'created_at', 'updated_at'
    ]
    inlines = [DeliveryTrackingInline]
    
    fieldsets = [
        ('Order Information', {
            'fields': ['order', 'organization']
        }),
        ('Assignment', {
            'fields': [
                'delivery_partner', 'delivery_route', 'delivery_zone',
                'assigned_at'
            ]
        }),
        ('Delivery Details', {
            'fields': [
                'status', 'priority', 'pickup_address', 'delivery_address',
                'distance', 'delivery_fee', 'partner_commission'
            ]
        }),
        ('Timing', {
            'fields': [
                'estimated_pickup_time', 'estimated_delivery_time',
                'actual_pickup_time', 'actual_delivery_time'
            ]
        }),
        ('Instructions & Notes', {
            'fields': [
                'pickup_instructions', 'delivery_instructions',
                'customer_notes'
            ],
            'classes': ['collapse']
        }),
        ('Verification & Proof', {
            'fields': [
                'delivery_otp', 'proof_of_delivery', 'customer_rating',
                'customer_feedback'
            ],
            'classes': ['collapse']
        }),
        ('Failure Handling', {
            'fields': ['failure_reason', 'return_reason', 'retry_count'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order Number'
    order_number.admin_order_field = 'order__order_number'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'delivery_partner', 'delivery_zone', 'organization'
        )
    
    actions = ['mark_as_delivered', 'mark_as_failed']
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.filter(
            status__in=['picked_up', 'in_transit']
        ).update(
            status='delivered',
            actual_delivery_time=timezone.now()
        )
        self.message_user(request, f'{updated} deliveries marked as delivered.')
    mark_as_delivered.short_description = 'Mark as delivered'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(
            status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
        ).update(status='failed')
        self.message_user(request, f'{updated} deliveries marked as failed.')
    mark_as_failed.short_description = 'Mark as failed'


@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
    list_display = [
        'delivery_order', 'delivery_partner', 'status', 'speed',
        'accuracy', 'battery_level', 'recorded_at'
    ]
    list_filter = ['status', 'recorded_at']
    search_fields = ['delivery__order__order_number']
    readonly_fields = ['created_at']
    
    def delivery_order(self, obj):
        return obj.delivery.order.order_number
    delivery_order.short_description = 'Order Number'
    
    def delivery_partner(self, obj):
        return obj.delivery.delivery_partner.name if obj.delivery.delivery_partner else '-'
    delivery_partner.short_description = 'Partner'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'delivery__order', 'delivery__delivery_partner'
        )


@admin.register(RouteOptimizationJob)
class RouteOptimizationJobAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'organization', 'job_type', 'status', 'priority',
        'execution_time', 'scheduled_at', 'created_at'
    ]
    list_filter = ['status', 'job_type', 'organization', 'created_at']
    search_fields = ['id']
    readonly_fields = [
        'result_data', 'execution_time', 'error_message',
        'started_at', 'completed_at', 'created_at'
    ]
    
    fieldsets = [
        ('Job Information', {
            'fields': ['organization', 'job_type', 'status', 'priority']
        }),
        ('Input Data', {
            'fields': ['input_data']
        }),
        ('Results', {
            'fields': ['result_data', 'execution_time', 'error_message'],
            'classes': ['collapse']
        }),
        ('Timing', {
            'fields': ['scheduled_at', 'started_at', 'completed_at', 'created_at']
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


@admin.register(DeliveryAnalytics)
class DeliveryAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'organization', 'delivery_partner', 'delivery_zone', 'period_type',
        'period_start', 'total_deliveries', 'success_rate_display',
        'average_delivery_time', 'total_delivery_fees'
    ]
    list_filter = [
        'period_type', 'organization', 'delivery_partner',
        'delivery_zone', 'period_start'
    ]
    search_fields = ['delivery_partner__name', 'delivery_zone__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Analytics Period', {
            'fields': [
                'organization', 'delivery_partner', 'delivery_zone',
                'period_type', 'period_start', 'period_end'
            ]
        }),
        ('Delivery Metrics', {
            'fields': [
                'total_deliveries', 'successful_deliveries',
                'failed_deliveries', 'cancelled_deliveries'
            ]
        }),
        ('Performance Metrics', {
            'fields': [
                'average_delivery_time', 'average_distance', 'total_distance'
            ]
        }),
        ('Financial Metrics', {
            'fields': ['total_delivery_fees', 'total_commissions']
        }),
        ('Customer Satisfaction', {
            'fields': ['average_rating', 'total_ratings']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def success_rate_display(self, obj):
        if obj.total_deliveries == 0:
            return '100.0%'
        
        rate = (obj.successful_deliveries / obj.total_deliveries) * 100
        color = 'green' if rate >= 90 else 'orange' if rate >= 80 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'organization', 'delivery_partner', 'delivery_zone'
        )


# Custom admin site configurations
admin.site.site_header = "SUPER Logistics Administration"
admin.site.site_title = "SUPER Logistics Admin"
admin.site.index_title = "Welcome to SUPER Logistics Administration"