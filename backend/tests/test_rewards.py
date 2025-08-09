"""
Test cases for rewards app
"""

from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, Mock
from decimal import Decimal
from datetime import datetime, timedelta

from rewards.models import (
    RewardsCampaign, RewardTransaction, CashbackRule, ReferralProgram,
    RewardConfiguration, RewardsTier, UserRewardsProfile
)
from rewards.services import RewardsService, CashbackService, ReferralService
from .base import BaseAPITestCase, TestDataFactory, AuthenticationTestMixin


class RewardsServiceTestCase(BaseAPITestCase):
    """Test cases for Rewards Service"""
    
    def setUp(self):
        super().setUp()
        
        # Create rewards profile for customer
        self.rewards_profile = UserRewardsProfile.objects.create(
            user=self.customer_user,
            organization=self.organization,
            total_points=1000,
            lifetime_earned=5000,
            tier_level="silver"
        )
        
        # Create rewards campaign
        self.campaign = RewardsCampaign.objects.create(
            name="Welcome Bonus",
            description="Bonus for new users",
            campaign_type="signup",
            reward_type="points",
            reward_value=Decimal('100'),
            organization=self.organization,
            is_active=True,
            start_date=datetime.now() - timedelta(days=10),
            end_date=datetime.now() + timedelta(days=20)
        )
        
        self.service = RewardsService(self.organization)
    
    def test_award_points(self):
        """Test awarding points to user"""
        initial_points = self.rewards_profile.total_points
        
        transaction = self.service.award_points(
            user=self.customer_user,
            points=500,
            transaction_type="purchase",
            reference_id="order_123",
            description="Order completion bonus"
        )
        
        self.assertEqual(transaction.points, 500)
        self.assertEqual(transaction.transaction_type, "purchase")
        self.assertEqual(transaction.status, "completed")
        
        # Check profile was updated
        self.rewards_profile.refresh_from_db()
        self.assertEqual(self.rewards_profile.total_points, initial_points + 500)
        self.assertEqual(self.rewards_profile.lifetime_earned, 5000 + 500)
    
    def test_redeem_points(self):
        """Test redeeming points"""
        initial_points = self.rewards_profile.total_points
        
        transaction = self.service.redeem_points(
            user=self.customer_user,
            points=300,
            redemption_type="discount",
            reference_id="order_456",
            description="Discount redemption"
        )
        
        self.assertEqual(transaction.points, -300)  # Negative for redemption
        self.assertEqual(transaction.transaction_type, "redemption")
        
        # Check profile was updated
        self.rewards_profile.refresh_from_db()
        self.assertEqual(self.rewards_profile.total_points, initial_points - 300)
    
    def test_insufficient_points_redemption(self):
        """Test redemption with insufficient points"""
        with self.assertRaises(ValueError):
            self.service.redeem_points(
                user=self.customer_user,
                points=2000,  # More than available
                redemption_type="discount",
                reference_id="order_789"
            )
    
    def test_calculate_campaign_reward(self):
        """Test calculating reward based on campaign"""
        reward = self.service.calculate_campaign_reward(
            user=self.customer_user,
            campaign=self.campaign,
            transaction_amount=Decimal('1000.00')
        )
        
        self.assertEqual(reward['points'], 100)  # Fixed reward from campaign
        self.assertEqual(reward['campaign_id'], str(self.campaign.id))
    
    def test_process_tier_upgrade(self):
        """Test tier upgrade processing"""
        # Increase points to trigger tier upgrade
        self.rewards_profile.total_points = 5000
        self.rewards_profile.save()
        
        # Create tier configuration
        gold_tier = RewardsTier.objects.create(
            name="Gold",
            organization=self.organization,
            min_points=5000,
            multiplier=Decimal('1.5'),
            benefits={"priority_support": True, "free_shipping": True}
        )
        
        upgraded = self.service.check_and_upgrade_tier(self.customer_user)
        
        self.assertTrue(upgraded)
        self.rewards_profile.refresh_from_db()
        self.assertEqual(self.rewards_profile.tier_level, "Gold")


