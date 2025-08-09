"""
Django admin configuration for accounts app
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.gis.admin import OSMGeoAdmin
from .models import User, Organization, UserAddress, OTPVerification, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""
    list_display = [
        'email', 'first_name', 'last_name', 'role', 'organization',
        'is_phone_verified', 'is_email_verified', 'is_active', 'created_at'
    ]
    list_filter = [
        'role', 'user_type', 'is_phone_verified', 'is_email_verified',
        'is_active', 'is_staff', 'is_superuser', 'created_at'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'phone', 'avatar', 
                      'date_of_birth', 'gender')
        }),
        ('Organization', {
            'fields': ('role', 'user_type', 'organization')
        }),
        ('Corporate', {
            'fields': ('company_name', 'company_gstin'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': ('preferred_language', 'timezone')
        }),
        ('Verification', {
            'fields': ('is_phone_verified', 'is_email_verified')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 
                      'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'first_name', 'last_name', 
                      'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'date_joined']


@admin.register(Organization)
class OrganizationAdmin(OSMGeoAdmin):
    """Organization admin with map widget"""
    list_display = [
        'name', 'business_type', 'status', 'city', 'state',
        'delivery_radius', 'created_at'
    ]
    list_filter = ['business_type', 'status', 'state', 'created_at']
    search_fields = ['name', 'email', 'phone', 'city']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'business_type', 'status')
        }),
        ('Business Details', {
            'fields': ('registration_number', 'gstin')
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 
                      'pincode', 'location')
        }),
        ('Service Area', {
            'fields': ('delivery_radius', 'service_zones')
        }),
        ('Business Hours', {
            'fields': ('business_hours',)
        }),
        ('Platform Settings', {
            'fields': ('platform_fee_percentage', 'commission_percentage')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserAddress)
class UserAddressAdmin(OSMGeoAdmin):
    """UserAddress admin with map widget"""
    list_display = [
        'user', 'label', 'address_type', 'city', 'pincode', 
        'is_default', 'is_active'
    ]
    list_filter = ['address_type', 'is_default', 'is_active', 'city']
    search_fields = ['user__email', 'label', 'city', 'pincode']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Address Details', {
            'fields': ('label', 'address_type', 'address_line1', 
                      'address_line2', 'landmark', 'city', 'state', 
                      'pincode', 'location')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """OTP Verification admin"""
    list_display = [
        'identifier', 'verification_type', 'otp', 'is_verified',
        'attempts', 'created_at', 'expires_at'
    ]
    list_filter = ['verification_type', 'is_verified', 'created_at']
    search_fields = ['identifier', 'otp']
    readonly_fields = ['otp', 'created_at', 'verified_at']
    
    fieldsets = (
        ('OTP Details', {
            'fields': ('identifier', 'verification_type', 'otp')
        }),
        ('Status', {
            'fields': ('is_verified', 'attempts', 'verified_at')
        }),
        ('Timing', {
            'fields': ('created_at', 'expires_at')
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """User Session admin"""
    list_display = [
        'user', 'device_name', 'platform', 'app_version',
        'ip_address', 'is_active', 'created_at', 'last_activity'
    ]
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['user__email', 'device_name', 'ip_address']
    readonly_fields = ['refresh_token', 'created_at', 'last_activity']
    
    fieldsets = (
        ('User & Session', {
            'fields': ('user', 'device_id', 'device_name')
        }),
        ('Device Info', {
            'fields': ('platform', 'app_version', 'ip_address', 'location')
        }),
        ('Token & Status', {
            'fields': ('refresh_token', 'is_active')
        }),
        ('Timing', {
            'fields': ('created_at', 'last_activity', 'expires_at')
        }),
    )