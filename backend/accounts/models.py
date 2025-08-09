"""
User and Organization models for SUPER platform
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models
from django.core.validators import RegexValidator
from phonenumber_field.modelfields import PhoneNumberField


class Organization(models.Model):
    """
    Organization/Merchant entity
    """
    MERCHANT_TYPES = [
        ('kirana', 'Kirana Store'),
        ('barber', 'Barber/Salon'),
        ('garage', 'Auto Service'),
        ('water_purifier', 'Water Purifier'),
        ('pharmacy', 'Pharmacy'),
        ('restaurant', 'Restaurant'),
        ('grocery', 'Grocery'),
        ('electronics', 'Electronics'),
        ('other', 'Other')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=50, choices=MERCHANT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Business Details
    registration_number = models.CharField(max_length=50, blank=True)
    gstin = models.CharField(
        max_length=15, 
        blank=True,
        validators=[RegexValidator(r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$')]
    )
    
    # Contact Information
    email = models.EmailField()
    phone = PhoneNumberField()
    
    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    location = models.PointField(blank=True, null=True)
    
    # Service Area
    delivery_radius = models.FloatField(default=5.0, help_text="Delivery radius in KM")
    service_zones = models.JSONField(default=list, help_text="List of serviceable pin codes")
    
    # Business Hours
    business_hours = models.JSONField(
        default=dict,
        help_text="Business hours by day: {'monday': {'open': '09:00', 'close': '18:00'}}"
    )
    
    # Platform Settings
    platform_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.50)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        indexes = [
            models.Index(fields=['business_type', 'status']),
            models.Index(fields=['city', 'status']),
        ]
    
    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('mid_admin', 'Mid Admin'),
        ('merchant_owner', 'Merchant Owner'),
        ('merchant_staff', 'Merchant Staff'),
        ('dispatcher', 'Dispatcher'),
        ('rider', 'Rider'),
        ('consumer', 'Consumer'),
    ]
    
    USER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('corporate', 'Corporate'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Override email to be unique and required
    email = models.EmailField(unique=True)
    phone = PhoneNumberField(unique=True)
    
    # User Profile
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='consumer')
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='individual')
    
    # Organization relationship
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='users',
        blank=True,
        null=True
    )
    
    # Profile Information
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10, 
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        blank=True
    )
    
    # Preferences
    preferred_language = models.CharField(max_length=5, default='en')
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    
    # Corporate Details (for corporate users)
    company_name = models.CharField(max_length=255, blank=True)
    company_gstin = models.CharField(max_length=15, blank=True)
    
    # Security
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    last_location = models.PointField(blank=True, null=True)
    device_tokens = models.JSONField(default=list, help_text="FCM tokens for push notifications")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Use email as username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['organization', 'role']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    @property
    def full_name(self):
        return self.get_full_name()


class UserAddress(models.Model):
    """
    Multiple addresses for users
    """
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    
    label = models.CharField(max_length=50)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES)
    
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    landmark = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    location = models.PointField()
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_addresses'
        unique_together = [['user', 'is_default']]
    
    def __str__(self):
        return f"{self.label} - {self.user.get_full_name()}"


class OTPVerification(models.Model):
    """
    OTP verification for phone and email
    """
    VERIFICATION_TYPES = [
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('login', 'Login'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    
    verification_type = models.CharField(max_length=10, choices=VERIFICATION_TYPES)
    identifier = models.CharField(max_length=255)  # phone number or email
    otp = models.CharField(max_length=6)
    
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'otp_verifications'
        indexes = [
            models.Index(fields=['identifier', 'verification_type', 'is_verified']),
        ]
    
    def __str__(self):
        return f"OTP for {self.identifier} ({self.verification_type})"


class UserSession(models.Model):
    """
    User session tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    
    device_id = models.CharField(max_length=255)
    device_name = models.CharField(max_length=255, blank=True)
    platform = models.CharField(max_length=50)  # web, android, ios
    app_version = models.CharField(max_length=20, blank=True)
    
    ip_address = models.GenericIPAddressField()
    location = models.PointField(blank=True, null=True)
    
    refresh_token = models.TextField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['refresh_token']),
        ]
    
    def __str__(self):
        return f"Session for {self.user.email} on {self.platform}"