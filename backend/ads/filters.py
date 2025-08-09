import django_filters
from django_filters import rest_framework as filters
from django.db.models import Q
from decimal import Decimal

from .models import (
    AdCampaign, AdCreative, AdImpression, AdClick, AdConversion,
    AdKeyword, AdBudgetSpend, AdReportingData
)


class AdCampaignFilter(filters.FilterSet):
    """Advanced filtering for ad campaigns"""
    
    # Status and type filters
    status = filters.MultipleChoiceFilter(choices=AdCampaign.STATUS_CHOICES)
    campaign_type = filters.MultipleChoiceFilter(choices=AdCampaign.CAMPAIGN_TYPES)
    bidding_strategy = filters.MultipleChoiceFilter(choices=AdCampaign.BIDDING_STRATEGIES)
    
    # Date range filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    start_date_after = filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')
    end_date_after = filters.DateTimeFilter(field_name='end_date', lookup_expr='gte')
    end_date_before = filters.DateTimeFilter(field_name='end_date', lookup_expr='lte')
    
    # Budget filters
    daily_budget_min = filters.NumberFilter(field_name='daily_budget', lookup_expr='gte')
    daily_budget_max = filters.NumberFilter(field_name='daily_budget', lookup_expr='lte')
    total_budget_min = filters.NumberFilter(field_name='total_budget', lookup_expr='gte')
    total_budget_max = filters.NumberFilter(field_name='total_budget', lookup_expr='lte')
    
    # Performance filters
    impressions_min = filters.NumberFilter(field_name='impressions', lookup_expr='gte')
    impressions_max = filters.NumberFilter(field_name='impressions', lookup_expr='lte')
    clicks_min = filters.NumberFilter(field_name='clicks', lookup_expr='gte')
    clicks_max = filters.NumberFilter(field_name='clicks', lookup_expr='lte')
    conversions_min = filters.NumberFilter(field_name='conversions', lookup_expr='gte')
    conversions_max = filters.NumberFilter(field_name='conversions', lookup_expr='lte')
    spend_min = filters.NumberFilter(field_name='spend', lookup_expr='gte')
    spend_max = filters.NumberFilter(field_name='spend', lookup_expr='lte')
    revenue_min = filters.NumberFilter(field_name='revenue', lookup_expr='gte')
    revenue_max = filters.NumberFilter(field_name='revenue', lookup_expr='lte')
    
    # Text search
    search = filters.CharFilter(method='filter_search')
    
    # Advertiser filter
    advertiser = filters.UUIDFilter(field_name='advertiser__id')
    advertiser_name = filters.CharFilter(field_name='advertiser__business_name', lookup_expr='icontains')
    
    # Active campaigns filter
    is_active = filters.BooleanFilter(method='filter_is_active')
    
    # Performance metrics filters
    has_clicks = filters.BooleanFilter(method='filter_has_clicks')
    has_conversions = filters.BooleanFilter(method='filter_has_conversions')
    
    class Meta:
        model = AdCampaign
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(advertiser__business_name__icontains=value)
        )
    
    def filter_is_active(self, queryset, name, value):
        """Filter for currently active campaigns"""
        if value is None:
            return queryset
        
        if value:
            return queryset.filter(
                status='active',
                start_date__lte=django_filters.utils.timezone.now(),
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=django_filters.utils.timezone.now())
            )
        else:
            return queryset.exclude(
                status='active',
                start_date__lte=django_filters.utils.timezone.now(),
            ).exclude(
                Q(end_date__isnull=True) | Q(end_date__gte=django_filters.utils.timezone.now())
            )
    
    def filter_has_clicks(self, queryset, name, value):
        """Filter campaigns with or without clicks"""
        if value is None:
            return queryset
        
        if value:
            return queryset.filter(clicks__gt=0)
        else:
            return queryset.filter(clicks=0)
    
    def filter_has_conversions(self, queryset, name, value):
        """Filter campaigns with or without conversions"""
        if value is None:
            return queryset
        
        if value:
            return queryset.filter(conversions__gt=0)
        else:
            return queryset.filter(conversions=0)


