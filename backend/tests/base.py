"""
Base test classes and utilities for SUPER platform testing
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import Mock, patch
import uuid
from decimal import Decimal

from accounts.models import Organization, Customer, Merchant, Rider
from orders.models import Order, OrderItem
from catalog.models import Product, Category
from payments_upi.models import UPIPayment, Settlement
from logistics.models import DeliveryZone, DeliveryBatch, DeliveryTask
from rewards.models import RewardsCampaign, RewardTransaction
from ads.models import AdCampaign, AdCreative, AdPlacement

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test case with common setup for all tests"""
    
    def setUp(self):
        """Set up test data"""
        self.setup_organization()
        self.setup_users()
        self.setup_basic_data()
    
    def setup_organization(self):
        """Create test organization"""
        self.organization = Organization.objects.create(
            name="Test Organization",
            domain="test.super.com",
            is_active=True,
            settings={
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "language": "en"
            }
        )
    
    def setup_users(self):
        """Create test users"""
        # Admin user
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            is_staff=True,
            is_superuser=True,
            organization=self.organization
        )
        
        # Customer user
        self.customer_user = User.objects.create_user(
            email="customer@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Customer",
            organization=self.organization
        )
        
        self.customer = Customer.objects.create(
            user=self.customer_user,
            organization=self.organization,
            phone_number="+919876543210",
            date_of_birth="1990-01-01",
            gender="male"
        )
        
        # Merchant user
        self.merchant_user = User.objects.create_user(
            email="merchant@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Merchant",
            organization=self.organization
        )
        
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            organization=self.organization,
            business_name="Test Business",
            business_type="retail",
            phone_number="+919876543211",
            address="Test Address",
            city="Test City",
            state="Test State",
            pincode="123456"
        )
        
        # Rider user
        self.rider_user = User.objects.create_user(
            email="rider@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Rider",
            organization=self.organization
        )
        
        self.rider = Rider.objects.create(
            user=self.rider_user,
            organization=self.organization,
            phone_number="+919876543212",
            vehicle_type="bike",
            license_number="TEST123"
        )
    
    def setup_basic_data(self):
        """Create basic test data"""
        # Category
        self.category = Category.objects.create(
            name="Test Category",
            organization=self.organization
        )
        
        # Product
        self.product = Product.objects.create(
            name="Test Product",
            description="Test product description",
            price=Decimal('100.00'),
            category=self.category,
            merchant=self.merchant,
            organization=self.organization,
            is_active=True
        )
        
        # Delivery Zone
        self.delivery_zone = DeliveryZone.objects.create(
            name="Test Zone",
            organization=self.organization,
            zone_type="city",
            is_active=True
        )


class BaseAPITestCase(APITestCase):
    """Base API test case with authentication helpers"""
    
    def setUp(self):
        """Set up API test data"""
        self.setup_organization()
        self.setup_users()
        self.setup_basic_data()
        self.client = APIClient()
    
    def setup_organization(self):
        """Create test organization"""
        self.organization = Organization.objects.create(
            name="Test Organization",
            domain="test.super.com",
            is_active=True,
            settings={
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "language": "en"
            }
        )
    
    def setup_users(self):
        """Create test users"""
        # Admin user
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            is_staff=True,
            is_superuser=True,
            organization=self.organization
        )
        
        # Customer user
        self.customer_user = User.objects.create_user(
            email="customer@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Customer",
            organization=self.organization
        )
        
        self.customer = Customer.objects.create(
            user=self.customer_user,
            organization=self.organization,
            phone_number="+919876543210",
            date_of_birth="1990-01-01",
            gender="male"
        )
        
        # Merchant user
        self.merchant_user = User.objects.create_user(
            email="merchant@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Merchant",
            organization=self.organization
        )
        
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            organization=self.organization,
            business_name="Test Business",
            business_type="retail",
            phone_number="+919876543211",
            address="Test Address",
            city="Test City",
            state="Test State",
            pincode="123456"
        )
    
    def setup_basic_data(self):
        """Create basic test data"""
        # Category
        self.category = Category.objects.create(
            name="Test Category",
            organization=self.organization
        )
        
        # Product
        self.product = Product.objects.create(
            name="Test Product",
            description="Test product description",
            price=Decimal('100.00'),
            category=self.category,
            merchant=self.merchant,
            organization=self.organization,
            is_active=True
        )
    
    def get_jwt_token(self, user):
        """Get JWT token for user"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_user(self, user):
        """Authenticate user for API requests"""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return token
    
    def authenticate_admin(self):
        """Authenticate admin user"""
        return self.authenticate_user(self.admin_user)
    
    def authenticate_customer(self):
        """Authenticate customer user"""
        return self.authenticate_user(self.customer_user)
    
    def authenticate_merchant(self):
        """Authenticate merchant user"""
        return self.authenticate_user(self.merchant_user)


class MockExternalServices:
    """Mock external services for testing"""
    
    @staticmethod
    def mock_upi_payment():
        """Mock UPI payment response"""
        return Mock(
            transaction_id="TEST_TXN_123",
            status="success",
            amount=Decimal('100.00'),
            provider_response={"status": "SUCCESS"},
            created_at="2023-01-01T10:00:00Z"
        )
    
    @staticmethod
    def mock_osrm_response():
        """Mock OSRM routing response"""
        return {
            "routes": [{
                "duration": 1800,  # 30 minutes
                "distance": 15000,  # 15km
                "geometry": "test_geometry"
            }]
        }
    
    @staticmethod
    def mock_porter_response():
        """Mock Porter API response"""
        return {
            "order_id": "PORTER_123",
            "status": "confirmed",
            "fare": {
                "total_fare": 50.0
            },
            "driver": {
                "name": "Test Driver",
                "phone": "+919876543213"
            }
        }


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_order(customer, merchant, organization, **kwargs):
        """Create test order"""
        defaults = {
            "order_number": f"ORD{uuid.uuid4().hex[:8].upper()}",
            "status": "pending",
            "total_amount": Decimal('200.00'),
            "delivery_fee": Decimal('20.00'),
            "tax_amount": Decimal('36.00'),
            "discount_amount": Decimal('0.00'),
            "net_amount": Decimal('256.00'),
            "payment_method": "upi",
            "delivery_address": "Test Delivery Address"
        }
        defaults.update(kwargs)
        
        return Order.objects.create(
            customer=customer,
            merchant=merchant,
            organization=organization,
            **defaults
        )
    
    @staticmethod
    def create_order_item(order, product, **kwargs):
        """Create test order item"""
        defaults = {
            "quantity": 2,
            "unit_price": product.price,
            "total_price": product.price * 2
        }
        defaults.update(kwargs)
        
        return OrderItem.objects.create(
            order=order,
            product=product,
            **defaults
        )
    
    @staticmethod
    def create_upi_payment(order, **kwargs):
        """Create test UPI payment"""
        defaults = {
            "provider": "demo",
            "transaction_id": f"TXN{uuid.uuid4().hex[:8].upper()}",
            "amount": order.net_amount,
            "status": "pending",
            "provider_transaction_id": f"PROV{uuid.uuid4().hex[:8].upper()}",
            "payment_method": "upi"
        }
        defaults.update(kwargs)
        
        return UPIPayment.objects.create(
            order=order,
            customer=order.customer,
            organization=order.organization,
            **defaults
        )
    
    @staticmethod
    def create_ad_placement(organization, **kwargs):
        """Create test ad placement"""
        defaults = {
            "name": "Test Placement",
            "description": "Test placement for ads",
            "placement_type": "search_results",
            "base_cpm": Decimal('10.00'),
            "base_cpc": Decimal('1.00'),
            "minimum_bid": Decimal('0.50'),
            "is_active": True
        }
        defaults.update(kwargs)
        
        return AdPlacement.objects.create(
            organization=organization,
            **defaults
        )
    
    @staticmethod
    def create_ad_campaign(merchant, organization, **kwargs):
        """Create test ad campaign"""
        defaults = {
            "name": "Test Campaign",
            "description": "Test ad campaign",
            "campaign_type": "search",
            "status": "active",
            "bidding_strategy": "manual_cpc",
            "daily_budget": Decimal('1000.00'),
            "default_bid": Decimal('5.00'),
            "start_date": "2023-01-01T00:00:00Z",
            "created_by": str(merchant.user.id)
        }
        defaults.update(kwargs)
        
        return AdCampaign.objects.create(
            advertiser=merchant,
            organization=organization,
            **defaults
        )


# Test mixins for common functionality
class AuthenticationTestMixin:
    """Mixin for testing authentication"""
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 401)
    
    def test_wrong_organization_access_denied(self):
        """Test that users from different organizations cannot access resources"""
        # Create another organization and user
        other_org = Organization.objects.create(
            name="Other Organization",
            domain="other.super.com",
            is_active=True
        )
        
        other_user = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            organization=other_org
        )
        
        # Authenticate with other organization user
        self.authenticate_user(other_user)
        
        # Try to access resource from first organization
        response = self.client.get(self.get_url())
        self.assertIn(response.status_code, [403, 404])
    
    def get_url(self):
        """Override in test classes to provide the URL to test"""
        raise NotImplementedError("Must override get_url method")


class PaginationTestMixin:
    """Mixin for testing pagination"""
    
    def test_pagination_works(self):
        """Test that pagination works correctly"""
        # Create enough objects to trigger pagination
        self.create_test_objects(25)  # More than default page size of 20
        
        response = self.client.get(self.get_list_url())
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 20)  # Default page size
    
    def create_test_objects(self, count):
        """Override in test classes to create objects for pagination testing"""
        raise NotImplementedError("Must override create_test_objects method")
    
    def get_list_url(self):
        """Override in test classes to provide the list URL"""
        raise NotImplementedError("Must override get_list_url method")


class FilteringTestMixin:
    """Mixin for testing filtering"""
    
    def test_basic_filtering_works(self):
        """Test that basic filtering works"""
        self.create_test_objects_for_filtering()
        
        # Test each filter
        for filter_param, filter_value, expected_count in self.get_filter_test_cases():
            with self.subTest(filter_param=filter_param, filter_value=filter_value):
                response = self.client.get(
                    self.get_list_url(),
                    {filter_param: filter_value}
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()
                if 'results' in data:
                    self.assertEqual(len(data['results']), expected_count)
                else:
                    self.assertEqual(len(data), expected_count)
    
    def create_test_objects_for_filtering(self):
        """Override in test classes to create objects for filter testing"""
        raise NotImplementedError("Must override create_test_objects_for_filtering method")
    
    def get_filter_test_cases(self):
        """Override in test classes to provide filter test cases"""
        raise NotImplementedError("Must override get_filter_test_cases method")