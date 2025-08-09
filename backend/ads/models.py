from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import json

from accounts.models import Organization, Customer, Merchant
from orders.models import Order


class AdCategory(models.Model):
    """Categories for ad targeting and classification"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ad_categories')
    
    # Category details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Category configuration
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Targeting attributes
    keywords = models.JSONField(default=list, help_text="Keywords for automatic categorization")
    targeting_attributes = models.JSONField(default=dict, help_text="Additional targeting parameters")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ads_categories'
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['parent']),
        ]
        unique_together = ['organization', 'name']
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.organization.name}"
    
    @property
    def full_path(self):
        """Get full category path"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class AdCampaign(models.Model):
    """Ad campaigns with bidding and targeting configuration"""
    
    CAMPAIGN_TYPES = [
        ('search', 'Search Ads'),
        ('display', 'Display Ads'),
        ('banner', 'Banner Ads'),
        ('sponsored_product', 'Sponsored Products'),
        ('sponsored_merchant', 'Sponsored Merchants'),
        ('native', 'Native Ads'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    BIDDING_STRATEGIES = [
        ('manual_cpc', 'Manual CPC'),
        ('auto_cpc', 'Automatic CPC'),
        ('target_cpa', 'Target CPA'),
        ('target_roas', 'Target ROAS'),
        ('maximize_clicks', 'Maximize Clicks'),
        ('maximize_conversions', 'Maximize Conversions'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ad_campaigns')
    advertiser = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='ad_campaigns')
    
    # Campaign details
    name = models.CharField(max_length=200)
    description = models.TextField()
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Campaign timing
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Bidding configuration
    bidding_strategy = models.CharField(max_length=20, choices=BIDDING_STRATEGIES, default='manual_cpc')
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2)
    total_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Bid amounts
    default_bid = models.DecimalField(max_digits=8, decimal_places=4, help_text="Default bid per click/impression")
    max_bid = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    target_cpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Target cost per acquisition")
    target_roas = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Target return on ad spend %")
    
    # Targeting configuration
    target_categories = models.ManyToManyField(AdCategory, blank=True)
    target_keywords = models.JSONField(default=list, help_text="Target keywords for search ads")
    target_demographics = models.JSONField(default=dict, help_text="Age, gender, interests targeting")
    target_locations = models.JSONField(default=list, help_text="Geographic targeting")
    target_devices = models.JSONField(default=list, help_text="Device targeting")
    target_schedule = models.JSONField(default=dict, help_text="Day/hour scheduling")
    
    # Advanced targeting
    exclude_keywords = models.JSONField(default=list, help_text="Negative keywords")
    exclude_placements = models.JSONField(default=list, help_text="Excluded ad placements")
    audience_targeting = models.JSONField(default=dict, help_text="Custom audience configuration")
    
    # Performance tracking
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    conversions = models.IntegerField(default=0)
    spend = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Campaign settings
    is_evergreen = models.BooleanField(default=False, help_text="Campaign continues indefinitely")
    auto_pause_low_performance = models.BooleanField(default=True)
    enable_dynamic_ads = models.BooleanField(default=False)
    enable_audience_expansion = models.BooleanField(default=False)
    
    # Approval and moderation
    approved_by = models.CharField(max_length=100, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ads_campaigns'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['advertiser', 'status']),
            models.Index(fields=['campaign_type']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.advertiser.business_name}"
    
    @property
    def is_active(self):
        now = timezone.now()
        return (
            self.status == 'active' and
            self.start_date <= now and
            (self.end_date is None or self.end_date >= now) and
            (self.total_budget is None or self.spend < self.total_budget)
        )
    
    @property
    def ctr(self):
        """Click-through rate"""
        if self.impressions == 0:
            return 0.0
        return (self.clicks / self.impressions) * 100
    
    @property
    def cpc(self):
        """Cost per click"""
        if self.clicks == 0:
            return Decimal('0.00')
        return self.spend / self.clicks
    
    @property
    def cpa(self):
        """Cost per acquisition"""
        if self.conversions == 0:
            return Decimal('0.00')
        return self.spend / self.conversions
    
    @property
    def roas(self):
        """Return on ad spend"""
        if self.spend == 0:
            return Decimal('0.00')
        return (self.revenue / self.spend) * 100


class AdGroup(models.Model):
    """Ad groups within campaigns for granular targeting"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('removed', 'Removed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(AdCampaign, on_delete=models.CASCADE, related_name='ad_groups')
    
    # Ad group details
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    # Bidding overrides
    default_bid = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    
    # Targeting overrides
    keywords = models.JSONField(default=list, help_text="Specific keywords for this ad group")
    negative_keywords = models.JSONField(default=list, help_text="Negative keywords for this ad group")
    
    # Performance tracking
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    conversions = models.IntegerField(default=0)
    spend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ads_ad_groups'
        indexes = [
            models.Index(fields=['campaign', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.campaign.name}"
    
    @property
    def effective_bid(self):
        """Get effective bid (ad group or campaign default)"""
        return self.default_bid or self.campaign.default_bid


class AdCreative(models.Model):
    """Ad creatives and content"""
    
    CREATIVE_TYPES = [
        ('text', 'Text Ad'),
        ('image', 'Image Ad'),
        ('video', 'Video Ad'),
        ('carousel', 'Carousel Ad'),
        ('product', 'Product Ad'),
        ('merchant', 'Merchant Ad'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('pending_review', 'Pending Review'),
        ('rejected', 'Rejected'),
        ('removed', 'Removed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad_group = models.ForeignKey(AdGroup, on_delete=models.CASCADE, related_name='creatives')
    
    # Creative details
    name = models.CharField(max_length=200)
    creative_type = models.CharField(max_length=20, choices=CREATIVE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Text content
    headline = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    call_to_action = models.CharField(max_length=50, blank=True)
    
    # Media content
    image_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    
    # Carousel/multi-media
    media_assets = models.JSONField(default=list, help_text="Multiple images/videos for carousel ads")
    
    # Landing page
    destination_url = models.URLField()
    display_url = models.CharField(max_length=200, blank=True)
    
    # Product/Merchant specific
    promoted_products = models.JSONField(default=list, help_text="Product IDs for product ads")
    merchant_info = models.JSONField(default=dict, help_text="Merchant details for merchant ads")
    
    # Creative performance
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    conversions = models.IntegerField(default=0)
    spend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Quality and compliance
    quality_score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    compliance_status = models.CharField(max_length=20, default='pending')
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ads_creatives'
        indexes = [
            models.Index(fields=['ad_group', 'status']),
            models.Index(fields=['creative_type']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.creative_type}"


class AdPlacement(models.Model):
    """Available ad placements across the platform"""
    
    PLACEMENT_TYPES = [
        ('search_results', 'Search Results'),
        ('category_listing', 'Category Listing'),
        ('product_detail', 'Product Detail Page'),
        ('home_banner', 'Home Page Banner'),
        ('checkout', 'Checkout Page'),
        ('order_confirmation', 'Order Confirmation'),
        ('mobile_app_banner', 'Mobile App Banner'),
        ('email_newsletter', 'Email Newsletter'),
        ('push_notification', 'Push Notification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ad_placements')
    
    # Placement details
    name = models.CharField(max_length=100)
    description = models.TextField()
    placement_type = models.CharField(max_length=20, choices=PLACEMENT_TYPES)
    
    # Placement configuration
    dimensions = models.JSONField(default=dict, help_text="Width/height requirements")
    supported_formats = models.JSONField(default=list, help_text="Supported creative formats")
    max_ads_per_page = models.IntegerField(default=1)
    
    # Pricing
    base_cpm = models.DecimalField(max_digits=6, decimal_places=2, help_text="Base cost per thousand impressions")
    base_cpc = models.DecimalField(max_digits=6, decimal_places=4, help_text="Base cost per click")
    minimum_bid = models.DecimalField(max_digits=6, decimal_places=4)
    
    # Targeting restrictions
    allowed_categories = models.ManyToManyField(AdCategory, blank=True)
    content_restrictions = models.JSONField(default=dict, help_text="Content policy restrictions")
    
    # Performance data
    average_ctr = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    average_cpc = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.00'))
    monthly_impressions = models.BigIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ads_placements'
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['placement_type']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.placement_type}"


class AdAuction(models.Model):
    """Real-time ad auction records"""
    
    AUCTION_TYPES = [
        ('first_price', 'First Price Auction'),
        ('second_price', 'Second Price Auction'),
        ('vcg', 'Vickrey-Clarke-Groves'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    placement = models.ForeignKey(AdPlacement, on_delete=models.CASCADE)
    
    # Auction details
    auction_type = models.CharField(max_length=15, choices=AUCTION_TYPES, default='second_price')
    request_id = models.CharField(max_length=100, unique=True)
    
    # Request context
    user_context = models.JSONField(help_text="User demographics, behavior, location")
    page_context = models.JSONField(help_text="Page content, category, search terms")
    device_context = models.JSONField(help_text="Device type, browser, OS")
    
    # Auction participants
    eligible_campaigns = models.JSONField(default=list, help_text="Campaigns that could participate")
    participating_bids = models.JSONField(default=list, help_text="Actual bids submitted")
    
    # Auction results
    winner_creative = models.ForeignKey(AdCreative, on_delete=models.SET_NULL, null=True, blank=True)
    winning_bid = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    clearing_price = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    
    # Auction metrics
    total_eligible = models.IntegerField(default=0)
    total_participating = models.IntegerField(default=0)
    auction_duration_ms = models.IntegerField(default=0)
    
    # Timestamps
    auction_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ads_auctions'
        indexes = [
            models.Index(fields=['organization', 'auction_time']),
            models.Index(fields=['placement', 'auction_time']),
            models.Index(fields=['request_id']),
        ]
    
    def __str__(self):
        return f"Auction {self.request_id} - {self.placement.name}"


class AdImpression(models.Model):
    """Ad impression tracking"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creative = models.ForeignKey(AdCreative, on_delete=models.CASCADE, related_name='impressions')
    placement = models.ForeignKey(AdPlacement, on_delete=models.CASCADE)
    auction = models.ForeignKey(AdAuction, on_delete=models.SET_NULL, null=True, blank=True)
    
    # User context
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100)
    user_agent = models.TextField()
    ip_address = models.GenericIPAddressField()
    
    # Impression details
    impression_id = models.CharField(max_length=100, unique=True)
    page_url = models.URLField()
    referrer_url = models.URLField(blank=True)
    
    # Geographic data
    country = models.CharField(max_length=2, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    location = gis_models.PointField(srid=4326, null=True, blank=True)
    
    # Device information
    device_type = models.CharField(max_length=20, blank=True)  # desktop, mobile, tablet
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    
    # Impression metrics
    viewable = models.BooleanField(default=True)
    view_duration = models.IntegerField(default=0, help_text="View time in milliseconds")
    scroll_depth = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Bidding information
    bid_amount = models.DecimalField(max_digits=8, decimal_places=4)
    cost = models.DecimalField(max_digits=8, decimal_places=4, help_text="Actual cost charged")
    
    # Timestamps
    served_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ads_impressions'
        indexes = [
            models.Index(fields=['creative', 'served_at']),
            models.Index(fields=['placement', 'served_at']),
            models.Index(fields=['customer', 'served_at']),
            models.Index(fields=['impression_id']),
        ]
    
    def __str__(self):
        return f"Impression {self.impression_id}"


class AdClick(models.Model):
    """Ad click tracking"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    impression = models.OneToOneField(AdImpression, on_delete=models.CASCADE, related_name='click')
    creative = models.ForeignKey(AdCreative, on_delete=models.CASCADE, related_name='clicks')
    
    # Click details
    click_id = models.CharField(max_length=100, unique=True)
    destination_url = models.URLField()
    
    # Click context
    click_position = models.JSONField(default=dict, help_text="X,Y coordinates of click")
    time_to_click = models.IntegerField(help_text="Time from impression to click in seconds")
    
    # Fraud detection
    is_valid = models.BooleanField(default=True)
    fraud_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    fraud_reason = models.CharField(max_length=200, blank=True)
    
    # Cost information
    cost = models.DecimalField(max_digits=8, decimal_places=4)
    
    # Timestamps
    clicked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ads_clicks'
        indexes = [
            models.Index(fields=['creative', 'clicked_at']),
            models.Index(fields=['click_id']),
            models.Index(fields=['is_valid']),
        ]
    
    def __str__(self):
        return f"Click {self.click_id}"


class AdConversion(models.Model):
    """Ad conversion tracking"""
    
    CONVERSION_TYPES = [
        ('purchase', 'Purchase'),
        ('signup', 'Sign Up'),
        ('lead', 'Lead Generation'),
        ('app_install', 'App Install'),
        ('page_view', 'Page View'),
        ('add_to_cart', 'Add to Cart'),
        ('custom', 'Custom Event'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    click = models.ForeignKey(AdClick, on_delete=models.CASCADE, related_name='conversions')
    creative = models.ForeignKey(AdCreative, on_delete=models.CASCADE, related_name='conversions')
    
    # Conversion details
    conversion_type = models.CharField(max_length=20, choices=CONVERSION_TYPES)
    conversion_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Attribution
    attribution_model = models.CharField(max_length=50, default='last_click')
    time_to_conversion = models.IntegerField(help_text="Time from click to conversion in minutes")
    
    # Order/transaction reference
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Custom conversion data
    conversion_data = models.JSONField(default=dict, help_text="Additional conversion parameters")
    
    # Validation
    is_verified = models.BooleanField(default=True)
    verification_method = models.CharField(max_length=50, default='automatic')
    
    # Timestamps
    converted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ads_conversions'
        indexes = [
            models.Index(fields=['creative', 'converted_at']),
            models.Index(fields=['conversion_type']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"Conversion {self.conversion_type} - ₹{self.conversion_value}"


class AdBudgetSpend(models.Model):
    """Daily budget and spend tracking"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(AdCampaign, on_delete=models.CASCADE, related_name='daily_spends')
    
    # Date tracking
    spend_date = models.DateField()
    
    # Budget and spend
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2)
    total_spend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Performance metrics
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    conversions = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Budget status
    budget_exhausted_at = models.DateTimeField(null=True, blank=True)
    is_budget_exceeded = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ads_budget_spends'
        indexes = [
            models.Index(fields=['campaign', 'spend_date']),
        ]
        unique_together = ['campaign', 'spend_date']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.spend_date} - ₹{self.total_spend}"
    
    @property
    def budget_utilization(self):
        """Budget utilization percentage"""
        if self.daily_budget == 0:
            return Decimal('0.00')
        return (self.total_spend / self.daily_budget) * 100


class AdKeyword(models.Model):
    """Keyword targeting and bidding"""
    
    MATCH_TYPES = [
        ('exact', 'Exact Match'),
        ('phrase', 'Phrase Match'),
        ('broad', 'Broad Match'),
        ('broad_modifier', 'Broad Match Modifier'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('removed', 'Removed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad_group = models.ForeignKey(AdGroup, on_delete=models.CASCADE, related_name='keywords')
    
    # Keyword details
    keyword_text = models.CharField(max_length=200)
    match_type = models.CharField(max_length=15, choices=MATCH_TYPES, default='broad')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    # Bidding
    bid_amount = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    quality_score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    
    # Performance metrics
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    conversions = models.IntegerField(default=0)
    spend = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # Search volume data
    monthly_searches = models.BigIntegerField(null=True, blank=True)
    competition_level = models.CharField(max_length=10, blank=True)  # low, medium, high
    suggested_bid = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ads_keywords'
        indexes = [
            models.Index(fields=['ad_group', 'status']),
            models.Index(fields=['keyword_text']),
        ]
        unique_together = ['ad_group', 'keyword_text', 'match_type']
    
    def __str__(self):
        return f"{self.keyword_text} ({self.match_type})"
    
    @property
    def effective_bid(self):
        """Get effective bid amount"""
        return self.bid_amount or self.ad_group.effective_bid


class AdAudienceSegment(models.Model):
    """Custom audience segments for targeting"""
    
    SEGMENT_TYPES = [
        ('behavioral', 'Behavioral'),
        ('demographic', 'Demographic'),
        ('interest', 'Interest-based'),
        ('lookalike', 'Lookalike'),
        ('custom', 'Custom Upload'),
        ('remarketing', 'Remarketing'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audience_segments')
    created_by = models.ForeignKey(Merchant, on_delete=models.CASCADE)
    
    # Segment details
    name = models.CharField(max_length=200)
    description = models.TextField()
    segment_type = models.CharField(max_length=20, choices=SEGMENT_TYPES)
    
    # Segment definition
    criteria = models.JSONField(help_text="Segment criteria and rules")
    size_estimate = models.BigIntegerField(default=0)
    
    # Performance data
    avg_ctr = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    avg_conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Status
    is_active = models.BooleanField(default=True)
    last_refreshed = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ads_audience_segments'
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.segment_type})"


class AdReportingData(models.Model):
    """Aggregated reporting data for performance analysis"""
    
    AGGREGATION_LEVELS = [
        ('campaign', 'Campaign'),
        ('ad_group', 'Ad Group'),
        ('creative', 'Creative'),
        ('keyword', 'Keyword'),
        ('placement', 'Placement'),
        ('demographic', 'Demographic'),
        ('geographic', 'Geographic'),
        ('device', 'Device'),
    ]
    
    GRANULARITY_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    campaign = models.ForeignKey(AdCampaign, on_delete=models.CASCADE, related_name='reports')
    
    # Report dimensions
    aggregation_level = models.CharField(max_length=20, choices=AGGREGATION_LEVELS)
    granularity = models.CharField(max_length=10, choices=GRANULARITY_CHOICES)
    dimension_values = models.JSONField(help_text="Values for the aggregation dimension")
    
    # Time period
    report_date = models.DateField()
    report_hour = models.IntegerField(null=True, blank=True)
    
    # Performance metrics
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    conversions = models.IntegerField(default=0)
    spend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Calculated metrics
    ctr = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    cpc = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal('0.00'))
    cpa = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    roas = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ads_reporting_data'
        indexes = [
            models.Index(fields=['organization', 'report_date']),
            models.Index(fields=['campaign', 'aggregation_level', 'report_date']),
        ]
        unique_together = ['campaign', 'aggregation_level', 'granularity', 'report_date', 'report_hour', 'dimension_values']
    
    def __str__(self):
        return f"Report {self.aggregation_level} - {self.report_date}"