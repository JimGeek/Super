"""
Settlement and Ledger models for SUPER platform
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class LedgerAccount(models.Model):
    """
    Ledger accounts for double-entry bookkeeping
    """
    ACCOUNT_TYPES = [
        ('platform', 'Platform Account'),
        ('merchant', 'Merchant Account'),
        ('consumer', 'Consumer Wallet'),
        ('rider', 'Rider Earnings'),
        ('ads', 'Ads Wallet'),
        ('escrow', 'Escrow Account'),
        ('commission', 'Commission Account'),
        ('refund', 'Refund Account'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Account Details
    account_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    
    # Associated Entity
    org_id = models.UUIDField(blank=True, null=True, help_text="Organization ID")
    user_id = models.UUIDField(blank=True, null=True, help_text="User ID")
    
    # Balance Tracking
    current_balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Constraints
    minimum_balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    maximum_balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ledger_accounts'
        indexes = [
            models.Index(fields=['type', 'is_active']),
            models.Index(fields=['org_id', 'type']),
            models.Index(fields=['user_id', 'type']),
        ]
    
    def __str__(self):
        return f"{self.account_number} - {self.name}"
    
    def get_balance(self):
        """Calculate current balance from entries"""
        from django.db.models import Sum, Q
        
        debits = LedgerEntry.objects.filter(
            debit_account=self
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        credits = LedgerEntry.objects.filter(
            credit_account=self
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # For asset/expense accounts: balance = debits - credits
        # For liability/income/equity accounts: balance = credits - debits
        if self.type in ['platform', 'commission']:
            balance = credits - debits
        else:
            balance = debits - credits
        
        return balance
    
    def update_balance(self):
        """Update cached balance"""
        self.current_balance = self.get_balance()
        self.save(update_fields=['current_balance', 'updated_at'])


class LedgerEntry(models.Model):
    """
    Individual ledger entries for double-entry bookkeeping
    """
    ENTRY_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('commission', 'Commission'),
        ('settlement', 'Settlement'),
        ('reward', 'Reward'),
        ('adjustment', 'Adjustment'),
        ('fee', 'Platform Fee'),
        ('ads_spend', 'Ads Spending'),
        ('ads_topup', 'Ads Top-up'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Double Entry
    debit_account = models.ForeignKey(
        LedgerAccount, 
        on_delete=models.PROTECT,
        related_name='debit_entries'
    )
    credit_account = models.ForeignKey(
        LedgerAccount, 
        on_delete=models.PROTECT,
        related_name='credit_entries'
    )
    
    # Amount
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Entry Details
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    description = models.CharField(max_length=500)
    
    # Reference to source transaction/object
    reference_type = models.CharField(max_length=50)  # e.g., 'upi_transaction', 'order'
    reference_id = models.UUIDField()
    
    # Metadata
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ledger_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Settlement tracking
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'ledger_entries'
        indexes = [
            models.Index(fields=['entry_type', 'created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
            models.Index(fields=['debit_account', 'created_at']),
            models.Index(fields=['credit_account', 'created_at']),
            models.Index(fields=['is_settled', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.entry_type} - {self.amount} - {self.description}"


class Settlement(models.Model):
    """
    Settlement records for payouts to merchants
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    SETTLEMENT_TYPES = [
        ('merchant_payout', 'Merchant Payout'),
        ('rider_payout', 'Rider Payout'),
        ('refund_payout', 'Refund Payout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Settlement Details
    settlement_ref = models.CharField(max_length=100, unique=True)
    settlement_type = models.CharField(max_length=20, choices=SETTLEMENT_TYPES)
    
    # Associated Accounts
    from_account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name='outgoing_settlements'
    )
    to_account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name='incoming_settlements'
    )
    
    # Amount Details
    gross_amount = models.DecimalField(max_digits=15, decimal_places=2)
    commission_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    platform_fee = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    net_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Payout Details
    payout_method = models.CharField(
        max_length=20,
        choices=[
            ('upi', 'UPI Transfer'),
            ('bank', 'Bank Transfer'),
            ('wallet', 'Wallet Credit'),
        ],
        default='upi'
    )
    payout_vpa = models.CharField(max_length=255, blank=True)
    payout_account_number = models.CharField(max_length=50, blank=True)
    payout_ifsc = models.CharField(max_length=11, blank=True)
    
    # Status & Timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason = models.TextField(blank=True)
    
    # Related Entries
    ledger_entries = models.ManyToManyField(
        LedgerEntry,
        related_name='settlements',
        blank=True
    )
    
    # Processing Details
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='processed_settlements'
    )
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField()
    processed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'settlements'
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['settlement_type', 'created_at']),
            models.Index(fields=['from_account', 'status']),
            models.Index(fields=['to_account', 'status']),
        ]
    
    def __str__(self):
        return f"Settlement {self.settlement_ref} - {self.net_amount}"