class AdCreativeFilter(filters.FilterSet):
    """Advanced filtering for ad creatives"""
    
    # Basic filters
    status = filters.MultipleChoiceFilter(choices=AdCreative.STATUS_CHOICES)
    creative_type = filters.MultipleChoiceFilter(choices=AdCreative.CREATIVE_TYPES)
    compliance_status = filters.CharFilter()
    
    # Relationship filters
    campaign = filters.UUIDFilter(field_name='ad_group__campaign__id')
    ad_group = filters.UUIDFilter(field_name='ad_group__id')
    
    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Performance filters
    impressions_min = filters.NumberFilter(field_name='impressions', lookup_expr='gte')
    impressions_max = filters.NumberFilter(field_name='impressions', lookup_expr='lte')
    clicks_min = filters.NumberFilter(field_name='clicks', lookup_expr='gte')
    clicks_max = filters.NumberFilter(field_name='clicks', lookup_expr='lte')
    conversions_min = filters.NumberFilter(field_name='conversions', lookup_expr='gte')
    conversions_max = filters.NumberFilter(field_name='conversions', lookup_expr='lte')
    
    # Quality filters
    quality_score_min = filters.NumberFilter(field_name='quality_score', lookup_expr='gte')
    quality_score_max = filters.NumberFilter(field_name='quality_score', lookup_expr='lte')
    
    # Text search
    search = filters.CharFilter(method='filter_search')
    
    # Active creatives
    is_active = filters.BooleanFilter(method='filter_is_active')
    
    class Meta:
        model = AdCreative
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(name__icontains=value) |
            Q(headline__icontains=value) |
            Q(description__icontains=value) |
            Q(ad_group__name__icontains=value) |
            Q(ad_group__campaign__name__icontains=value)
        )
    
    def filter_is_active(self, queryset, name, value):
        """Filter active creatives"""
        if value is None:
            return queryset
        
        if value:
            return queryset.filter(status='active')
        else:
            return queryset.exclude(status='active')


class AdImpressionFilter(filters.FilterSet):
    """Advanced filtering for ad impressions"""
    
    # Relationship filters
    creative = filters.UUIDFilter()
    placement = filters.UUIDFilter()
    campaign = filters.UUIDFilter(field_name='creative__ad_group__campaign__id')
    customer = filters.UUIDFilter()
    
    # Date filters
    served_after = filters.DateTimeFilter(field_name='served_at', lookup_expr='gte')
    served_before = filters.DateTimeFilter(field_name='served_at', lookup_expr='lte')
    served_date = filters.DateFilter(field_name='served_at__date')
    
    # Geographic filters
    country = filters.CharFilter()
    region = filters.CharFilter(lookup_expr='icontains')
    city = filters.CharFilter(lookup_expr='icontains')
    
    # Device filters
    device_type = filters.MultipleChoiceFilter()
    browser = filters.CharFilter(lookup_expr='icontains')
    os = filters.CharFilter(lookup_expr='icontains')
    
    # Cost filters
    cost_min = filters.NumberFilter(field_name='cost', lookup_expr='gte')
    cost_max = filters.NumberFilter(field_name='cost', lookup_expr='lte')
    bid_amount_min = filters.NumberFilter(field_name='bid_amount', lookup_expr='gte')
    bid_amount_max = filters.NumberFilter(field_name='bid_amount', lookup_expr='lte')
    
    # Viewability filters
    viewable = filters.BooleanFilter()
    view_duration_min = filters.NumberFilter(field_name='view_duration', lookup_expr='gte')
    view_duration_max = filters.NumberFilter(field_name='view_duration', lookup_expr='lte')
    
    class Meta:
        model = AdImpression
        fields = []


class AdClickFilter(filters.FilterSet):
    """Advanced filtering for ad clicks"""
    
    # Relationship filters
    creative = filters.UUIDFilter()
    impression = filters.UUIDFilter()
    campaign = filters.UUIDFilter(field_name='creative__ad_group__campaign__id')
    
    # Date filters
    clicked_after = filters.DateTimeFilter(field_name='clicked_at', lookup_expr='gte')
    clicked_before = filters.DateTimeFilter(field_name='clicked_at', lookup_expr='lte')
    clicked_date = filters.DateFilter(field_name='clicked_at__date')
    
    # Validity filters
    is_valid = filters.BooleanFilter()
    fraud_score_min = filters.NumberFilter(field_name='fraud_score', lookup_expr='gte')
    fraud_score_max = filters.NumberFilter(field_name='fraud_score', lookup_expr='lte')
    
    # Cost filters
    cost_min = filters.NumberFilter(field_name='cost', lookup_expr='gte')
    cost_max = filters.NumberFilter(field_name='cost', lookup_expr='lte')
    
    # Time to click filters
    time_to_click_min = filters.NumberFilter(field_name='time_to_click', lookup_expr='gte')
    time_to_click_max = filters.NumberFilter(field_name='time_to_click', lookup_expr='lte')
    
    class Meta:
        model = AdClick
        fields = []


