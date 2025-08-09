"""
URL patterns for accounts app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'organizations', views.OrganizationViewSet)
router.register(r'addresses', views.UserAddressViewSet, basename='address')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('register/', views.register, name='register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # OTP endpoints
    path('otp/request/', views.request_otp, name='request_otp'),
    path('otp/verify/', views.verify_otp, name='verify_otp'),
    
    # Password reset
    path('password/reset/', views.reset_password, name='reset_password'),
    path('password/reset/confirm/', views.reset_password_confirm, name='reset_password_confirm'),
    
    # Merchant onboarding
    path('merchants/onboard/', views.merchant_onboarding, name='merchant_onboarding'),
]