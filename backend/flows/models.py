"""
Flow Designer models for SUPER platform
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()


class Flow(models.Model):
    """
    Main flow definition for different verticals
    """
    FLOW_TYPES = [
        ('order_flow', 'Order Flow'),
        ('service_flow', 'Service Flow'),
        ('subscription_flow', 'Subscription Flow'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
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
    
    # Flow Details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    flow_type = models.CharField(max_length=20, choices=FLOW_TYPES)
    vertical = models.CharField(max_length=20, choices=VERTICALS)
    
    # Version Control
    version = models.CharField(max_length=20, default='1.0.0')
    is_default = models.BooleanField(default=False)
    
    # Flow Schema (JSON)
    schema = models.JSONField(
        help_text="JSON schema defining the flow steps and structure"
    )
    
    # UI Schema (for rendering)
    ui_schema = models.JSONField(
        default=dict,
        help_text="UI-specific schema for form rendering"
    )
    
    # Validation Rules
    validation_rules = models.JSONField(
        default=list,
        help_text="Validation rules for the flow"
    )
    
    # Localization
    translations = models.JSONField(
        default=dict,
        help_text="Translations for different languages"
    )
    
    # Targeting
    target_cities = models.JSONField(
        default=list,
        help_text="Cities where this flow is active"
    )
    merchant_segments = models.JSONField(
        default=list,
        help_text="Merchant segments that use this flow"
    )
    
    # A/B Testing
    ab_test_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text="Percentage of users who see this flow (for A/B testing)"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_flows'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_flows'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'flows'
        unique_together = [['vertical', 'version', 'is_default']]
        indexes = [
            models.Index(fields=['vertical', 'status']),
            models.Index(fields=['flow_type', 'status']),
            models.Index(fields=['status', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.vertical})"


class FlowStep(models.Model):
    """
    Individual steps within a flow
    """
    STEP_TYPES = [
        ('form', 'Form Input'),
        ('display', 'Information Display'),
        ('selection', 'Option Selection'),
        ('confirmation', 'Confirmation Step'),
        ('payment', 'Payment Step'),
        ('scheduling', 'Scheduling Step'),
        ('address', 'Address Selection'),
        ('file_upload', 'File Upload'),
        ('signature', 'Digital Signature'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='steps')
    
    # Step Details
    step_key = models.CharField(
        max_length=100,
        validators=[RegexValidator(r'^[a-zA-Z0-9_]+$')]
    )
    step_name = models.CharField(max_length=255)
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    
    # Ordering
    order = models.IntegerField(default=0)
    
    # Step Configuration
    config = models.JSONField(
        default=dict,
        help_text="Step-specific configuration"
    )
    
    # Form Schema (for form-type steps)
    form_schema = models.JSONField(
        default=dict,
        help_text="JSON Schema for form validation"
    )
    
    # UI Configuration
    ui_config = models.JSONField(
        default=dict,
        help_text="UI rendering configuration"
    )
    
    # Conditional Logic
    show_condition = models.JSONField(
        default=dict,
        help_text="Conditions for showing this step"
    )
    
    # Validation Rules
    validation_rules = models.JSONField(
        default=list,
        help_text="Step-specific validation rules"
    )
    
    # Navigation
    next_step_logic = models.JSONField(
        default=dict,
        help_text="Logic for determining next step"
    )
    
    # Required/Optional
    is_required = models.BooleanField(default=True)
    is_skippable = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'flow_steps'
        unique_together = [['flow', 'step_key']]
        ordering = ['order', 'step_key']
        indexes = [
            models.Index(fields=['flow', 'order']),
            models.Index(fields=['step_type']),
        ]
    
    def __str__(self):
        return f"{self.flow.name} - {self.step_name}"


class FlowExecution(models.Model):
    """
    Track individual flow executions by users
    """
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Flow & User
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='executions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flow_executions')
    
    # Organization (if applicable)
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='flow_executions'
    )
    
    # Execution Details
    execution_context = models.JSONField(
        default=dict,
        help_text="Context data for this execution"
    )
    
    # Current State
    current_step = models.ForeignKey(
        FlowStep,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='current_executions'
    )
    
    # Collected Data
    collected_data = models.JSONField(
        default=dict,
        help_text="Data collected from user during flow execution"
    )
    
    # Progress Tracking
    completed_steps = models.JSONField(
        default=list,
        help_text="List of completed step keys"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00
    )
    
    # Result
    result_data = models.JSONField(
        default=dict,
        help_text="Final result data after completion"
    )
    
    # Associated Objects
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='flow_executions'
    )
    
    # Session tracking
    session_id = models.CharField(max_length=255, blank=True)
    device_info = models.JSONField(default=dict)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'flow_executions'
        indexes = [
            models.Index(fields=['flow', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'started_at']),
        ]
    
    def __str__(self):
        return f"{self.flow.name} execution by {self.user.get_full_name()}"


class FlowStepExecution(models.Model):
    """
    Track individual step executions within a flow
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # References
    flow_execution = models.ForeignKey(
        FlowExecution,
        on_delete=models.CASCADE,
        related_name='step_executions'
    )
    step = models.ForeignKey(FlowStep, on_delete=models.CASCADE)
    
    # Step Data
    input_data = models.JSONField(
        default=dict,
        help_text="Data submitted for this step"
    )
    
    # Validation Results
    validation_errors = models.JSONField(
        default=list,
        help_text="Validation errors encountered"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    duration_seconds = models.IntegerField(blank=True, null=True)
    
    # Retry tracking
    attempt_number = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'flow_step_executions'
        unique_together = [['flow_execution', 'step']]
        indexes = [
            models.Index(fields=['flow_execution', 'status']),
            models.Index(fields=['step', 'status']),
        ]
    
    def __str__(self):
        return f"{self.step.step_name} - {self.status}"


class FlowTemplate(models.Model):
    """
    Pre-built flow templates for different verticals
    """
    TEMPLATE_CATEGORIES = [
        ('basic', 'Basic Templates'),
        ('advanced', 'Advanced Templates'),
        ('premium', 'Premium Templates'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template Details
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=TEMPLATE_CATEGORIES)
    
    # Vertical
    vertical = models.CharField(max_length=20, choices=Flow.VERTICALS)
    
    # Template Data
    template_data = models.JSONField(
        help_text="Complete flow template with steps and configuration"
    )
    
    # Preview
    preview_images = models.JSONField(
        default=list,
        help_text="URLs to preview images"
    )
    
    # Features
    features = models.JSONField(
        default=list,
        help_text="List of features this template provides"
    )
    
    # Pricing
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    
    # Usage Stats
    usage_count = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'flow_templates'
        indexes = [
            models.Index(fields=['vertical', 'category', 'is_active']),
            models.Index(fields=['is_active', 'usage_count']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.vertical}"


class FlowAnalytics(models.Model):
    """
    Analytics data for flows
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Flow reference
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='analytics')
    
    # Date
    date = models.DateField()
    
    # Metrics
    total_starts = models.IntegerField(default=0)
    total_completions = models.IntegerField(default=0)
    total_abandons = models.IntegerField(default=0)
    
    # Conversion rates
    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00
    )
    abandon_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00
    )
    
    # Time metrics
    average_completion_time = models.IntegerField(
        default=0,
        help_text="Average completion time in seconds"
    )
    
    # Step-wise metrics
    step_metrics = models.JSONField(
        default=dict,
        help_text="Per-step analytics data"
    )
    
    # Device/Platform breakdown
    device_breakdown = models.JSONField(
        default=dict,
        help_text="Breakdown by device type"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'flow_analytics'
        unique_together = [['flow', 'date']]
        indexes = [
            models.Index(fields=['flow', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.flow.name} analytics - {self.date}"