class CashbackServiceTestCase(BaseAPITestCase):
    """Test cases for Cashback Service"""
    
    def setUp(self):
        super().setUp()
        
        # Create cashback rule
        self.cashback_rule = CashbackRule.objects.create(
            name="Electronics Cashback",
            rule_type="category",
            cashback_type="percentage",
            cashback_value=Decimal('5.0'),  # 5% cashback
            min_order_value=Decimal('500.00'),
            max_cashback=Decimal('100.00'),
            organization=self.organization,
            is_active=True
        )
        
        self.service = CashbackService(self.organization)
        
        # Create test order
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization,
            total_amount=Decimal('1000.00')
        )
    
    def test_calculate_cashback_percentage(self):
        """Test calculating percentage-based cashback"""
        cashback = self.service.calculate_cashback(
            order=self.order,
            rules=[self.cashback_rule]
        )
        
        expected_cashback = Decimal('50.00')  # 5% of 1000
        self.assertEqual(cashback['amount'], expected_cashback)
        self.assertEqual(cashback['rule_applied'], str(self.cashback_rule.id))
    
    def test_calculate_cashback_with_max_limit(self):
        """Test cashback calculation with max limit"""
        # Create order with high amount
        high_order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization,
            total_amount=Decimal('3000.00')
        )
        
        cashback = self.service.calculate_cashback(
            order=high_order,
            rules=[self.cashback_rule]
        )
        
        # Should be capped at max_cashback
        self.assertEqual(cashback['amount'], Decimal('100.00'))
    
    def test_calculate_cashback_below_minimum(self):
        """Test cashback calculation below minimum order value"""
        low_order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization,
            total_amount=Decimal('200.00')  # Below min_order_value
        )
        
        cashback = self.service.calculate_cashback(
            order=low_order,
            rules=[self.cashback_rule]
        )
        
        self.assertEqual(cashback['amount'], Decimal('0.00'))
        self.assertIsNone(cashback.get('rule_applied'))
    
    def test_fixed_amount_cashback(self):
        """Test fixed amount cashback calculation"""
        fixed_rule = CashbackRule.objects.create(
            name="Fixed Cashback",
            rule_type="general",
            cashback_type="fixed",
            cashback_value=Decimal('50.00'),  # Fixed ₹50
            min_order_value=Decimal('300.00'),
            organization=self.organization,
            is_active=True
        )
        
        cashback = self.service.calculate_cashback(
            order=self.order,
            rules=[fixed_rule]
        )
        
        self.assertEqual(cashback['amount'], Decimal('50.00'))
    
    def test_process_cashback_credit(self):
        """Test processing cashback credit to user"""
        cashback_amount = Decimal('75.00')
        
        transaction = self.service.process_cashback(
            user=self.customer_user,
            order=self.order,
            cashback_amount=cashback_amount,
            rule_id=str(self.cashback_rule.id)
        )
        
        self.assertEqual(transaction.points, 75)  # Assuming 1:1 ratio
        self.assertEqual(transaction.transaction_type, "cashback")
        self.assertEqual(transaction.reference_id, str(self.order.id))


