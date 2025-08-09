"""
Views for UPI payments app
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
import json
import logging

from .models import (
    UPIProvider, VirtualPaymentAddress, UPITransaction, 
    UPIMandate, UPIRefund, UPIWebhookLog
)
from .serializers import (
    UPIProviderSerializer, VirtualPaymentAddressSerializer,
    UPITransactionSerializer, UPIMandateSerializer, UPIRefundSerializer,
    PaymentInitiateSerializer, PaymentResponseSerializer,
    MandateCreateSerializer, RefundCreateSerializer
)
from .services import UPIPaymentService

logger = logging.getLogger(__name__)


class UPIProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for UPI providers (read-only)"""
    queryset = UPIProvider.objects.filter(is_active=True)
    serializer_class = UPIProviderSerializer
    permission_classes = [IsAuthenticated]


class VirtualPaymentAddressViewSet(viewsets.ModelViewSet):
    """ViewSet for VPA management"""
    serializer_class = VirtualPaymentAddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'mid_admin']:
            return VirtualPaymentAddress.objects.all()
        elif self.request.user.organization:
            return VirtualPaymentAddress.objects.filter(
                organization=self.request.user.organization
            )
        else:
            return VirtualPaymentAddress.objects.filter(
                user=self.request.user
            )


class UPITransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for UPI transactions (read-only)"""
    serializer_class = UPITransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'mid_admin']:
            return UPITransaction.objects.all()
        elif self.request.user.organization:
            return UPITransaction.objects.filter(
                organization=self.request.user.organization
            )
        else:
            return UPITransaction.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get transaction status"""
        transaction = self.get_object()
        
        # Check with provider if status is still pending
        if transaction.status in ['pending', 'processing']:
            service = UPIPaymentService()
            try:
                provider_service, _ = service.get_provider_service(transaction.provider.code)
                result = provider_service.check_transaction_status(transaction)
                
                if result.get('status') == 'success':
                    transaction.status = 'success'
                    transaction.upi_txn_id = result.get('upi_txn_id')
                    transaction.save()
                elif result.get('status') == 'failed':
                    transaction.status = 'failed'
                    transaction.failure_reason = result.get('reason')
                    transaction.save()
                    
            except Exception as e:
                logger.error(f"Status check failed for {transaction.txn_ref}: {str(e)}")
        
        serializer = self.get_serializer(transaction)
        return Response(serializer.data)


