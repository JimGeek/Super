"""
UPI Payment models for SUPER platform
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()


class UPIProvider(models.Model):
    """UPI service provider configuration"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    
    # API Configuration
    base_url = models.URLField()
    api_key = models.CharField(max_length=255)
    secret_key = models.CharField(max_length=255)
    webhook_secret = models.CharField(max_length=255)
    
    # Capabilities
    supports_intent = models.BooleanField(default=True)
    supports_collect = models.BooleanField(default=True)
    supports_qr = models.BooleanField(default=True)
    supports_mandates = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_production = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'upi_providers'
    
    def __str__(self):
        return self.name


class VirtualPaymentAddress(models.Model):
    """VPA (Virtual Payment Address) management"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # VPA Details
    vpa = models.CharField(
        max_length=255, 
        unique=True,
        validators=[RegexValidator(r'^[\w.-]+@[\w.-]+$')]
    )
    holder_name = models.CharField(max_length=255)
    
    # Association
    organization = models.ForeignKey(
        'accounts.Organization', 
        on_delete=models.CASCADE, 
        related_name='vpas',
        blank=True,
        null=True
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='vpas',
        blank=True,
        null=True
    )
    
    # Purpose
    PURPOSE_CHOICES = [
        ('merchant', 'Merchant Collection'),
        ('platform', 'Platform Collection'),
        ('settlement', 'Settlement Payout'),
    ]
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    
    # Provider
    provider = models.ForeignKey(UPIProvider, on_delete=models.CASCADE)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'virtual_payment_addresses'
        unique_together = [['organization', 'purpose'], ['user', 'purpose']]
    
    def __str__(self):
        return f"{self.vpa} ({self.purpose})"


class UPITransaction(models.Model):
    """UPI payment transaction records"""
    
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('settlement', 'Settlement'),
        ('mandate', 'Mandate'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Transaction Details
    txn_ref = models.CharField(max_length=100, unique=True)
    provider_txn_id = models.CharField(max_length=255, blank=True)
    upi_txn_id = models.CharField(max_length=255, blank=True)  # UPI transaction ID from NPCI
    
    # Amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    # VPAs
    payer_vpa = models.CharField(max_length=255)
    payee_vpa = models.CharField(max_length=255)
    
    # Associated Records
    order = models.ForeignKey(
        'orders.Order', 
        on_delete=models.SET_NULL, 
        related_name='upi_transactions',
        blank=True,
        null=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='upi_transactions')
    organization = models.ForeignKey(
        'accounts.Organization', 
        on_delete=models.CASCADE, 
        related_name='upi_transactions',
        blank=True,
        null=True
    )
    
    # Transaction Metadata
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='payment')
    description = models.CharField(max_length=255)
    
    # Provider & Method
    provider = models.ForeignKey(UPIProvider, on_delete=models.CASCADE)
    payment_method = models.CharField(
        max_length=20,
        choices=[('intent', 'Intent'), ('collect', 'Collect'), ('qr', 'QR')],
        default='intent'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    failure_reason = models.TextField(blank=True)
    
    # Webhook & Reconciliation
    webhook_received = models.BooleanField(default=False)
    reconciled = models.BooleanField(default=False)
    reconciliation_ref = models.CharField(max_length=255, blank=True)
    
    # Timing
    initiated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Provider Response
    provider_response = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'upi_transactions'
        indexes = [
            models.Index(fields=['status', 'transaction_type']),
            models.Index(fields=['provider_txn_id']),
            models.Index(fields=['upi_txn_id']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['reconciled', 'status']),
        ]
    
    def __str__(self):
        return f"UPI {self.transaction_type} - {self.txn_ref} - {self.amount}"


class UPIMandate(models.Model):
    """UPI Mandate (Auto-pay) management"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]
    
    PURPOSE_CHOICES = [
        ('subscription', 'Subscription Plan'),
        ('ads_wallet', 'Ads Wallet Top-up'),
        ('emi', 'EMI Payment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Mandate Details
    mandate_ref = models.CharField(max_length=100, unique=True)
    provider_mandate_id = models.CharField(max_length=255, blank=True)
    
    # Payer & Payee
    payer_vpa = models.CharField(max_length=255)
    payee_vpa = models.CharField(max_length=255)
    
    # Associated Records
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='upi_mandates')
    organization = models.ForeignKey(
        'accounts.Organization', 
        on_delete=models.CASCADE, 
        related_name='upi_mandates'
    )
    
    # Mandate Terms
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    description = models.CharField(max_length=255)
    
    # Amount Limits
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
            ('as_required', 'As Required'),
        ],
        default='monthly'
    )
    
    # Schedule
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    
    # Auto-charge settings (for threshold-based top-ups)
    auto_charge_threshold = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True
    )
    auto_charge_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Provider
    provider = models.ForeignKey(UPIProvider, on_delete=models.CASCADE)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    last_charged_at = models.DateTimeField(blank=True, null=True)
    next_charge_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    provider_response = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'upi_mandates'
        indexes = [
            models.Index(fields=['status', 'next_charge_at']),
            models.Index(fields=['organization', 'purpose']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"Mandate {self.mandate_ref} - {self.purpose}"


class UPIMandateExecution(models.Model):
    """Individual mandate execution records"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mandate = models.ForeignKey(UPIMandate, on_delete=models.CASCADE, related_name='executions')
    transaction = models.OneToOneField(
        UPITransaction, 
        on_delete=models.CASCADE, 
        related_name='mandate_execution'
    )
    
    # Execution Details
    execution_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Trigger
    trigger_type = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('threshold', 'Threshold Based'),
            ('manual', 'Manual'),
        ],
        default='scheduled'
    )
    
    # Retry Logic
    retry_count = models.IntegerField(default=0)
    next_retry_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'upi_mandate_executions'
    
    def __str__(self):
        return f"Execution {self.mandate.mandate_ref} - {self.execution_date}"


class UPIRefund(models.Model):
    """UPI refund management"""
    
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Refund Details
    refund_ref = models.CharField(max_length=100, unique=True)
    provider_refund_id = models.CharField(max_length=255, blank=True)
    
    # Original Transaction
    original_transaction = models.ForeignKey(
        UPITransaction, 
        on_delete=models.CASCADE, 
        related_name='refunds'
    )
    
    # Refund Amount
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    failure_reason = models.TextField(blank=True)
    
    # Timing
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    provider_response = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'upi_refunds'
    
    def __str__(self):
        return f"Refund {self.refund_ref} - {self.refund_amount}"


class UPIWebhookLog(models.Model):
    """Log all webhook events for debugging and audit"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Provider & Event
    provider = models.ForeignKey(UPIProvider, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=100)
    
    # Related Transaction
    transaction = models.ForeignKey(
        UPITransaction, 
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    
    # Webhook Data
    headers = models.JSONField(default=dict)
    payload = models.JSONField(default=dict)
    signature = models.TextField(blank=True)
    
    # Processing
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    # Timing
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'upi_webhook_logs'
        indexes = [
            models.Index(fields=['provider', 'event_type']),
            models.Index(fields=['is_processed', 'received_at']),
        ]
    
    def __str__(self):
        return f"Webhook {self.provider.name} - {self.event_type}"