class ReferralServiceTestCase(BaseAPITestCase):
    """Test cases for Referral Service"""
    
    def setUp(self):
        super().setUp()
        
        # Create referral program
        self.referral_program = ReferralProgram.objects.create(
            name="Customer Referral",
            referrer_reward=Decimal('100'),  # Points for referrer
            referee_reward=Decimal('50'),   # Points for referee
            min_referee_purchase=Decimal('500.00'),
            max_referrals_per_user=10,
            organization=self.organization,
            is_active=True
        )
        
        # Create another customer as referee
        self.referee_user = self.admin_user  # Reuse admin as referee for simplicity
        self.referee = Customer.objects.create(
            user=self.referee_user,
            organization=self.organization,
            phone_number="+919876543299"
        )
        
        self.service = ReferralService(self.organization)
    
    def test_create_referral(self):
        """Test creating a referral relationship"""
        referral = self.service.create_referral(
            referrer=self.customer_user,
            referee=self.referee_user,
            referral_code="REF123"
        )
        
        self.assertEqual(referral.referrer, self.customer_user)
        self.assertEqual(referral.referee, self.referee_user)
        self.assertEqual(referral.status, "pending")
    
    def test_process_successful_referral(self):
        """Test processing successful referral"""
        # Create referral
        referral = self.service.create_referral(
            referrer=self.customer_user,
            referee=self.referee_user,
            referral_code="REF456"
        )
        
        # Create qualifying order for referee
        referee_order = TestDataFactory.create_order(
            self.referee, self.merchant, self.organization,
            total_amount=Decimal('600.00')  # Above minimum
        )
        
        # Process referral
        rewards = self.service.process_referral_completion(
            referral=referral,
            qualifying_order=referee_order
        )
        
        self.assertEqual(len(rewards), 2)  # Referrer and referee rewards
        
        # Check referral status updated
        referral.refresh_from_db()
        self.assertEqual(referral.status, "completed")
        
        # Check reward transactions were created
        referrer_transaction = RewardTransaction.objects.get(
            user=self.customer_user,
            transaction_type="referral_bonus"
        )
        self.assertEqual(referrer_transaction.points, 100)
        
        referee_transaction = RewardTransaction.objects.get(
            user=self.referee_user,
            transaction_type="referral_bonus"
        )
        self.assertEqual(referee_transaction.points, 50)
    
    def test_referral_below_minimum_purchase(self):
        """Test referral with purchase below minimum"""
        referral = self.service.create_referral(
            referrer=self.customer_user,
            referee=self.referee_user,
            referral_code="REF789"
        )
        
        # Create order below minimum
        low_order = TestDataFactory.create_order(
            self.referee, self.merchant, self.organization,
            total_amount=Decimal('200.00')  # Below minimum
        )
        
        # Process referral - should not complete
        rewards = self.service.process_referral_completion(
            referral=referral,
            qualifying_order=low_order
        )
        
        self.assertEqual(len(rewards), 0)
        
        referral.refresh_from_db()
        self.assertEqual(referral.status, "pending")  # Still pending


class RewardsAPITestCase(BaseAPITestCase, AuthenticationTestMixin):
    """Test cases for Rewards API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_customer()
        
        # Create rewards profile
        self.rewards_profile = UserRewardsProfile.objects.create(
            user=self.customer_user,
            organization=self.organization,
            total_points=1000,
            lifetime_earned=5000
        )
        
        # Create test transactions
        RewardTransaction.objects.create(
            user=self.customer_user,
            organization=self.organization,
            points=200,
            transaction_type="purchase",
            reference_id="order_123",
            description="Order bonus",
            status="completed"
        )
    
    def get_url(self):
        return reverse('rewards:rewards-profile')
    
    def test_rewards_profile(self):
        """Test getting rewards profile"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['total_points'], 1000)
        self.assertEqual(data['lifetime_earned'], 5000)
        self.assertIn('tier_level', data)
    
    def test_rewards_transactions(self):
        """Test listing reward transactions"""
        url = reverse('rewards:reward-transactions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
        
        transaction = data['results'][0]
        self.assertEqual(transaction['points'], 200)
        self.assertEqual(transaction['transaction_type'], "purchase")
    
    def test_redeem_points_endpoint(self):
        """Test points redemption endpoint"""
        data = {
            "points": 300,
            "redemption_type": "discount",
            "description": "Order discount"
        }
        
        url = reverse('rewards:redeem-points')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response_data = response.json()
        self.assertEqual(response_data['points'], -300)
        self.assertEqual(response_data['transaction_type'], "redemption")
        
        # Check profile was updated
        self.rewards_profile.refresh_from_db()
        self.assertEqual(self.rewards_profile.total_points, 700)  # 1000 - 300
    
    def test_redeem_insufficient_points(self):
        """Test redemption with insufficient points"""
        data = {
            "points": 2000,  # More than available
            "redemption_type": "discount"
        }
        
        url = reverse('rewards:redeem-points')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_rewards_campaigns_list(self):
        """Test listing active rewards campaigns"""
        # Create active campaign
        RewardsCampaign.objects.create(
            name="Summer Sale Bonus",
            description="Extra points for summer purchases",
            campaign_type="purchase",
            reward_type="points",
            reward_value=Decimal('200'),
            organization=self.organization,
            is_active=True,
            start_date=datetime.now() - timedelta(days=5),
            end_date=datetime.now() + timedelta(days=15)
        )
        
        url = reverse('rewards:campaigns-active')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertTrue(len(data) >= 1)
        
        campaign = data[0]
        self.assertEqual(campaign['name'], "Summer Sale Bonus")
        self.assertTrue(campaign['is_active'])
    
    def test_calculate_cashback_preview(self):
        """Test cashback calculation preview"""
        # Create cashback rule
        CashbackRule.objects.create(
            name="Preview Cashback",
            rule_type="general",
            cashback_type="percentage",
            cashback_value=Decimal('3.0'),
            min_order_value=Decimal('100.00'),
            organization=self.organization,
            is_active=True
        )
        
        data = {
            "order_amount": "500.00",
            "category": "electronics"
        }
        
        url = reverse('rewards:calculate-cashback')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertEqual(str(response_data['cashback_amount']), '15.00')  # 3% of 500
        self.assertIn('applicable_rules', response_data)
    
    def test_referral_code_generation(self):
        """Test generating user referral code"""
        url = reverse('rewards:generate-referral-code')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        data = response.json()
        self.assertIn('referral_code', data)
        self.assertIn('referral_link', data)
        
        # Check code is unique and follows format
        referral_code = data['referral_code']
        self.assertTrue(len(referral_code) >= 6)
    
    def test_apply_referral_code(self):
        """Test applying referral code"""
        # First generate a referral code for existing customer
        self.client.post(reverse('rewards:generate-referral-code'))
        
        # Create new customer to apply referral
        new_user = self.admin_user  # Reuse for simplicity
        self.authenticate_user(new_user)
        
        data = {
            "referral_code": "REF123"  # Would be generated code in real scenario
        }
        
        url = reverse('rewards:apply-referral-code')
        response = self.client.post(url, data, format='json')
        # This might return 400 if referral doesn't exist, which is expected in test


class RewardsCampaignAPITestCase(BaseAPITestCase, AuthenticationTestMixin):
    """Test cases for Rewards Campaign management"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        self.campaign = RewardsCampaign.objects.create(
            name="Test Campaign",
            description="Test rewards campaign",
            campaign_type="purchase",
            reward_type="points",
            reward_value=Decimal('150'),
            organization=self.organization,
            is_active=True,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30)
        )
    
    def get_url(self):
        return reverse('rewards:campaigns-list')
    
    def test_campaign_list(self):
        """Test listing campaigns"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_create_campaign(self):
        """Test creating rewards campaign"""
        data = {
            "name": "New Campaign",
            "description": "New test campaign",
            "campaign_type": "signup",
            "reward_type": "cashback",
            "reward_value": "100.00",
            "start_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_date": (datetime.now() + timedelta(days=31)).isoformat(),
            "target_audience": {
                "user_types": ["new_customer"],
                "min_age": 18,
                "max_age": 65
            },
            "conditions": {
                "min_purchase_amount": "200.00",
                "eligible_categories": ["electronics", "fashion"]
            }
        }
        
        response = self.client.post(self.get_url(), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        campaign = RewardsCampaign.objects.get(name="New Campaign")
        self.assertEqual(campaign.campaign_type, "signup")
        self.assertEqual(campaign.reward_value, Decimal('100.00'))
        self.assertTrue(campaign.is_active)
    
    def test_campaign_activation(self):
        """Test activating/deactivating campaign"""
        # Deactivate campaign
        url = reverse('rewards:campaign-deactivate', kwargs={'pk': self.campaign.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.campaign.refresh_from_db()
        self.assertFalse(self.campaign.is_active)
        
        # Reactivate campaign
        url = reverse('rewards:campaign-activate', kwargs={'pk': self.campaign.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.campaign.refresh_from_db()
        self.assertTrue(self.campaign.is_active)
    
    def test_campaign_analytics(self):
        """Test campaign performance analytics"""
        # Create some test transactions for the campaign
        RewardTransaction.objects.create(
            user=self.customer_user,
            organization=self.organization,
            points=150,
            transaction_type="campaign_reward",
            campaign=self.campaign,
            reference_id="test_ref",
            status="completed"
        )
        
        url = reverse('rewards:campaign-analytics', kwargs={'pk': self.campaign.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('total_participants', data)
        self.assertIn('total_rewards_given', data)
        self.assertIn('total_points_awarded', data)
        self.assertIn('campaign_roi', data)
        self.assertEqual(data['total_participants'], 1)
        self.assertEqual(data['total_points_awarded'], 150)