class UPIMandateViewSet(viewsets.ModelViewSet):
    """ViewSet for UPI mandates"""
    serializer_class = UPIMandateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'mid_admin']:
            return UPIMandate.objects.all()
        elif self.request.user.organization:
            return UPIMandate.objects.filter(
                organization=self.request.user.organization
            )
        else:
            return UPIMandate.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause mandate"""
        mandate = self.get_object()
        mandate.status = 'paused'
        mandate.save()
        return Response({'message': 'Mandate paused successfully'})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume mandate"""
        mandate = self.get_object()
        mandate.status = 'active'
        mandate.save()
        return Response({'message': 'Mandate resumed successfully'})
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke mandate"""
        mandate = self.get_object()
        mandate.status = 'revoked'
        mandate.save()
        return Response({'message': 'Mandate revoked successfully'})


class UPIRefundViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for UPI refunds (read-only)"""
    serializer_class = UPIRefundSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'mid_admin']:
            return UPIRefund.objects.all()
        elif self.request.user.organization:
            return UPIRefund.objects.filter(
                original_transaction__organization=self.request.user.organization
            )
        else:
            return UPIRefund.objects.filter(
                original_transaction__user=self.request.user
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    """Initiate UPI payment"""
    serializer = PaymentInitiateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            service = UPIPaymentService()
            result = service.initiate_payment(
                user=request.user,
                amount=serializer.validated_data['amount'],
                description=serializer.validated_data['description'],
                payment_method=serializer.validated_data['payment_method'],
                order_id=serializer.validated_data.get('order_id'),
                organization=request.user.organization
            )
            
            response_serializer = PaymentResponseSerializer(data=result)
            if response_serializer.is_valid():
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    response_serializer.errors, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Payment initiation failed: {str(e)}")
            return Response(
                {'error': f'Payment initiation failed: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_mandate(request):
    """Create UPI mandate"""
    serializer = MandateCreateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            service = UPIPaymentService()
            result = service.create_mandate(
                user=request.user,
                organization=request.user.organization,
                **serializer.validated_data
            )
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Mandate creation failed: {str(e)}")
            return Response(
                {'error': f'Mandate creation failed: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_refund(request):
    """Initiate refund"""
    serializer = RefundCreateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Check if user has permission to refund this transaction
            transaction = UPITransaction.objects.get(
                id=serializer.validated_data['transaction_id']
            )
            
            if (request.user.role not in ['super_admin', 'mid_admin'] and 
                transaction.organization != request.user.organization and
                transaction.user != request.user):
                return Response(
                    {'error': 'Permission denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            service = UPIPaymentService()
            result = service.initiate_refund(
                transaction_id=serializer.validated_data['transaction_id'],
                refund_amount=serializer.validated_data['refund_amount'],
                reason=serializer.validated_data['reason']
            )
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Refund initiation failed: {str(e)}")
            return Response(
                {'error': f'Refund initiation failed: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@require_POST
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_handler(request, provider_code):
    """Handle UPI provider webhooks"""
    try:
        # Get webhook data
        webhook_data = json.loads(request.body.decode('utf-8'))
        signature = request.META.get('HTTP_X_SIGNATURE', '')
        
        # Log incoming webhook
        logger.info(f"Received webhook from {provider_code}: {webhook_data}")
        
        # Process webhook
        service = UPIPaymentService()
        result = service.process_webhook(provider_code, webhook_data, signature)
        
        if 'error' in result:
            logger.error(f"Webhook processing error: {result['error']}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return Response(
            {'error': 'Invalid JSON'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        return Response(
            {'error': 'Processing failed'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_methods(request):
    """Get available payment methods"""
    try:
        from django.conf import settings
        service = UPIPaymentService()
        provider_service, provider = service.get_provider_service(settings.UPI_PROVIDER)
        
        methods = []
        if provider.supports_intent:
            methods.append({
                'method': 'intent',
                'name': 'UPI Intent',
                'description': 'Pay using any UPI app'
            })
        if provider.supports_collect:
            methods.append({
                'method': 'collect',
                'name': 'UPI Collect',
                'description': 'Receive payment request on your UPI app'
            })
        if provider.supports_qr:
            methods.append({
                'method': 'qr',
                'name': 'QR Code',
                'description': 'Scan QR code to pay'
            })
        
        return Response({'methods': methods})
        
    except Exception as e:
        logger.error(f"Failed to get payment methods: {str(e)}")
        return Response(
            {'error': 'Failed to get payment methods'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_summary(request):
    """Get transaction summary for user/organization"""
    queryset = UPITransaction.objects.all()
    
    # Filter based on user role
    if request.user.role in ['super_admin', 'mid_admin']:
        pass  # No filtering for admins
    elif request.user.organization:
        queryset = queryset.filter(organization=request.user.organization)
    else:
        queryset = queryset.filter(user=request.user)
    
    # Calculate summary
    from django.db.models import Sum, Count
    from decimal import Decimal
    
    summary = queryset.aggregate(
        total_transactions=Count('id'),
        total_amount=Sum('amount'),
        successful_transactions=Count('id', filter=queryset.filter(status='success').query),
        successful_amount=Sum('amount', filter=queryset.filter(status='success').query),
        failed_transactions=Count('id', filter=queryset.filter(status='failed').query),
        pending_transactions=Count('id', filter=queryset.filter(status__in=['pending', 'processing']).query)
    )
    
    # Handle None values
    for key, value in summary.items():
        if value is None:
            summary[key] = 0 if 'amount' in key else 0
    
    # Calculate success rate
    if summary['total_transactions'] > 0:
        summary['success_rate'] = (
            summary['successful_transactions'] / summary['total_transactions']
        ) * 100
    else:
        summary['success_rate'] = 0
    
    return Response(summary)