class SettlementSchedule(models.Model):
    """
    Settlement schedules for organizations
    """
    FREQUENCY_CHOICES = [
        ('instant', 'Instant (T+0)'),
        ('daily', 'Daily (T+1)'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Organization
    organization = models.OneToOneField(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='settlement_schedule'
    )
    
    # Schedule Settings
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    minimum_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('100.00')
    )
    
    # Settlement Days (for weekly/monthly)
    settlement_day = models.IntegerField(
        blank=True, 
        null=True,
        help_text="Day of week (0=Monday) or day of month"
    )
    
    # Payout Configuration
    payout_method = models.CharField(
        max_length=20,
        choices=[
            ('upi', 'UPI Transfer'),
            ('bank', 'Bank Transfer'),
        ],
        default='upi'
    )
    payout_vpa = models.CharField(max_length=255, blank=True)
    payout_account_number = models.CharField(max_length=50, blank=True)
    payout_ifsc = models.CharField(max_length=11, blank=True)
    payout_account_name = models.CharField(max_length=255, blank=True)
    
    # Settings
    auto_settlement = models.BooleanField(default=True)
    hold_settlements = models.BooleanField(default=False)
    
    # Timing
    last_settlement_at = models.DateTimeField(blank=True, null=True)
    next_settlement_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'settlement_schedules'
    
    def __str__(self):
        return f"{self.organization.name} - {self.frequency}"


class SettlementHold(models.Model):
    """
    Holds on settlements due to disputes or compliance
    """
    HOLD_TYPES = [
        ('dispute', 'Dispute Hold'),
        ('compliance', 'Compliance Hold'),
        ('manual', 'Manual Hold'),
        ('risk', 'Risk Management Hold'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Hold Details
    account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.CASCADE,
        related_name='holds'
    )
    
    hold_type = models.CharField(max_length=20, choices=HOLD_TYPES)
    hold_amount = models.DecimalField(max_digits=15, decimal_places=2)
    reason = models.TextField()
    
    # Associated Records
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.UUIDField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timing
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(blank=True, null=True)
    released_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='released_holds'
    )
    
    class Meta:
        db_table = 'settlement_holds'
        indexes = [
            models.Index(fields=['account', 'is_active']),
            models.Index(fields=['hold_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"Hold {self.hold_type} - {self.hold_amount} on {self.account}"


class ReconciliationRecord(models.Model):
    """
    Records for payment reconciliation
    """
    STATUS_CHOICES = [
        ('matched', 'Matched'),
        ('unmatched', 'Unmatched'),
        ('dispute', 'In Dispute'),
        ('resolved', 'Resolved'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Transaction References
    internal_ref = models.CharField(max_length=100)  # Our transaction reference
    external_ref = models.CharField(max_length=100)  # Provider/Bank reference
    
    # Amount Details
    internal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    external_amount = models.DecimalField(max_digits=15, decimal_places=2)
    variance_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Reconciliation Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unmatched')
    reconciled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reconciled_records'
    )
    
    # Associated Records
    upi_transaction = models.ForeignKey(
        'payments_upi.UPITransaction',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reconciliation_records'
    )
    ledger_entry = models.ForeignKey(
        LedgerEntry,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reconciliation_records'
    )
    
    # External Data
    external_data = models.JSONField(default=dict)
    
    # Timing
    transaction_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    reconciled_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'reconciliation_records'
        indexes = [
            models.Index(fields=['status', 'transaction_date']),
            models.Index(fields=['internal_ref']),
            models.Index(fields=['external_ref']),
        ]
    
    def __str__(self):
        return f"Recon {self.internal_ref} - {self.status}"