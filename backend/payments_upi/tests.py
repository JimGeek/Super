"""
Comprehensive tests for UPI payments app
"""
import json
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, Mock

from accounts.models import Organization
from .models import (
    UPIProvider, VirtualPaymentAddress, UPITransaction, 
    UPIMandate, UPIMandateExecution, UPIRefund, UPIWebhookLog
)
from .services import UPIPaymentService, DemoUPIProvider

User = get_user_model()


class UPIModelTests(TestCase):
    """Test UPI models"""
    
    def setUp(self):
        # Create test user and organization
        self.organization = Organization.objects.create(
            name="Test Merchant",
            business_type="kirana",
            email="merchant@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        self.user = User.objects.create_user(
            email="user@test.com",
            phone="+919876543210",
            first_name="Test",
            last_name="User",
            password="testpass123",
            organization=self.organization,
            role="merchant_owner"
        )
        
        # Create UPI provider
        self.provider = UPIProvider.objects.create(
            name="Test Provider",
            code="test",
            base_url="https://test-api.com",
            api_key="test_key",
            secret_key="test_secret",
            webhook_secret="webhook_secret",
            supports_intent=True,
            supports_collect=True,
            supports_qr=True,
            supports_mandates=True
        )
    
    def test_upi_provider_creation(self):
        """Test UPI provider model"""
        self.assertEqual(str(self.provider), "Test Provider")
        self.assertTrue(self.provider.supports_intent)
        self.assertTrue(self.provider.is_active)
    
    def test_vpa_creation(self):
        """Test VPA model"""
        vpa = VirtualPaymentAddress.objects.create(
            vpa="merchant@test",
            holder_name="Test Merchant",
            organization=self.organization,
            purpose="merchant",
            provider=self.provider
        )
        
        self.assertEqual(str(vpa), "merchant@test (merchant)")
        self.assertTrue(vpa.is_active)
        self.assertFalse(vpa.is_verified)
    
    def test_upi_transaction_creation(self):
        """Test UPI transaction model"""
        transaction = UPITransaction.objects.create(
            txn_ref="TXN123456",
            amount=Decimal('100.00'),
            payer_vpa="user@test",
            payee_vpa="merchant@test",
            user=self.user,
            organization=self.organization,
            description="Test payment",
            provider=self.provider,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        self.assertEqual(str(transaction), "UPI payment - TXN123456 - 100.00")
        self.assertEqual(transaction.status, 'initiated')
        self.assertEqual(transaction.currency, 'INR')
    
    def test_upi_mandate_creation(self):
        """Test UPI mandate model"""
        mandate = UPIMandate.objects.create(
            mandate_ref="MND123456",
            payer_vpa="user@test",
            payee_vpa="platform@test",
            user=self.user,
            organization=self.organization,
            purpose="subscription",
            description="Monthly subscription",
            max_amount=Decimal('1000.00'),
            frequency="monthly",
            start_date=timezone.now().date(),
            provider=self.provider
        )
        
        self.assertEqual(str(mandate), "Mandate MND123456 - subscription")
        self.assertEqual(mandate.status, 'active')
        self.assertEqual(mandate.frequency, 'monthly')


class UPIServiceTests(TestCase):
    """Test UPI service layer"""
    
    def setUp(self):
        # Create test data
        self.organization = Organization.objects.create(
            name="Test Merchant",
            business_type="kirana",
            email="merchant@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        self.user = User.objects.create_user(
            email="user@test.com",
            phone="+919876543210",
            first_name="Test",
            last_name="User",
            password="testpass123",
            organization=self.organization
        )
        
        self.provider = UPIProvider.objects.create(
            name="Demo Provider",
            code="demo",
            base_url="https://demo-api.com",
            api_key="demo_key",
            secret_key="demo_secret",
            webhook_secret="webhook_secret",
            supports_intent=True,
            supports_collect=True,
            supports_qr=True,
            supports_mandates=True
        )
        
        self.service = UPIPaymentService()
    
    def test_get_provider_service(self):
        """Test provider service instantiation"""
        provider_service, provider = self.service.get_provider_service("demo")
        
        self.assertIsInstance(provider_service, DemoUPIProvider)
        self.assertEqual(provider.code, "demo")
    
    def test_get_invalid_provider_service(self):
        """Test invalid provider handling"""
        with self.assertRaises(ValueError):
            self.service.get_provider_service("invalid")
    
    @patch('payments_upi.services.settings.UPI_PROVIDER', 'demo')
    @patch('payments_upi.services.settings.UPI_VPA_PLATFORM', 'platform@demo')
    def test_initiate_payment_intent(self):
        """Test payment initiation with intent method"""
        result = self.service.initiate_payment(
            user=self.user,
            amount=Decimal('100.00'),
            description="Test payment",
            payment_method='intent',
            organization=self.organization
        )
        
        self.assertIn('transaction_id', result)
        self.assertIn('txn_ref', result)
        self.assertIn('intent_url', result)
        self.assertIn('expires_at', result)
        
        # Verify transaction was created
        transaction = UPITransaction.objects.get(id=result['transaction_id'])
        self.assertEqual(transaction.status, 'pending')
        self.assertEqual(transaction.amount, Decimal('100.00'))
        self.assertEqual(transaction.payment_method, 'intent')
    
    @patch('payments_upi.services.settings.UPI_PROVIDER', 'demo')
    @patch('payments_upi.services.settings.UPI_VPA_PLATFORM', 'platform@demo')
    def test_initiate_payment_qr(self):
        """Test payment initiation with QR method"""
        result = self.service.initiate_payment(
            user=self.user,
            amount=Decimal('50.00'),
            description="QR payment",
            payment_method='qr'
        )
        
        self.assertIn('qr_code', result)
        
        # Verify transaction
        transaction = UPITransaction.objects.get(id=result['transaction_id'])
        self.assertEqual(transaction.payment_method, 'qr')
    
    @patch('payments_upi.services.settings.UPI_PROVIDER', 'demo')
    @patch('payments_upi.services.settings.UPI_VPA_PLATFORM', 'platform@demo')
    def test_create_mandate(self):
        """Test mandate creation"""
        result = self.service.create_mandate(
            user=self.user,
            organization=self.organization,
            purpose="subscription",
            max_amount=Decimal('1000.00'),
            frequency="monthly",
            description="Monthly subscription",
            start_date=timezone.now().date()
        )
        
        self.assertIn('mandate_id', result)
        self.assertIn('mandate_ref', result)
        self.assertIn('approval_url', result)
        
        # Verify mandate was created
        mandate = UPIMandate.objects.get(id=result['mandate_id'])
        self.assertEqual(mandate.status, 'active')
        self.assertEqual(mandate.purpose, 'subscription')
    
    def test_initiate_refund(self):
        """Test refund initiation"""
        # Create successful transaction first
        transaction = UPITransaction.objects.create(
            txn_ref="TXN123456",
            amount=Decimal('100.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Test payment",
            provider=self.provider,
            status='success',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        result = self.service.initiate_refund(
            transaction_id=transaction.id,
            refund_amount=Decimal('50.00'),
            reason="Partial refund"
        )
        
        self.assertIn('refund_id', result)
        self.assertIn('refund_ref', result)
        
        # Verify refund was created
        refund = UPIRefund.objects.get(id=result['refund_id'])
        self.assertEqual(refund.refund_amount, Decimal('50.00'))
        self.assertEqual(refund.status, 'processing')
    
    def test_refund_amount_validation(self):
        """Test refund amount validation"""
        transaction = UPITransaction.objects.create(
            txn_ref="TXN123456",
            amount=Decimal('100.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Test payment",
            provider=self.provider,
            status='success',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Try to refund more than transaction amount
        with self.assertRaises(ValueError):
            self.service.initiate_refund(
                transaction_id=transaction.id,
                refund_amount=Decimal('150.00'),
                reason="Invalid refund"
            )


class UPIAPITests(APITestCase):
    """Test UPI API endpoints"""
    
    def setUp(self):
        # Create test data
        self.organization = Organization.objects.create(
            name="Test Merchant",
            business_type="kirana",
            email="merchant@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        self.user = User.objects.create_user(
            email="user@test.com",
            phone="+919876543210",
            first_name="Test",
            last_name="User",
            password="testpass123",
            organization=self.organization
        )
        
        self.provider = UPIProvider.objects.create(
            name="Demo Provider",
            code="demo",
            base_url="https://demo-api.com",
            api_key="demo_key",
            secret_key="demo_secret",
            webhook_secret="webhook_secret",
            supports_intent=True,
            supports_collect=True,
            supports_qr=True,
            supports_mandates=True
        )
        
        # Authenticate user
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_list_providers(self):
        """Test provider listing endpoint"""
        url = reverse('upi:upiprovider-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['code'], 'demo')
    
    @patch('payments_upi.services.settings.UPI_PROVIDER', 'demo')
    @patch('payments_upi.services.settings.UPI_VPA_PLATFORM', 'platform@demo')
    def test_initiate_payment_api(self):
        """Test payment initiation API"""
        url = reverse('upi:initiate_payment')
        data = {
            'amount': '100.00',
            'description': 'Test payment',
            'payment_method': 'intent'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('txn_ref', response.data)
        self.assertIn('intent_url', response.data)
    
    def test_initiate_payment_invalid_amount(self):
        """Test payment initiation with invalid amount"""
        url = reverse('upi:initiate_payment')
        data = {
            'amount': '0.50',  # Below minimum
            'description': 'Test payment',
            'payment_method': 'intent'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('payments_upi.services.settings.UPI_PROVIDER', 'demo')
    @patch('payments_upi.services.settings.UPI_VPA_PLATFORM', 'platform@demo')
    def test_create_mandate_api(self):
        """Test mandate creation API"""
        url = reverse('upi:create_mandate')
        data = {
            'purpose': 'subscription',
            'description': 'Monthly subscription',
            'max_amount': '1000.00',
            'frequency': 'monthly',
            'start_date': timezone.now().date().isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('mandate_ref', response.data)
    
    def test_transaction_list(self):
        """Test transaction listing"""
        # Create test transaction
        UPITransaction.objects.create(
            txn_ref="TXN123456",
            amount=Decimal('100.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Test payment",
            provider=self.provider,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        url = reverse('upi:transaction-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_transaction_status(self):
        """Test transaction status endpoint"""
        transaction = UPITransaction.objects.create(
            txn_ref="TXN123456",
            amount=Decimal('100.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Test payment",
            provider=self.provider,
            status='pending',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        url = reverse('upi:transaction-status', kwargs={'pk': transaction.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')  # Demo provider returns success
    
    def test_payment_methods(self):
        """Test payment methods endpoint"""
        url = reverse('upi:payment_methods')
        
        with patch('payments_upi.services.settings.UPI_PROVIDER', 'demo'):
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('methods', response.data)
        self.assertTrue(len(response.data['methods']) > 0)
    
    def test_transaction_summary(self):
        """Test transaction summary endpoint"""
        # Create test transactions
        UPITransaction.objects.create(
            txn_ref="TXN1",
            amount=Decimal('100.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Test payment 1",
            provider=self.provider,
            status='success',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        UPITransaction.objects.create(
            txn_ref="TXN2",
            amount=Decimal('50.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Test payment 2",
            provider=self.provider,
            status='failed',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        url = reverse('upi:transaction_summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_transactions'], 2)
        self.assertEqual(response.data['successful_transactions'], 1)
        self.assertEqual(response.data['failed_transactions'], 1)
        self.assertEqual(float(response.data['successful_amount']), 100.00)


class UPIWebhookTests(TestCase):
    """Test UPI webhook processing"""
    
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Merchant",
            business_type="kirana",
            email="merchant@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        self.user = User.objects.create_user(
            email="user@test.com",
            phone="+919876543210",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        
        self.provider = UPIProvider.objects.create(
            name="Demo Provider",
            code="demo",
            base_url="https://demo-api.com",
            api_key="demo_key",
            secret_key="demo_secret",
            webhook_secret="webhook_secret",
            supports_intent=True
        )
        
        self.transaction = UPITransaction.objects.create(
            txn_ref="TXN123456",
            amount=Decimal('100.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Test payment",
            provider=self.provider,
            status='pending',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        self.service = UPIPaymentService()
    
    def test_process_payment_success_webhook(self):
        """Test payment success webhook processing"""
        webhook_data = {
            'event_type': 'payment_success',
            'transaction_ref': 'TXN123456',
            'status': 'success',
            'upi_txn_id': 'UPI123456789'
        }
        
        # Generate signature
        provider_service = DemoUPIProvider(self.provider)
        signature = provider_service.generate_signature(webhook_data, "webhook_secret")
        
        result = self.service.process_webhook("demo", webhook_data, signature)
        
        self.assertEqual(result['status'], 'processed')
        
        # Verify transaction was updated
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, 'success')
        self.assertEqual(self.transaction.upi_txn_id, 'UPI123456789')
        self.assertTrue(self.transaction.webhook_received)
    
    def test_process_payment_failure_webhook(self):
        """Test payment failure webhook processing"""
        webhook_data = {
            'event_type': 'payment_failed',
            'transaction_ref': 'TXN123456',
            'status': 'failed',
            'failure_reason': 'Insufficient funds'
        }
        
        provider_service = DemoUPIProvider(self.provider)
        signature = provider_service.generate_signature(webhook_data, "webhook_secret")
        
        result = self.service.process_webhook("demo", webhook_data, signature)
        
        self.assertEqual(result['status'], 'processed')
        
        # Verify transaction was updated
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, 'failed')
        self.assertEqual(self.transaction.failure_reason, 'Insufficient funds')
    
    def test_invalid_signature_webhook(self):
        """Test webhook with invalid signature"""
        webhook_data = {
            'event_type': 'payment_success',
            'transaction_ref': 'TXN123456',
            'status': 'success'
        }
        
        invalid_signature = "invalid_signature"
        
        result = self.service.process_webhook("demo", webhook_data, invalid_signature)
        
        self.assertEqual(result['error'], 'Invalid signature')
    
    def test_webhook_api_endpoint(self):
        """Test webhook API endpoint"""
        webhook_data = {
            'event_type': 'payment_success',
            'transaction_ref': 'TXN123456',
            'status': 'success',
            'upi_txn_id': 'UPI123456789'
        }
        
        provider_service = DemoUPIProvider(self.provider)
        signature = provider_service.generate_signature(webhook_data, "webhook_secret")
        
        client = APIClient()
        url = reverse('upi:webhook_handler', kwargs={'provider_code': 'demo'})
        
        response = client.post(
            url,
            data=json.dumps(webhook_data),
            content_type='application/json',
            HTTP_X_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')


class UPITaskTests(TransactionTestCase):
    """Test UPI Celery tasks"""
    
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Merchant",
            business_type="kirana",
            email="merchant@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        self.user = User.objects.create_user(
            email="user@test.com",
            phone="+919876543210",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        
        self.provider = UPIProvider.objects.create(
            name="Demo Provider",
            code="demo",
            base_url="https://demo-api.com",
            api_key="demo_key",
            secret_key="demo_secret",
            webhook_secret="webhook_secret",
            supports_intent=True
        )
    
    def test_check_pending_payments_task(self):
        """Test check pending payments task"""
        from .tasks import check_pending_payments
        
        # Create old pending transaction
        old_transaction = UPITransaction.objects.create(
            txn_ref="TXN_OLD",
            amount=Decimal('100.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Old payment",
            provider=self.provider,
            status='pending',
            expires_at=timezone.now() + timedelta(minutes=15),
            initiated_at=timezone.now() - timedelta(minutes=10)
        )
        
        # Create expired transaction
        expired_transaction = UPITransaction.objects.create(
            txn_ref="TXN_EXPIRED",
            amount=Decimal('50.00'),
            payer_vpa="user@demo",
            payee_vpa="merchant@demo",
            user=self.user,
            organization=self.organization,
            description="Expired payment",
            provider=self.provider,
            status='pending',
            expires_at=timezone.now() - timedelta(minutes=5)
        )
        
        result = check_pending_payments()
        
        self.assertIn('processed', result)
        self.assertIn('expired', result)
        
        # Check if transactions were updated
        old_transaction.refresh_from_db()
        expired_transaction.refresh_from_db()
        
        self.assertEqual(old_transaction.status, 'success')  # Demo provider returns success
        self.assertEqual(expired_transaction.status, 'expired')


class UPIIntegrationTests(APITestCase):
    """Integration tests for complete UPI payment flows"""
    
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Merchant",
            business_type="kirana",
            email="merchant@test.com",
            phone="+919876543210",
            address_line1="Test Address",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001"
        )
        
        self.user = User.objects.create_user(
            email="user@test.com",
            phone="+919876543210",
            first_name="Test",
            last_name="User",
            password="testpass123",
            organization=self.organization
        )
        
        self.provider = UPIProvider.objects.create(
            name="Demo Provider",
            code="demo",
            base_url="https://demo-api.com",
            api_key="demo_key",
            secret_key="demo_secret",
            webhook_secret="webhook_secret",
            supports_intent=True,
            supports_collect=True,
            supports_qr=True,
            supports_mandates=True
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    @patch('payments_upi.services.settings.UPI_PROVIDER', 'demo')
    @patch('payments_upi.services.settings.UPI_VPA_PLATFORM', 'platform@demo')
    def test_complete_payment_flow(self):
        """Test complete payment flow from initiation to webhook"""
        # 1. Initiate payment
        initiate_url = reverse('upi:initiate_payment')
        initiate_data = {
            'amount': '100.00',
            'description': 'Test payment',
            'payment_method': 'intent'
        }
        
        response = self.client.post(initiate_url, initiate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        transaction_id = response.data['transaction_id']
        txn_ref = response.data['txn_ref']
        
        # 2. Check initial status
        status_url = reverse('upi:transaction-status', kwargs={'pk': transaction_id})
        response = self.client.get(status_url)
        self.assertEqual(response.data['status'], 'success')  # Demo provider simulation
        
        # 3. Simulate webhook
        webhook_data = {
            'event_type': 'payment_success',
            'transaction_ref': txn_ref,
            'status': 'success',
            'upi_txn_id': 'UPI123456789'
        }
        
        service = UPIPaymentService()
        provider_service = DemoUPIProvider(self.provider)
        signature = provider_service.generate_signature(webhook_data, "webhook_secret")
        
        result = service.process_webhook("demo", webhook_data, signature)
        self.assertEqual(result['status'], 'processed')
        
        # 4. Verify final transaction state
        transaction = UPITransaction.objects.get(id=transaction_id)
        self.assertEqual(transaction.status, 'success')
        self.assertEqual(transaction.upi_txn_id, 'UPI123456789')
        self.assertTrue(transaction.webhook_received)
    
    @patch('payments_upi.services.settings.UPI_PROVIDER', 'demo')
    @patch('payments_upi.services.settings.UPI_VPA_PLATFORM', 'platform@demo')
    def test_payment_and_refund_flow(self):
        """Test payment followed by refund"""
        # 1. Create successful payment
        service = UPIPaymentService()
        payment_result = service.initiate_payment(
            user=self.user,
            amount=Decimal('100.00'),
            description="Test payment for refund",
            payment_method='intent',
            organization=self.organization
        )
        
        # Simulate payment success
        transaction = UPITransaction.objects.get(id=payment_result['transaction_id'])
        transaction.status = 'success'
        transaction.completed_at = timezone.now()
        transaction.save()
        
        # 2. Initiate refund
        refund_url = reverse('upi:initiate_refund')
        refund_data = {
            'transaction_id': transaction.id,
            'refund_amount': '50.00',
            'reason': 'Partial refund'
        }
        
        response = self.client.post(refund_url, refund_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. Verify refund created
        refund = UPIRefund.objects.get(refund_ref=response.data['refund_ref'])
        self.assertEqual(refund.refund_amount, Decimal('50.00'))
        self.assertEqual(refund.status, 'processing')
    
    def test_mandate_creation_and_execution_flow(self):
        """Test mandate creation and execution"""
        # 1. Create mandate
        with patch('payments_upi.services.settings.UPI_PROVIDER', 'demo'), \
             patch('payments_upi.services.settings.UPI_VPA_PLATFORM', 'platform@demo'):
            
            mandate_url = reverse('upi:create_mandate')
            mandate_data = {
                'purpose': 'subscription',
                'description': 'Monthly subscription',
                'max_amount': '1000.00',
                'frequency': 'monthly',
                'start_date': timezone.now().date().isoformat()
            }
            
            response = self.client.post(mandate_url, mandate_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            mandate_id = response.data['mandate_id']
            
        # 2. Test mandate operations
        mandate = UPIMandate.objects.get(id=mandate_id)
        
        # Pause mandate
        pause_url = reverse('upi:mandate-pause', kwargs={'pk': mandate_id})
        response = self.client.post(pause_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        mandate.refresh_from_db()
        self.assertEqual(mandate.status, 'paused')
        
        # Resume mandate
        resume_url = reverse('upi:mandate-resume', kwargs={'pk': mandate_id})
        response = self.client.post(resume_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        mandate.refresh_from_db()
        self.assertEqual(mandate.status, 'active')


if __name__ == '__main__':
    import unittest
    unittest.main()