"""
Django admin configuration for UPI payments app
"""
from django.contrib import admin
from .models import (
    UPIProvider, VirtualPaymentAddress, UPITransaction, 
    UPIMandate, UPIMandateExecution, UPIRefund, UPIWebhookLog
)


@admin.register(UPIProvider)
class UPIProviderAdmin(admin.ModelAdmin):
    """UPI Provider admin"""
    list_display = [
        'name', 'code', 'supports_intent', 'supports_collect',
        'supports_qr', 'supports_mandates', 'is_active', 'is_production'
    ]
    list_filter = ['is_active', 'is_production', 'supports_mandates']
    search_fields = ['name', 'code']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'code')
        }),
        ('API Configuration', {
            'fields': ('base_url', 'api_key', 'secret_key', 'webhook_secret'),
            'classes': ('collapse',)
        }),
        ('Capabilities', {
            'fields': ('supports_intent', 'supports_collect', 'supports_qr', 'supports_mandates')
        }),
        ('Status', {
            'fields': ('is_active', 'is_production')
        }),
    )


@admin.register(VirtualPaymentAddress)
class VirtualPaymentAddressAdmin(admin.ModelAdmin):
    """VPA admin"""
    list_display = ['vpa', 'holder_name', 'purpose', 'organization', 'user', 'is_active', 'is_verified']
    list_filter = ['purpose', 'is_active', 'is_verified', 'provider']
    search_fields = ['vpa', 'holder_name']
    
    fieldsets = (
        ('VPA Details', {
            'fields': ('vpa', 'holder_name', 'purpose')
        }),
        ('Association', {
            'fields': ('organization', 'user')
        }),
        ('Provider & Status', {
            'fields': ('provider', 'is_active', 'is_verified')
        }),
    )


@admin.register(UPITransaction)
class UPITransactionAdmin(admin.ModelAdmin):
    """UPI Transaction admin"""
    list_display = [
        'txn_ref', 'amount', 'status', 'transaction_type', 'payment_method',
        'user', 'organization', 'initiated_at'
    ]
    list_filter = [
        'status', 'transaction_type', 'payment_method', 'provider',
        'initiated_at', 'completed_at'
    ]
    search_fields = ['txn_ref', 'provider_txn_id', 'upi_txn_id', 'user__email']
    readonly_fields = [
        'txn_ref', 'provider_txn_id', 'upi_txn_id', 'initiated_at', 
        'completed_at', 'provider_response'
    ]
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('txn_ref', 'provider_txn_id', 'upi_txn_id', 'amount', 'currency')
        }),
        ('VPAs', {
            'fields': ('payer_vpa', 'payee_vpa')
        }),
        ('Associated Records', {
            'fields': ('order', 'user', 'organization')
        }),
        ('Transaction Info', {
            'fields': ('transaction_type', 'description', 'provider', 'payment_method')
        }),
        ('Status & Timing', {
            'fields': ('status', 'failure_reason', 'initiated_at', 'expires_at', 'completed_at')
        }),
        ('Reconciliation', {
            'fields': ('webhook_received', 'reconciled', 'reconciliation_ref')
        }),
        ('Provider Response', {
            'fields': ('provider_response',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UPIMandate)
class UPIMandateAdmin(admin.ModelAdmin):
    """UPI Mandate admin"""
    list_display = [
        'mandate_ref', 'purpose', 'user', 'organization', 'max_amount',
        'frequency', 'status', 'created_at'
    ]
    list_filter = ['purpose', 'frequency', 'status', 'provider', 'created_at']
    search_fields = ['mandate_ref', 'user__email', 'organization__name']
    readonly_fields = [
        'mandate_ref', 'provider_mandate_id', 'created_at', 
        'last_charged_at', 'provider_response'
    ]
    
    fieldsets = (
        ('Mandate Details', {
            'fields': ('mandate_ref', 'provider_mandate_id', 'purpose', 'description')
        }),
        ('Payer & Payee', {
            'fields': ('payer_vpa', 'payee_vpa', 'user', 'organization')
        }),
        ('Terms', {
            'fields': ('max_amount', 'frequency', 'start_date', 'end_date')
        }),
        ('Auto-charge Settings', {
            'fields': ('auto_charge_threshold', 'auto_charge_amount'),
            'classes': ('collapse',)
        }),
        ('Status & Provider', {
            'fields': ('status', 'provider')
        }),
        ('Timing', {
            'fields': ('created_at', 'last_charged_at', 'next_charge_at')
        }),
        ('Provider Response', {
            'fields': ('provider_response',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UPIMandateExecution)
class UPIMandateExecutionAdmin(admin.ModelAdmin):
    """Mandate Execution admin"""
    list_display = [
        'mandate', 'execution_date', 'amount', 'trigger_type',
        'retry_count', 'created_at'
    ]
    list_filter = ['trigger_type', 'execution_date', 'created_at']
    search_fields = ['mandate__mandate_ref']
    
    fieldsets = (
        ('Execution Details', {
            'fields': ('mandate', 'transaction', 'execution_date', 'amount')
        }),
        ('Trigger & Retry', {
            'fields': ('trigger_type', 'retry_count', 'next_retry_at')
        }),
    )


@admin.register(UPIRefund)
class UPIRefundAdmin(admin.ModelAdmin):
    """UPI Refund admin"""
    list_display = [
        'refund_ref', 'original_transaction', 'refund_amount',
        'status', 'initiated_at', 'processed_at'
    ]
    list_filter = ['status', 'initiated_at', 'processed_at']
    search_fields = ['refund_ref', 'original_transaction__txn_ref']
    readonly_fields = [
        'refund_ref', 'provider_refund_id', 'initiated_at', 
        'processed_at', 'provider_response'
    ]
    
    fieldsets = (
        ('Refund Details', {
            'fields': ('refund_ref', 'provider_refund_id', 'original_transaction')
        }),
        ('Refund Info', {
            'fields': ('refund_amount', 'reason')
        }),
        ('Status & Timing', {
            'fields': ('status', 'failure_reason', 'initiated_at', 'processed_at')
        }),
        ('Provider Response', {
            'fields': ('provider_response',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UPIWebhookLog)
class UPIWebhookLogAdmin(admin.ModelAdmin):
    """Webhook Log admin"""
    list_display = [
        'provider', 'event_type', 'transaction', 'is_processed',
        'received_at', 'processed_at'
    ]
    list_filter = ['provider', 'event_type', 'is_processed', 'received_at']
    search_fields = ['event_type', 'transaction__txn_ref']
    readonly_fields = [
        'provider', 'event_type', 'transaction', 'headers', 'payload',
        'signature', 'received_at', 'processed_at'
    ]
    
    fieldsets = (
        ('Webhook Info', {
            'fields': ('provider', 'event_type', 'transaction')
        }),
        ('Processing', {
            'fields': ('is_processed', 'processing_error', 'received_at', 'processed_at')
        }),
        ('Webhook Data', {
            'fields': ('headers', 'payload', 'signature'),
            'classes': ('collapse',)
        }),
    )