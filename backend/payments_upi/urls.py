"""
URL patterns for UPI payments app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'providers', views.UPIProviderViewSet)
router.register(r'vpas', views.VirtualPaymentAddressViewSet, basename='vpa')
router.register(r'transactions', views.UPITransactionViewSet, basename='transaction')
router.register(r'mandates', views.UPIMandateViewSet, basename='mandate')
router.register(r'refunds', views.UPIRefundViewSet, basename='refund')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Payment operations
    path('initiate/', views.initiate_payment, name='initiate_payment'),
    path('methods/', views.payment_methods, name='payment_methods'),
    path('summary/', views.transaction_summary, name='transaction_summary'),
    
    # Mandate operations
    path('mandates/create/', views.create_mandate, name='create_mandate'),
    
    # Refund operations
    path('refunds/initiate/', views.initiate_refund, name='initiate_refund'),
    
    # Webhooks
    path('webhook/<str:provider_code>/', views.webhook_handler, name='webhook_handler'),
]