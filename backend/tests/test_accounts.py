"""
Test cases for accounts app
"""

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from accounts.models import Organization, Customer, Merchant, Rider
from .base import BaseAPITestCase, AuthenticationTestMixin, PaginationTestMixin

User = get_user_model()


class OrganizationAPITestCase(BaseAPITestCase, AuthenticationTestMixin, PaginationTestMixin):
    """Test cases for Organization API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
    
    def get_url(self):
        return reverse('organization-list')
    
    def get_list_url(self):
        return reverse('organization-list')
    
    def create_test_objects(self, count):
        for i in range(count):
            Organization.objects.create(
                name=f"Test Org {i}",
                domain=f"test{i}.super.com",
                is_active=True
            )
    
    def test_create_organization(self):
        """Test creating a new organization"""
        data = {
            "name": "New Organization",
            "domain": "new.super.com",
            "settings": {
                "currency": "INR",
                "timezone": "Asia/Kolkata"
            }
        }
        
        response = self.client.post(self.get_url(), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        org = Organization.objects.get(domain="new.super.com")
        self.assertEqual(org.name, "New Organization")
        self.assertTrue(org.is_active)
    
    def test_organization_list(self):
        """Test listing organizations"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)  # At least the test org
    
    def test_organization_detail(self):
        """Test getting organization details"""
        url = reverse('organization-detail', kwargs={'pk': self.organization.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['name'], self.organization.name)
        self.assertEqual(data['domain'], self.organization.domain)


class UserRegistrationTestCase(BaseAPITestCase):
    """Test cases for user registration"""
    
    def test_customer_registration(self):
        """Test customer user registration"""
        data = {
            "email": "newcustomer@test.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
            "first_name": "New",
            "last_name": "Customer",
            "user_type": "customer",
            "phone_number": "+919876543213",
            "date_of_birth": "1995-05-15",
            "gender": "female"
        }
        
        url = reverse('auth-register')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check user was created
        user = User.objects.get(email="newcustomer@test.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "Customer")
        
        # Check customer profile was created
        customer = Customer.objects.get(user=user)
        self.assertEqual(customer.phone_number, "+919876543213")
        self.assertEqual(customer.gender, "female")
    
    def test_merchant_registration(self):
        """Test merchant user registration"""
        data = {
            "email": "newmerchant@test.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
            "first_name": "New",
            "last_name": "Merchant",
            "user_type": "merchant",
            "business_name": "New Business",
            "business_type": "restaurant",
            "phone_number": "+919876543214",
            "address": "New Business Address",
            "city": "New City",
            "state": "New State",
            "pincode": "654321"
        }
        
        url = reverse('auth-register')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check user was created
        user = User.objects.get(email="newmerchant@test.com")
        self.assertEqual(user.first_name, "New")
        
        # Check merchant profile was created
        merchant = Merchant.objects.get(user=user)
        self.assertEqual(merchant.business_name, "New Business")
        self.assertEqual(merchant.business_type, "restaurant")
    
    def test_password_mismatch_registration(self):
        """Test registration with password mismatch"""
        data = {
            "email": "test@test.com",
            "password": "pass123",
            "password_confirm": "different123",
            "first_name": "Test",
            "last_name": "User",
            "user_type": "customer"
        }
        
        url = reverse('auth-register')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_duplicate_email_registration(self):
        """Test registration with duplicate email"""
        data = {
            "email": "customer@test.com",  # Already exists
            "password": "newpass123",
            "password_confirm": "newpass123",
            "first_name": "Test",
            "last_name": "User",
            "user_type": "customer"
        }
        
        url = reverse('auth-register')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthenticationTestCase(BaseAPITestCase):
    """Test cases for authentication"""
    
    def test_login_success(self):
        """Test successful login"""
        data = {
            "email": "customer@test.com",
            "password": "testpass123"
        }
        
        url = reverse('auth-login')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], "customer@test.com")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            "email": "customer@test.com",
            "password": "wrongpassword"
        }
        
        url = reverse('auth-login')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_inactive_user(self):
        """Test login with inactive user"""
        self.customer_user.is_active = False
        self.customer_user.save()
        
        data = {
            "email": "customer@test.com",
            "password": "testpass123"
        }
        
        url = reverse('auth-login')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh(self):
        """Test token refresh"""
        # First login to get refresh token
        login_data = {
            "email": "customer@test.com",
            "password": "testpass123"
        }
        
        login_url = reverse('auth-login')
        login_response = self.client.post(login_url, login_data, format='json')
        refresh_token = login_response.json()['refresh']
        
        # Use refresh token to get new access token
        refresh_data = {
            "refresh": refresh_token
        }
        
        refresh_url = reverse('auth-refresh')
        refresh_response = self.client.post(refresh_url, refresh_data, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.json())
    
    def test_logout(self):
        """Test logout"""
        # First login
        self.authenticate_customer()
        
        # Get refresh token
        login_data = {
            "email": "customer@test.com",
            "password": "testpass123"
        }
        
        login_url = reverse('auth-login')
        login_response = self.client.post(login_url, login_data, format='json')
        refresh_token = login_response.json()['refresh']
        
        # Logout
        logout_data = {
            "refresh": refresh_token
        }
        
        logout_url = reverse('auth-logout')
        logout_response = self.client.post(logout_url, logout_data, format='json')
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)


class UserProfileTestCase(BaseAPITestCase):
    """Test cases for user profile management"""
    
    def test_get_profile_customer(self):
        """Test getting customer profile"""
        self.authenticate_customer()
        
        url = reverse('auth-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['email'], "customer@test.com")
        self.assertEqual(data['user_type'], "customer")
        self.assertIn('customer_profile', data)
    
    def test_get_profile_merchant(self):
        """Test getting merchant profile"""
        self.authenticate_merchant()
        
        url = reverse('auth-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['email'], "merchant@test.com")
        self.assertEqual(data['user_type'], "merchant")
        self.assertIn('merchant_profile', data)
    
    def test_update_profile(self):
        """Test updating user profile"""
        self.authenticate_customer()
        
        data = {
            "first_name": "Updated",
            "last_name": "Name",
            "customer_profile": {
                "phone_number": "+919876543299"
            }
        }
        
        url = reverse('auth-profile')
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check updates were applied
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.first_name, "Updated")
        self.assertEqual(self.customer_user.last_name, "Name")
        
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone_number, "+919876543299")


class CustomerAPITestCase(BaseAPITestCase, AuthenticationTestMixin):
    """Test cases for Customer API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
    
    def get_url(self):
        return reverse('customer-list')
    
    def test_customer_list(self):
        """Test listing customers"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_customer_detail(self):
        """Test getting customer details"""
        url = reverse('customer-detail', kwargs={'pk': self.customer.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['phone_number'], self.customer.phone_number)
    
    def test_customer_orders(self):
        """Test getting customer orders"""
        # Create a test order
        from .base import TestDataFactory
        order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization
        )
        
        url = reverse('customer-orders', kwargs={'pk': self.customer.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(len(data) >= 1)
        self.assertEqual(data[0]['order_number'], order.order_number)


class MerchantAPITestCase(BaseAPITestCase, AuthenticationTestMixin):
    """Test cases for Merchant API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
    
    def get_url(self):
        return reverse('merchant-list')
    
    def test_merchant_list(self):
        """Test listing merchants"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_merchant_detail(self):
        """Test getting merchant details"""
        url = reverse('merchant-detail', kwargs={'pk': self.merchant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['business_name'], self.merchant.business_name)
    
    def test_merchant_approve(self):
        """Test approving merchant"""
        self.merchant.status = 'pending'
        self.merchant.save()
        
        url = reverse('merchant-approve', kwargs={'pk': self.merchant.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.status, 'approved')
    
    def test_merchant_reject(self):
        """Test rejecting merchant"""
        data = {
            "reason": "Incomplete documentation"
        }
        
        url = reverse('merchant-reject', kwargs={'pk': self.merchant.pk})
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.status, 'rejected')
        self.assertEqual(self.merchant.rejection_reason, "Incomplete documentation")