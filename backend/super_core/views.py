"""
Global views for SUPER platform
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def handler404(request, exception):
    """Custom 404 handler"""
    return JsonResponse({
        'error': 'Not Found',
        'message': 'The requested resource was not found.',
        'status_code': 404
    }, status=404)


def handler500(request):
    """Custom 500 handler"""
    logger.error(f"Internal Server Error for request: {request.path}")
    return JsonResponse({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred. Please try again later.',
        'status_code': 500
    }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'service': 'super-platform',
        'version': '1.0.0'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def version_info(request):
    """Version information endpoint"""
    return Response({
        'platform': 'SUPER',
        'version': '1.0.0',
        'api_version': 'v1',
        'status': 'active'
    })


@api_view(['POST'])
def webhook_handler(request, provider):
    """Generic webhook handler for external providers"""
    try:
        # Route to appropriate webhook handler based on provider
        if provider == 'upi':
            from payments_upi.webhooks import handle_upi_webhook
            return handle_upi_webhook(request)
        elif provider == 'porter':
            from porter.webhooks import handle_porter_webhook
            return handle_porter_webhook(request)
        else:
            return Response(
                {'error': f'Unknown provider: {provider}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.error(f"Webhook error for {provider}: {str(e)}")
        return Response(
            {'error': 'Webhook processing failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )