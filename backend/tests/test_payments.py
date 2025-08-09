"""
Test cases for payments_upi app
"""

from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, Mock
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from payments_upi.models import UPIPayment, UPIRefund, UPIProvider, PaymentWebhook
from payments_upi.services import UPIPaymentService
from settlements.models import Settlement, SettlementTransaction
from .base import BaseAPITestCase, TestDataFactory, MockExternalServices


class UPIPaymentAPITestCase(BaseAPITestCase):
    """Test cases for UPI Payment API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_customer()
        
        # Create test order
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization
        )
        
        # Create test payment
        self.payment = TestDataFactory.create_upi_payment(self.order)
    
    def test_initiate_payment(self):
        """Test initiating a UPI payment"""
        data = {
            "order_id": str(self.order.id),
            "amount": str(self.order.net_amount),
            "provider": "razorpay",
            "payment_method": "upi",
            "upi_id": "test@paytm"
        }
        
        with patch('payments_upi.services.UPIPaymentService.initiate_payment') as mock_initiate:
            mock_initiate.return_value = {
                "payment_id": "pay_test123",
                "status": "created",
                "payment_url": "https://razorpay.com/pay/test123"
            }
            
            url = reverse('payment-initiate')
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            response_data = response.json()
            self.assertIn('payment_id', response_data)
            self.assertIn('payment_url', response_data)
            self.assertEqual(response_data['status'], 'created')
    
    def test_payment_status_check(self):
        """Test checking payment status"""
        url = reverse('payment-status', kwargs={'payment_id': self.payment.transaction_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['status'], self.payment.status)
        self.assertEqual(str(data['amount']), str(self.payment.amount))
    
    def test_payment_list_customer(self):
        """Test customer can see their payments"""
        url = reverse('payment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
        
        # Check customer can only see their own payments
        payment_data = data['results'][0]
        self.assertEqual(payment_data['customer'], str(self.customer.id))
    
    def test_payment_list_merchant_filter(self):
        """Test merchant can filter payments by their orders"""
        self.authenticate_merchant()
        
        url = reverse('payment-list')
        response = self.client.get(url, {'merchant': str(self.merchant.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        for payment in data['results']:
            self.assertEqual(payment['order']['merchant'], str(self.merchant.id))


class UPIPaymentServiceTestCase(BaseAPITestCase):
    """Test cases for UPI Payment Service"""
    
    def setUp(self):
        super().setUp()
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization
        )
        self.service = UPIPaymentService()
    
    @patch('payments_upi.services.requests.post')
    def test_initiate_razorpay_payment(self, mock_post):
        """Test initiating Razorpay payment"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "pay_razorpay123",
            "status": "created",
            "short_url": "https://rzp.io/i/test123"
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = self.service.initiate_payment(
            order=self.order,
            provider="razorpay",
            payment_method="upi",
            upi_id="test@paytm"
        )
        
        self.assertEqual(result['payment_id'], "pay_razorpay123")
        self.assertEqual(result['status'], "created")
        self.assertIn('payment_url', result)
        
        # Check payment was created in database
        payment = UPIPayment.objects.get(provider_transaction_id="pay_razorpay123")
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.provider, "razorpay")
    
    @patch('payments_upi.services.requests.post')
    def test_initiate_phonepe_payment(self, mock_post):
        """Test initiating PhonePe payment"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "merchantTransactionId": "txn_phonepe123",
                "instrumentResponse": {
                    "redirectInfo": {
                        "url": "https://mercury.phonepe.com/transact/test123"
                    }
                }
            }
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = self.service.initiate_payment(
            order=self.order,
            provider="phonepe",
            payment_method="upi",
            upi_id="test@phonepe"
        )
        
        self.assertEqual(result['payment_id'], "txn_phonepe123")
        self.assertIn('payment_url', result)
    
    @patch('payments_upi.services.requests.get')
    def test_verify_payment_status(self, mock_get):
        """Test verifying payment status"""
        payment = TestDataFactory.create_upi_payment(
            self.order,
            provider="razorpay",
            provider_transaction_id="pay_test123"
        )
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "pay_test123",
            "status": "captured",
            "amount": 25600  # Amount in paise
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        updated_payment = self.service.verify_payment(payment)
        
        self.assertEqual(updated_payment.status, "success")
        self.assertEqual(updated_payment.amount, Decimal('256.00'))
    
    def test_process_successful_payment(self):
        """Test processing successful payment"""
        payment = TestDataFactory.create_upi_payment(self.order)
        
        # Process payment success
        self.service.process_payment_success(payment)
        
        # Check order status updated
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")
        
        # Check payment status updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, "success")
    
    def test_process_failed_payment(self):
        """Test processing failed payment"""
        payment = TestDataFactory.create_upi_payment(self.order)
        
        # Process payment failure
        self.service.process_payment_failure(payment, "Payment declined by bank")
        
        # Check order status
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "failed")
        
        # Check payment status
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        self.assertEqual(payment.failure_reason, "Payment declined by bank")


class UPIRefundTestCase(BaseAPITestCase):
    """Test cases for UPI Refunds"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization
        )
        self.payment = TestDataFactory.create_upi_payment(
            self.order,
            status="success",
            provider_transaction_id="pay_success123"
        )
    
    @patch('payments_upi.services.requests.post')
    def test_initiate_full_refund(self, mock_post):
        """Test initiating full refund"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "rfnd_test123",
            "status": "processed",
            "amount": 25600
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        data = {
            "payment_id": str(self.payment.id),
            "amount": str(self.payment.amount),
            "reason": "Product not delivered"
        }
        
        url = reverse('refund-initiate')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check refund was created
        refund = UPIRefund.objects.get(payment=self.payment)
        self.assertEqual(refund.amount, self.payment.amount)
        self.assertEqual(refund.reason, "Product not delivered")
        self.assertEqual(refund.status, "processed")
    
    @patch('payments_upi.services.requests.post')
    def test_initiate_partial_refund(self, mock_post):
        """Test initiating partial refund"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "rfnd_partial123",
            "status": "processed",
            "amount": 10000  # Partial amount
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        partial_amount = Decimal('100.00')
        data = {
            "payment_id": str(self.payment.id),
            "amount": str(partial_amount),
            "reason": "Partial cancellation"
        }
        
        url = reverse('refund-initiate')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check refund amount
        refund = UPIRefund.objects.get(payment=self.payment)
        self.assertEqual(refund.amount, partial_amount)
    
    def test_refund_exceeds_payment_amount(self):
        """Test refund amount exceeding payment amount"""
        data = {
            "payment_id": str(self.payment.id),
            "amount": str(self.payment.amount + Decimal('100.00')),  # Exceeds payment
            "reason": "Full refund"
        }
        
        url = reverse('refund-initiate')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_refund_list(self):
        """Test listing refunds"""
        # Create test refund
        UPIRefund.objects.create(
            payment=self.payment,
            refund_id="test_refund_123",
            amount=Decimal('50.00'),
            reason="Test refund",
            status="processed",
            organization=self.organization
        )
        
        url = reverse('refund-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)


class PaymentWebhookTestCase(BaseAPITestCase):
    """Test cases for Payment Webhooks"""
    
    def setUp(self):
        super().setUp()
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization
        )
        self.payment = TestDataFactory.create_upi_payment(
            self.order,
            provider_transaction_id="pay_webhook123"
        )
    
    @patch('payments_upi.services.UPIPaymentService.verify_webhook_signature')
    def test_razorpay_webhook_payment_captured(self, mock_verify):
        """Test Razorpay webhook for payment captured"""
        mock_verify.return_value = True
        
        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_webhook123",
                        "status": "captured",
                        "amount": 25600
                    }
                }
            }
        }
        
        url = reverse('webhook-razorpay')
        response = self.client.post(url, webhook_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check payment status updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "success")
        
        # Check webhook was logged
        webhook = PaymentWebhook.objects.get(
            provider_transaction_id="pay_webhook123",
            event_type="payment.captured"
        )
        self.assertEqual(webhook.provider, "razorpay")
        self.assertEqual(webhook.status, "processed")
    
    @patch('payments_upi.services.UPIPaymentService.verify_webhook_signature')
    def test_webhook_invalid_signature(self, mock_verify):
        """Test webhook with invalid signature"""
        mock_verify.return_value = False
        
        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_webhook123",
                        "status": "captured"
                    }
                }
            }
        }
        
        url = reverse('webhook-razorpay')
        response = self.client.post(url, webhook_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check webhook was logged with error status
        webhook = PaymentWebhook.objects.get(
            provider_transaction_id="pay_webhook123"
        )
        self.assertEqual(webhook.status, "failed")
        self.assertIn("Invalid signature", webhook.error_message)
    
    def test_webhook_payment_failed(self):
        """Test webhook for payment failed"""
        with patch('payments_upi.services.UPIPaymentService.verify_webhook_signature', return_value=True):
            webhook_payload = {
                "event": "payment.failed",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_webhook123",
                            "status": "failed",
                            "error_description": "Payment declined by bank"
                        }
                    }
                }
            }
            
            url = reverse('webhook-razorpay')
            response = self.client.post(url, webhook_payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # Check payment status updated
            self.payment.refresh_from_db()
            self.assertEqual(self.payment.status, "failed")
            self.assertEqual(self.payment.failure_reason, "Payment declined by bank")


class SettlementTestCase(BaseAPITestCase):
    """Test cases for Settlement processing"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        # Create multiple successful payments for settlement
        self.payments = []
        for i in range(3):
            order = TestDataFactory.create_order(
                self.customer, self.merchant, self.organization,
                total_amount=Decimal('100.00'),
                net_amount=Decimal('100.00')
            )
            payment = TestDataFactory.create_upi_payment(
                order,
                status="success",
                amount=Decimal('100.00')
            )
            self.payments.append(payment)
    
    @patch('settlements.services.SettlementService.transfer_to_merchant')
    def test_daily_settlement_processing(self, mock_transfer):
        """Test daily settlement processing"""
        mock_transfer.return_value = {
            "transfer_id": "transfer_test123",
            "status": "processed"
        }
        
        # Trigger settlement processing
        from settlements.tasks import process_daily_settlements
        process_daily_settlements.apply()
        
        # Check settlement was created
        settlement = Settlement.objects.get(
            merchant=self.merchant,
            settlement_date=datetime.now().date()
        )
        
        expected_amount = Decimal('300.00')  # 3 payments of 100 each
        platform_fee = expected_amount * Decimal('0.025')  # 2.5% platform fee
        net_settlement = expected_amount - platform_fee
        
        self.assertEqual(settlement.gross_amount, expected_amount)
        self.assertEqual(settlement.platform_fee, platform_fee)
        self.assertEqual(settlement.net_amount, net_settlement)
        self.assertEqual(settlement.status, "processed")
        
        # Check settlement transactions were created
        transactions = SettlementTransaction.objects.filter(settlement=settlement)
        self.assertEqual(transactions.count(), 3)
    
    def test_settlement_list(self):
        """Test listing settlements"""
        # Create test settlement
        Settlement.objects.create(
            merchant=self.merchant,
            settlement_date=datetime.now().date(),
            gross_amount=Decimal('300.00'),
            platform_fee=Decimal('7.50'),
            tax_amount=Decimal('1.35'),
            net_amount=Decimal('291.15'),
            status="processed",
            organization=self.organization
        )
        
        url = reverse('settlement-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_merchant_settlement_filter(self):
        """Test merchant can only see their settlements"""
        self.authenticate_merchant()
        
        url = reverse('settlement-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        for settlement in data['results']:
            self.assertEqual(settlement['merchant'], str(self.merchant.id))


class PaymentAnalyticsTestCase(BaseAPITestCase):
    """Test cases for Payment Analytics"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        # Create payments with different statuses and dates
        self.create_test_payments()
    
    def create_test_payments(self):
        """Create test payments for analytics"""
        statuses = ['success', 'failed', 'pending']
        amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('150.00')]
        
        for i, (status, amount) in enumerate(zip(statuses, amounts)):
            order = TestDataFactory.create_order(
                self.customer, self.merchant, self.organization,
                total_amount=amount,
                net_amount=amount
            )
            TestDataFactory.create_upi_payment(
                order,
                status=status,
                amount=amount,
                created_at=datetime.now() - timedelta(days=i)
            )
    
    def test_payment_analytics_summary(self):
        """Test payment analytics summary"""
        url = reverse('payment-analytics-summary')
        response = self.client.get(url, {'days': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('total_payments', data)
        self.assertIn('successful_payments', data)
        self.assertIn('failed_payments', data)
        self.assertIn('total_amount', data)
        self.assertIn('success_rate', data)
        
        # Check calculations
        self.assertEqual(data['total_payments'], 3)
        self.assertEqual(data['successful_payments'], 1)
        self.assertEqual(data['failed_payments'], 1)
    
    def test_payment_analytics_by_provider(self):
        """Test payment analytics by provider"""
        url = reverse('payment-analytics-by-provider')
        response = self.client.get(url, {'days': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIsInstance(data, list)
        
        # Should have data for demo provider
        demo_data = next((item for item in data if item['provider'] == 'demo'), None)
        self.assertIsNotNone(demo_data)
        self.assertIn('payment_count', demo_data)
        self.assertIn('total_amount', demo_data)
    
    def test_payment_trends(self):
        """Test payment trends over time"""
        url = reverse('payment-trends')
        response = self.client.get(url, {'days': 7, 'granularity': 'daily'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) <= 7)  # Should have max 7 days of data
        
        # Check data structure
        for day_data in data:
            self.assertIn('date', day_data)
            self.assertIn('payment_count', day_data)
            self.assertIn('total_amount', day_data)
            self.assertIn('success_rate', day_data)