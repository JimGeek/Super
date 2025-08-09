from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeliveryZoneViewSet, DeliveryPartnerViewSet, DeliveryRouteViewSet,
    DeliveryViewSet, RouteOptimizationJobViewSet, DeliveryAnalyticsViewSet
)

app_name = 'logistics'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'zones', DeliveryZoneViewSet, basename='deliveryzone')
router.register(r'partners', DeliveryPartnerViewSet, basename='deliverypartner')
router.register(r'routes', DeliveryRouteViewSet, basename='deliveryroute')
router.register(r'deliveries', DeliveryViewSet, basename='delivery')
router.register(r'optimization-jobs', RouteOptimizationJobViewSet, basename='routeoptimizationjob')
router.register(r'analytics', DeliveryAnalyticsViewSet, basename='deliveryanalytics')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
]