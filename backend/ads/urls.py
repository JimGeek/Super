from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls

from .views import (
    AdCategoryViewSet, AdPlacementViewSet, AdCampaignViewSet,
    AdGroupViewSet, AdCreativeViewSet, AdKeywordViewSet,
    AdAudienceSegmentViewSet, AdTrackingViewSet, AdBudgetSpendViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'categories', AdCategoryViewSet, basename='adcategory')
router.register(r'placements', AdPlacementViewSet, basename='adplacement')
router.register(r'campaigns', AdCampaignViewSet, basename='adcampaign')
router.register(r'ad-groups', AdGroupViewSet, basename='adgroup')
router.register(r'creatives', AdCreativeViewSet, basename='adcreative')
router.register(r'keywords', AdKeywordViewSet, basename='adkeyword')
router.register(r'audience-segments', AdAudienceSegmentViewSet, basename='audiencesegment')
router.register(r'budget-spend', AdBudgetSpendViewSet, basename='budgetspend')
router.register(r'tracking', AdTrackingViewSet, basename='adtracking')

app_name = 'ads'

urlpatterns = [
    # Main API routes
    path('api/v1/', include(router.urls)),
    
    # Additional tracking endpoints (public, no auth required)
    path('track/', include([
        path('auction/', AdTrackingViewSet.as_view({'post': 'auction'}), name='track-auction'),
        path('impression/', AdTrackingViewSet.as_view({'post': 'impression'}), name='track-impression'),
        path('click/', AdTrackingViewSet.as_view({'post': 'click'}), name='track-click'),
        path('conversion/', AdTrackingViewSet.as_view({'post': 'conversion'}), name='track-conversion'),
    ])),
    
    # Campaign management endpoints
    path('campaigns/', include([
        path('<uuid:pk>/approve/', AdCampaignViewSet.as_view({'post': 'approve'}), name='campaign-approve'),
        path('<uuid:pk>/reject/', AdCampaignViewSet.as_view({'post': 'reject'}), name='campaign-reject'),
        path('<uuid:pk>/pause/', AdCampaignViewSet.as_view({'post': 'pause'}), name='campaign-pause'),
        path('<uuid:pk>/resume/', AdCampaignViewSet.as_view({'post': 'resume'}), name='campaign-resume'),
        path('<uuid:pk>/report/', AdCampaignViewSet.as_view({'post': 'report'}), name='campaign-report'),
        path('<uuid:pk>/optimize-bids/', AdCampaignViewSet.as_view({'post': 'optimize_bids'}), name='campaign-optimize-bids'),
        path('dashboard/', AdCampaignViewSet.as_view({'get': 'dashboard'}), name='campaign-dashboard'),
    ])),
    
    # Ad group management endpoints
    path('ad-groups/', include([
        path('<uuid:pk>/pause/', AdGroupViewSet.as_view({'post': 'pause'}), name='adgroup-pause'),
        path('<uuid:pk>/activate/', AdGroupViewSet.as_view({'post': 'activate'}), name='adgroup-activate'),
    ])),
    
    # Creative management endpoints
    path('creatives/', include([
        path('<uuid:pk>/review/', AdCreativeViewSet.as_view({'post': 'review'}), name='creative-review'),
        path('<uuid:pk>/performance/', AdCreativeViewSet.as_view({'get': 'performance'}), name='creative-performance'),
    ])),
    
    # Keyword management endpoints
    path('keywords/', include([
        path('suggest/', AdKeywordViewSet.as_view({'post': 'suggest'}), name='keyword-suggest'),
        path('bulk-update-bids/', AdKeywordViewSet.as_view({'post': 'bulk_update_bids'}), name='keyword-bulk-update-bids'),
    ])),
    
    # Audience segment endpoints
    path('audience-segments/', include([
        path('<uuid:pk>/refresh/', AdAudienceSegmentViewSet.as_view({'post': 'refresh'}), name='audience-segment-refresh'),
    ])),
    
    # Placement management endpoints
    path('placements/', include([
        path('<uuid:pk>/performance/', AdPlacementViewSet.as_view({'get': 'performance'}), name='placement-performance'),
    ])),
    
    # Category management endpoints
    path('categories/', include([
        path('tree/', AdCategoryViewSet.as_view({'get': 'tree'}), name='category-tree'),
    ])),
    
    # Budget and spend endpoints
    path('budget-spend/', include([
        path('summary/', AdBudgetSpendViewSet.as_view({'get': 'summary'}), name='budget-spend-summary'),
    ])),
    
    # API documentation
    path('docs/', include_docs_urls(title='SUPER Ads API')),
]