class AdConversionFilter(filters.FilterSet):
    """Advanced filtering for ad conversions"""
    
    # Relationship filters
    creative = filters.UUIDFilter()
    click = filters.UUIDFilter()
    campaign = filters.UUIDFilter(field_name='creative__ad_group__campaign__id')
    order = filters.UUIDFilter()
    
    # Date filters
    converted_after = filters.DateTimeFilter(field_name='converted_at', lookup_expr='gte')
    converted_before = filters.DateTimeFilter(field_name='converted_at', lookup_expr='lte')
    converted_date = filters.DateFilter(field_name='converted_at__date')
    
    # Conversion type filters
    conversion_type = filters.MultipleChoiceFilter(choices=AdConversion.CONVERSION_TYPES)
    
    # Value filters
    conversion_value_min = filters.NumberFilter(field_name='conversion_value', lookup_expr='gte')
    conversion_value_max = filters.NumberFilter(field_name='conversion_value', lookup_expr='lte')
    
    # Attribution filters
    attribution_model = filters.CharFilter()
    
    # Time to conversion filters
    time_to_conversion_min = filters.NumberFilter(field_name='time_to_conversion', lookup_expr='gte')
    time_to_conversion_max = filters.NumberFilter(field_name='time_to_conversion', lookup_expr='lte')
    
    # Verification filters
    is_verified = filters.BooleanFilter()
    verification_method = filters.CharFilter()
    
    class Meta:
        model = AdConversion
        fields = []


