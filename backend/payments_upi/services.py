"""
UPI Payment services and business logic
"""
import uuid
import hashlib
import hmac
import json
import requests
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import (
    UPIProvider, UPITransaction, UPIMandate, UPIMandateExecution,
    UPIRefund, VirtualPaymentAddress, UPIWebhookLog
)


class UPIProviderInterface:
    """Abstract interface for UPI providers"""
    
    def __init__(self, provider_config):
        self.provider = provider_config
        self.base_url = provider_config.base_url
        self.api_key = provider_config.api_key
        self.secret_key = provider_config.secret_key
    
    def generate_signature(self, data, secret=None):
        """Generate HMAC signature for request"""
        secret = secret or self.secret_key
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, data, signature, secret=None):
        """Verify webhook signature"""
        expected_signature = self.generate_signature(data, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    def create_payment_intent(self, transaction):
        """Create payment intent URL"""
        raise NotImplementedError
    
    def create_collect_request(self, transaction):
        """Create UPI collect request"""
        raise NotImplementedError
    
    def generate_qr_code(self, transaction):
        """Generate QR code for payment"""
        raise NotImplementedError
    
    def create_mandate(self, mandate):
        """Create UPI mandate"""
        raise NotImplementedError
    
    def execute_mandate(self, mandate_execution):
        """Execute mandate payment"""
        raise NotImplementedError
    
    def initiate_refund(self, refund):
        """Initiate refund"""
        raise NotImplementedError
    
    def check_transaction_status(self, transaction):
        """Check transaction status"""
        raise NotImplementedError


class DemoUPIProvider(UPIProviderInterface):
    """Demo UPI provider for testing"""
    
    def create_payment_intent(self, transaction):
        """Create demo payment intent"""
        intent_url = f"upi://pay?pa={transaction.payee_vpa}&pn={settings.PLATFORM_NAME}&tr={transaction.txn_ref}&am={transaction.amount}&tn={transaction.description}&cu=INR"
        
        return {
            'success': True,
            'intent_url': intent_url,
            'payment_url': f"https://demo-upi.com/pay/{transaction.txn_ref}",
            'expires_at': transaction.expires_at.isoformat()
        }
    
    def create_collect_request(self, transaction):
        """Create demo collect request"""
        return {
            'success': True,
            'collect_ref': f"COLLECT_{transaction.txn_ref}",
            'status': 'sent',
            'expires_at': transaction.expires_at.isoformat()
        }
    
    def generate_qr_code(self, transaction):
        """Generate demo QR code"""
        qr_data = f"upi://pay?pa={transaction.payee_vpa}&pn={settings.PLATFORM_NAME}&tr={transaction.txn_ref}&am={transaction.amount}&tn={transaction.description}&cu=INR"
        
        return {
            'success': True,
            'qr_code': qr_data,
            'qr_image_url': f"https://demo-qr.com/generate?data={qr_data}",
            'expires_at': transaction.expires_at.isoformat()
        }
    
    def create_mandate(self, mandate):
        """Create demo mandate"""
        return {
            'success': True,
            'mandate_id': f"MANDATE_{mandate.mandate_ref}",
            'status': 'active',
            'approval_url': f"https://demo-upi.com/mandate/{mandate.mandate_ref}"
        }
    
    def execute_mandate(self, mandate_execution):
        """Execute demo mandate"""
        return {
            'success': True,
            'execution_id': f"EXEC_{mandate_execution.id}",
            'status': 'processing'
        }
    
    def initiate_refund(self, refund):
        """Initiate demo refund"""
        return {
            'success': True,
            'refund_id': f"REFUND_{refund.refund_ref}",
            'status': 'processing'
        }
    
    def check_transaction_status(self, transaction):
        """Check demo transaction status"""
        # Simulate different outcomes based on amount
        if transaction.amount == Decimal('1.00'):
            return {'status': 'failed', 'reason': 'Insufficient funds'}
        elif transaction.payer_vpa == 'failure@demo':
            return {'status': 'failed', 'reason': 'Invalid VPA'}
        else:
            return {'status': 'success', 'upi_txn_id': f"UPI{transaction.txn_ref}"}


class UPIPaymentService:
    """Main UPI payment service"""
    
    def __init__(self):
        self.provider_map = {
            'demo': DemoUPIProvider,
            # Add other providers here
        }
    
    def get_provider_service(self, provider_code):
        """Get provider service instance"""
        try:
            provider = UPIProvider.objects.get(code=provider_code, is_active=True)
            provider_class = self.provider_map.get(provider_code)
            
            if not provider_class:
                raise ValueError(f"Provider {provider_code} not implemented")
            
            return provider_class(provider), provider
        except UPIProvider.DoesNotExist:
            raise ValueError(f"Provider {provider_code} not found")
    
    @transaction.atomic
    def initiate_payment(self, user, amount, description, payment_method='intent', 
                        order_id=None, organization=None):
        """Initiate UPI payment"""
        
        # Get provider
        provider_code = settings.UPI_PROVIDER
        provider_service, provider = self.get_provider_service(provider_code)
        
        # Generate transaction reference
        txn_ref = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        
        # Determine VPAs
        payer_vpa = user.vpas.filter(purpose='merchant').first()
        if not payer_vpa:
            # Use user's phone number as fallback
            payer_vpa = f"{user.phone.national_number}@{provider_code}"
        else:
            payer_vpa = payer_vpa.vpa
        
        # Platform VPA for collection
        payee_vpa = settings.UPI_VPA_PLATFORM
        
        # Create transaction record
        upi_transaction = UPITransaction.objects.create(
            txn_ref=txn_ref,
            amount=amount,
            payer_vpa=str(payer_vpa),
            payee_vpa=payee_vpa,
            user=user,
            organization=organization,
            description=description,
            provider=provider,
            payment_method=payment_method,
            expires_at=timezone.now() + timedelta(minutes=15),
            order_id=order_id
        )
        
        # Call provider API based on payment method
        if payment_method == 'intent':
            result = provider_service.create_payment_intent(upi_transaction)
        elif payment_method == 'collect':
            result = provider_service.create_collect_request(upi_transaction)
        elif payment_method == 'qr':
            result = provider_service.generate_qr_code(upi_transaction)
        else:
            raise ValueError(f"Unsupported payment method: {payment_method}")
        
        if result.get('success'):
            # Update transaction with provider response
            upi_transaction.provider_response = result
            upi_transaction.status = 'pending'
            upi_transaction.save()
            
            return {
                'transaction_id': upi_transaction.id,
                'txn_ref': txn_ref,
                'payment_url': result.get('payment_url'),
                'intent_url': result.get('intent_url'),
                'qr_code': result.get('qr_code'),
                'expires_at': upi_transaction.expires_at
            }
        else:
            upi_transaction.status = 'failed'
            upi_transaction.failure_reason = result.get('error', 'Provider error')
            upi_transaction.save()
            raise Exception(f"Payment initiation failed: {result.get('error')}")
    
    @transaction.atomic
    def create_mandate(self, user, organization, purpose, max_amount, frequency,
                      description, start_date, end_date=None, 
                      auto_charge_threshold=None, auto_charge_amount=None):
        """Create UPI mandate"""
        
        provider_code = settings.UPI_PROVIDER
        provider_service, provider = self.get_provider_service(provider_code)
        
        # Generate mandate reference
        mandate_ref = f"MND_{uuid.uuid4().hex[:12].upper()}"
        
        # Create mandate record
        mandate = UPIMandate.objects.create(
            mandate_ref=mandate_ref,
            payer_vpa=f"{user.phone.national_number}@{provider_code}",
            payee_vpa=settings.UPI_VPA_PLATFORM,
            user=user,
            organization=organization,
            purpose=purpose,
            description=description,
            max_amount=max_amount,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            auto_charge_threshold=auto_charge_threshold,
            auto_charge_amount=auto_charge_amount,
            provider=provider
        )
        
        # Call provider API
        result = provider_service.create_mandate(mandate)
        
        if result.get('success'):
            mandate.provider_mandate_id = result.get('mandate_id')
            mandate.provider_response = result
            mandate.save()
            
            return {
                'mandate_id': mandate.id,
                'mandate_ref': mandate_ref,
                'approval_url': result.get('approval_url'),
                'status': mandate.status
            }
        else:
            mandate.status = 'failed'
            mandate.save()
            raise Exception(f"Mandate creation failed: {result.get('error')}")
    
    @transaction.atomic
    def initiate_refund(self, transaction_id, refund_amount, reason):
        """Initiate refund for a transaction"""
        
        try:
            original_transaction = UPITransaction.objects.get(
                id=transaction_id, 
                status='success'
            )
        except UPITransaction.DoesNotExist:
            raise ValueError("Transaction not found or not eligible for refund")
        
        # Check refund eligibility
        total_refunded = sum(
            r.refund_amount for r in original_transaction.refunds.filter(status='success')
        )
        
        if total_refunded + refund_amount > original_transaction.amount:
            raise ValueError("Refund amount exceeds available amount")
        
        # Get provider service
        provider_service, _ = self.get_provider_service(original_transaction.provider.code)
        
        # Generate refund reference
        refund_ref = f"REF_{uuid.uuid4().hex[:12].upper()}"
        
        # Create refund record
        refund = UPIRefund.objects.create(
            refund_ref=refund_ref,
            original_transaction=original_transaction,
            refund_amount=refund_amount,
            reason=reason
        )
        
        # Call provider API
        result = provider_service.initiate_refund(refund)
        
        if result.get('success'):
            refund.provider_refund_id = result.get('refund_id')
            refund.status = 'processing'
            refund.provider_response = result
            refund.save()
            
            return {
                'refund_id': refund.id,
                'refund_ref': refund_ref,
                'status': refund.status
            }
        else:
            refund.status = 'failed'
            refund.failure_reason = result.get('error', 'Provider error')
            refund.save()
            raise Exception(f"Refund initiation failed: {result.get('error')}")
    
    def process_webhook(self, provider_code, webhook_data, signature):
        """Process webhook from UPI provider"""
        
        try:
            provider_service, provider = self.get_provider_service(provider_code)
        except ValueError:
            return {'error': 'Invalid provider'}
        
        # Verify signature
        if not provider_service.verify_signature(webhook_data, signature, provider.webhook_secret):
            return {'error': 'Invalid signature'}
        
        # Log webhook
        webhook_log = UPIWebhookLog.objects.create(
            provider=provider,
            event_type=webhook_data.get('event_type', 'unknown'),
            payload=webhook_data,
            signature=signature
        )
        
        try:
            # Process webhook based on event type
            event_type = webhook_data.get('event_type')
            
            if event_type in ['payment_success', 'payment_failed']:
                self._process_payment_webhook(webhook_data, webhook_log)
            elif event_type in ['mandate_approved', 'mandate_revoked']:
                self._process_mandate_webhook(webhook_data, webhook_log)
            elif event_type in ['refund_success', 'refund_failed']:
                self._process_refund_webhook(webhook_data, webhook_log)
            
            webhook_log.is_processed = True
            webhook_log.processed_at = timezone.now()
            webhook_log.save()
            
            return {'status': 'processed'}
        
        except Exception as e:
            webhook_log.processing_error = str(e)
            webhook_log.save()
            return {'error': f'Processing failed: {str(e)}'}
    
    def _process_payment_webhook(self, data, webhook_log):
        """Process payment webhook"""
        txn_ref = data.get('transaction_ref')
        status = data.get('status')
        
        try:
            transaction = UPITransaction.objects.get(txn_ref=txn_ref)
            webhook_log.transaction = transaction
            
            if status == 'success':
                transaction.status = 'success'
                transaction.upi_txn_id = data.get('upi_txn_id')
                transaction.completed_at = timezone.now()
            elif status == 'failed':
                transaction.status = 'failed'
                transaction.failure_reason = data.get('failure_reason')
            
            transaction.webhook_received = True
            transaction.save()
            
        except UPITransaction.DoesNotExist:
            raise Exception(f"Transaction not found: {txn_ref}")
    
    def _process_mandate_webhook(self, data, webhook_log):
        """Process mandate webhook"""
        mandate_ref = data.get('mandate_ref')
        status = data.get('status')
        
        try:
            mandate = UPIMandate.objects.get(mandate_ref=mandate_ref)
            
            if status == 'approved':
                mandate.status = 'active'
            elif status == 'revoked':
                mandate.status = 'revoked'
            
            mandate.save()
            
        except UPIMandate.DoesNotExist:
            raise Exception(f"Mandate not found: {mandate_ref}")
    
    def _process_refund_webhook(self, data, webhook_log):
        """Process refund webhook"""
        refund_ref = data.get('refund_ref')
        status = data.get('status')
        
        try:
            refund = UPIRefund.objects.get(refund_ref=refund_ref)
            
            if status == 'success':
                refund.status = 'success'
                refund.processed_at = timezone.now()
            elif status == 'failed':
                refund.status = 'failed'
                refund.failure_reason = data.get('failure_reason')
            
            refund.save()
            
        except UPIRefund.DoesNotExist:
            raise Exception(f"Refund not found: {refund_ref}")