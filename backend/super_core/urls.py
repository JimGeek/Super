"""
SUPER platform URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# API URL patterns
api_patterns = [
    path('auth/', include('accounts.urls')),
    path('plans/', include('plans.urls')),
    path('flows/', include('flows.urls')),
    path('catalog/', include('catalog.urls')),
    path('pricing/', include('pricing.urls')),
    path('inventory/', include('inventory.urls')),
    path('scheduling/', include('scheduling.urls')),
    path('orders/', include('orders.urls')),
    path('payments/', include('payments_upi.urls')),
    path('settlements/', include('settlements.urls')),
    path('logistics/', include('logistics.urls')),
    path('porter/', include('porter.urls')),
    path('invoicing/', include('invoicing.urls')),
    path('warranty/', include('warranty.urls')),
    path('rewards/', include('rewards.urls')),
    path('support/', include('support.urls')),
    path('notifications/', include('notifications.urls')),
    path('reviews/', include('reviews.urls')),
    path('analytics/', include('analytics.urls')),
    path('admin-portal/', include('admin_portal.urls')),
    path('mid-admin/', include('mid_admin.urls')),
    path('ads/', include('ads.urls')),
    path('dispatch/', include('dispatch.urls')),
]

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # API
    path('api/v1/', include(api_patterns)),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health Check
    path('health/', include('health_check.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Django Debug Toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Custom error handlers
handler404 = 'super_core.views.handler404'
handler500 = 'super_core.views.handler500'