class AdKeywordFilter(filters.FilterSet):
    """Advanced filtering for ad keywords"""
    
    # Basic filters
    status = filters.MultipleChoiceFilter(choices=AdKeyword.STATUS_CHOICES)
    match_type = filters.MultipleChoiceFilter(choices=AdKeyword.MATCH_TYPES)
    
    # Relationship filters
    ad_group = filters.UUIDFilter()
    campaign = filters.UUIDFilter(field_name='ad_group__campaign__id')
    
    # Performance filters
    impressions_min = filters.NumberFilter(field_name='impressions', lookup_expr='gte')
    impressions_max = filters.NumberFilter(field_name='impressions', lookup_expr='lte')
    clicks_min = filters.NumberFilter(field_name='clicks', lookup_expr='gte')
    clicks_max = filters.NumberFilter(field_name='clicks', lookup_expr='lte')
    conversions_min = filters.NumberFilter(field_name='conversions', lookup_expr='gte')
    conversions_max = filters.NumberFilter(field_name='conversions', lookup_expr='lte')
    
    # Bid filters
    bid_amount_min = filters.NumberFilter(field_name='bid_amount', lookup_expr='gte')
    bid_amount_max = filters.NumberFilter(field_name='bid_amount', lookup_expr='lte')
    
    # Quality filters
    quality_score_min = filters.NumberFilter(field_name='quality_score', lookup_expr='gte')
    quality_score_max = filters.NumberFilter(field_name='quality_score', lookup_expr='lte')
    
    # Search volume filters
    monthly_searches_min = filters.NumberFilter(field_name='monthly_searches', lookup_expr='gte')
    monthly_searches_max = filters.NumberFilter(field_name='monthly_searches', lookup_expr='lte')
    competition_level = filters.CharFilter()
    
    # Text search
    keyword_text = filters.CharFilter(lookup_expr='icontains')
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = AdKeyword
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search keywords"""
        if not value:
            return queryset
        
        return queryset.filter(keyword_text__icontains=value)


class AdBudgetSpendFilter(filters.FilterSet):
    """Advanced filtering for budget spend data"""
    
    # Relationship filters
    campaign = filters.UUIDFilter()
    
    # Date filters
    spend_date = filters.DateFilter()
    spend_date_after = filters.DateFilter(field_name='spend_date', lookup_expr='gte')
    spend_date_before = filters.DateFilter(field_name='spend_date', lookup_expr='lte')
    
    # Budget filters
    daily_budget_min = filters.NumberFilter(field_name='daily_budget', lookup_expr='gte')
    daily_budget_max = filters.NumberFilter(field_name='daily_budget', lookup_expr='lte')
    total_spend_min = filters.NumberFilter(field_name='total_spend', lookup_expr='gte')
    total_spend_max = filters.NumberFilter(field_name='total_spend', lookup_expr='lte')
    
    # Budget status
    is_budget_exceeded = filters.BooleanFilter()
    
    # Performance filters
    impressions_min = filters.NumberFilter(field_name='impressions', lookup_expr='gte')
    impressions_max = filters.NumberFilter(field_name='impressions', lookup_expr='lte')
    clicks_min = filters.NumberFilter(field_name='clicks', lookup_expr='gte')
    clicks_max = filters.NumberFilter(field_name='clicks', lookup_expr='lte')
    conversions_min = filters.NumberFilter(field_name='conversions', lookup_expr='gte')
    conversions_max = filters.NumberFilter(field_name='conversions', lookup_expr='lte')
    revenue_min = filters.NumberFilter(field_name='revenue', lookup_expr='gte')
    revenue_max = filters.NumberFilter(field_name='revenue', lookup_expr='lte')
    
    class Meta:
        model = AdBudgetSpend
        fields = []


class AdReportingDataFilter(filters.FilterSet):
    """Advanced filtering for reporting data"""
    
    # Relationship filters
    campaign = filters.UUIDFilter()
    
    # Dimension filters
    aggregation_level = filters.MultipleChoiceFilter(choices=AdReportingData.AGGREGATION_LEVELS)
    granularity = filters.MultipleChoiceFilter(choices=AdReportingData.GRANULARITY_CHOICES)
    
    # Date filters
    report_date = filters.DateFilter()
    report_date_after = filters.DateFilter(field_name='report_date', lookup_expr='gte')
    report_date_before = filters.DateFilter(field_name='report_date', lookup_expr='lte')
    report_hour = filters.NumberFilter()
    
    # Performance filters
    impressions_min = filters.NumberFilter(field_name='impressions', lookup_expr='gte')
    impressions_max = filters.NumberFilter(field_name='impressions', lookup_expr='lte')
    clicks_min = filters.NumberFilter(field_name='clicks', lookup_expr='gte')
    clicks_max = filters.NumberFilter(field_name='clicks', lookup_expr='lte')
    conversions_min = filters.NumberFilter(field_name='conversions', lookup_expr='gte')
    conversions_max = filters.NumberFilter(field_name='conversions', lookup_expr='lte')
    spend_min = filters.NumberFilter(field_name='spend', lookup_expr='gte')
    spend_max = filters.NumberFilter(field_name='spend', lookup_expr='lte')
    revenue_min = filters.NumberFilter(field_name='revenue', lookup_expr='gte')
    revenue_max = filters.NumberFilter(field_name='revenue', lookup_expr='lte')
    
    # Calculated metrics filters
    ctr_min = filters.NumberFilter(field_name='ctr', lookup_expr='gte')
    ctr_max = filters.NumberFilter(field_name='ctr', lookup_expr='lte')
    cpc_min = filters.NumberFilter(field_name='cpc', lookup_expr='gte')
    cpc_max = filters.NumberFilter(field_name='cpc', lookup_expr='lte')
    cpa_min = filters.NumberFilter(field_name='cpa', lookup_expr='gte')
    cpa_max = filters.NumberFilter(field_name='cpa', lookup_expr='lte')
    roas_min = filters.NumberFilter(field_name='roas', lookup_expr='gte')
    roas_max = filters.NumberFilter(field_name='roas', lookup_expr='lte')
    
    class Meta:
        model = AdReportingData
        fields = []


class DateRangeFilter(filters.FilterSet):
    """Generic date range filter for time-based analytics"""
    
    # Standard date ranges
    date_from = filters.DateTimeFilter(method='filter_date_from')
    date_to = filters.DateTimeFilter(method='filter_date_to')
    
    # Predefined ranges
    period = filters.ChoiceFilter(
        choices=[
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('last_7_days', 'Last 7 Days'),
            ('last_30_days', 'Last 30 Days'),
            ('last_90_days', 'Last 90 Days'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('this_quarter', 'This Quarter'),
            ('last_quarter', 'Last Quarter'),
            ('this_year', 'This Year'),
            ('last_year', 'Last Year'),
        ],
        method='filter_period'
    )
    
    def filter_date_from(self, queryset, name, value):
        """Filter from date - to be implemented by subclasses"""
        return queryset
    
    def filter_date_to(self, queryset, name, value):
        """Filter to date - to be implemented by subclasses"""
        return queryset
    
    def filter_period(self, queryset, name, value):
        """Filter by predefined period - to be implemented by subclasses"""
        from django.utils import timezone
        from datetime import timedelta
        import calendar
        
        now = timezone.now()
        today = now.date()
        
        if value == 'today':
            start_date = today
            end_date = today
        elif value == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date = yesterday
            end_date = yesterday
        elif value == 'last_7_days':
            start_date = today - timedelta(days=7)
            end_date = today
        elif value == 'last_30_days':
            start_date = today - timedelta(days=30)
            end_date = today
        elif value == 'last_90_days':
            start_date = today - timedelta(days=90)
            end_date = today
        elif value == 'this_month':
            start_date = today.replace(day=1)
            end_date = today
        elif value == 'last_month':
            last_month = today.replace(day=1) - timedelta(days=1)
            start_date = last_month.replace(day=1)
            end_date = last_month
        else:
            return queryset
        
        # This is a base implementation - subclasses should override
        return queryset