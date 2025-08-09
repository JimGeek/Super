from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SuperCashWalletViewSet, SuperCashTransactionViewSet, RewardCampaignViewSet,
    SuperCashRedemptionViewSet, LoyaltyTierViewSet, CustomerLoyaltyViewSet,
    RewardsSettingsViewSet, RewardsAnalyticsViewSet
)

app_name = 'rewards'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'wallets', SuperCashWalletViewSet, basename='supercashwallet')
router.register(r'transactions', SuperCashTransactionViewSet, basename='supercashtransaction')
router.register(r'campaigns', RewardCampaignViewSet, basename='rewardcampaign')
router.register(r'redemptions', SuperCashRedemptionViewSet, basename='supercashredemption')
router.register(r'tiers', LoyaltyTierViewSet, basename='loyaltytier')
router.register(r'loyalty', CustomerLoyaltyViewSet, basename='customerloyalty')
router.register(r'settings', RewardsSettingsViewSet, basename='rewardssettings')
router.register(r'analytics', RewardsAnalyticsViewSet, basename='rewardsanalytics')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]