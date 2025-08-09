"""
Serializers for UPI payments app
"""
from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .models import (
    UPIProvider, VirtualPaymentAddress, UPITransaction, 
    UPIMandate, UPIMandateExecution, UPIRefund, UPIWebhookLog
)


class UPIProviderSerializer(serializers.ModelSerializer):
    """Serializer for UPI Provider"""
    
    class Meta:
        model = UPIProvider
        fields = [
            'id', 'name', 'code', 'supports_intent', 'supports_collect',
            'supports_qr', 'supports_mandates', 'is_active', 'is_production'
        ]
        read_only_fields = ['id']


class VirtualPaymentAddressSerializer(serializers.ModelSerializer):
    """Serializer for VPA"""
    
    class Meta:
        model = VirtualPaymentAddress
        fields = [
            'id', 'vpa', 'holder_name', 'purpose', 'is_active', 'is_verified'
        ]
        read_only_fields = ['id', 'is_verified']


class UPITransactionSerializer(serializers.ModelSerializer):
    """Serializer for UPI Transaction"""
    
    class Meta:
        model = UPITransaction
        fields = [
            'id', 'txn_ref', 'provider_txn_id', 'upi_txn_id', 'amount', 
            'currency', 'payer_vpa', 'payee_vpa', 'transaction_type', 
            'description', 'payment_method', 'status', 'failure_reason',
            'initiated_at', 'expires_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'txn_ref', 'provider_txn_id', 'upi_txn_id', 'status',
            'failure_reason', 'initiated_at', 'completed_at'
        ]


class UPIMandateSerializer(serializers.ModelSerializer):
    """Serializer for UPI Mandate"""
    
    class Meta:
        model = UPIMandate
        fields = [
            'id', 'mandate_ref', 'purpose', 'description', 'max_amount',
            'frequency', 'start_date', 'end_date', 'auto_charge_threshold',
            'auto_charge_amount', 'status', 'created_at', 'last_charged_at',
            'next_charge_at'
        ]
        read_only_fields = [
            'id', 'mandate_ref', 'status', 'created_at', 'last_charged_at',
            'next_charge_at'
        ]


class PaymentInitiateSerializer(serializers.Serializer):
    """Serializer for initiating payment"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
    description = serializers.CharField(max_length=255)
    payment_method = serializers.ChoiceField(choices=['intent', 'collect', 'qr'])
    order_id = serializers.UUIDField(required=False)
    success_url = serializers.URLField(required=False)
    failure_url = serializers.URLField(required=False)


class PaymentResponseSerializer(serializers.Serializer):
    """Serializer for payment response"""
    txn_ref = serializers.CharField()
    payment_url = serializers.URLField(required=False)
    intent_url = serializers.CharField(required=False)
    qr_code = serializers.CharField(required=False)
    expires_at = serializers.DateTimeField()


class MandateCreateSerializer(serializers.Serializer):
    """Serializer for creating mandate"""
    purpose = serializers.ChoiceField(choices=UPIMandate.PURPOSE_CHOICES)
    description = serializers.CharField(max_length=255)
    max_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    frequency = serializers.ChoiceField(choices=[
        'daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'as_required'
    ])
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False)
    auto_charge_threshold = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    auto_charge_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )


class RefundCreateSerializer(serializers.Serializer):
    """Serializer for creating refund"""
    transaction_id = serializers.UUIDField()
    refund_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.CharField(max_length=255)
    
    def validate_transaction_id(self, value):
        try:
            transaction = UPITransaction.objects.get(id=value, status='success')
            return value
        except UPITransaction.DoesNotExist:
            raise serializers.ValidationError("Valid successful transaction required")
    
    def validate(self, attrs):
        transaction = UPITransaction.objects.get(id=attrs['transaction_id'])
        refund_amount = attrs['refund_amount']
        
        # Check if refund amount doesn't exceed transaction amount
        total_refunded = sum(
            r.refund_amount for r in transaction.refunds.filter(status='success')
        )
        
        if total_refunded + refund_amount > transaction.amount:
            raise serializers.ValidationError(
                "Refund amount exceeds available amount"
            )
        
        return attrs


class UPIRefundSerializer(serializers.ModelSerializer):
    """Serializer for UPI Refund"""
    
    class Meta:
        model = UPIRefund
        fields = [
            'id', 'refund_ref', 'refund_amount', 'reason', 'status',
            'failure_reason', 'initiated_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'refund_ref', 'status', 'failure_reason', 
            'initiated_at', 'processed_at'
        ]


class WebhookEventSerializer(serializers.Serializer):
    """Serializer for webhook events"""
    event_type = serializers.CharField()
    transaction_id = serializers.CharField(required=False)
    mandate_id = serializers.CharField(required=False)
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    timestamp = serializers.DateTimeField()
    signature = serializers.CharField()
    data = serializers.JSONField()