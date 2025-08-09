"""
Test cases for ads app
"""

from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, Mock
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from ads.models import (
    AdCategory, AdCampaign, AdGroup, AdCreative, AdPlacement,
    AdAuction, AdImpression, AdClick, AdConversion, AdKeyword,
    AdAudienceSegment, AdBudgetSpend
)
from ads.services import AdAuctionService, AdImpressionService
from .base import BaseAPITestCase, TestDataFactory, AuthenticationTestMixin, FilteringTestMixin


class AdCategoryAPITestCase(BaseAPITestCase, AuthenticationTestMixin):
    """Test cases for Ad Category API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        # Create parent category
        self.parent_category = AdCategory.objects.create(
            name="Electronics",
            description="Electronic products",
            organization=self.organization,
            is_active=True,
            sort_order=1
        )
        
        # Create child category
        self.child_category = AdCategory.objects.create(
            name="Smartphones",
            description="Mobile phones",
            parent=self.parent_category,
            organization=self.organization,
            is_active=True,
            sort_order=1
        )
    
    def get_url(self):
        return reverse('ads:adcategory-list')
    
    def test_category_list(self):
        """Test listing ad categories"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 2)
    
    def test_category_tree(self):
        """Test getting category tree structure"""
        url = reverse('ads:category-tree')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIsInstance(data, list)
        
        # Find parent category in response
        parent_data = next((cat for cat in data if cat['name'] == 'Electronics'), None)
        self.assertIsNotNone(parent_data)
        self.assertIn('children', parent_data)
        self.assertTrue(len(parent_data['children']) >= 1)
        
        # Check child category
        child_data = parent_data['children'][0]
        self.assertEqual(child_data['name'], 'Smartphones')
    
    def test_create_category(self):
        """Test creating ad category"""
        data = {
            "name": "Fashion",
            "description": "Fashion products",
            "keywords": ["clothes", "fashion", "apparel"],
            "targeting_attributes": {
                "demographics": ["18-35"],
                "interests": ["fashion", "style"]
            }
        }
        
        response = self.client.post(self.get_url(), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        category = AdCategory.objects.get(name="Fashion")
        self.assertEqual(category.description, "Fashion products")
        self.assertEqual(category.keywords, ["clothes", "fashion", "apparel"])
        self.assertEqual(category.organization, self.organization)


class AdPlacementAPITestCase(BaseAPITestCase, AuthenticationTestMixin):
    """Test cases for Ad Placement API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        self.placement = TestDataFactory.create_ad_placement(
            self.organization,
            name="Search Results",
            placement_type="search_results"
        )
    
    def get_url(self):
        return reverse('ads:adplacement-list')
    
    def test_placement_list(self):
        """Test listing ad placements"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_placement_performance(self):
        """Test getting placement performance metrics"""
        # Create impression data
        campaign = TestDataFactory.create_ad_campaign(self.merchant, self.organization)
        creative = AdCreative.objects.create(
            ad_group=campaign.ad_groups.create(name="Test Group"),
            name="Test Creative",
            creative_type="text",
            headline="Test Ad",
            destination_url="https://example.com",
            status="active"
        )
        
        AdImpression.objects.create(
            creative=creative,
            placement=self.placement,
            customer=self.customer,
            impression_id="test_imp_123",
            page_url="https://example.com/search",
            bid_amount=Decimal('5.00'),
            cost=Decimal('4.50'),
            organization=self.organization
        )
        
        url = reverse('ads:placement-performance', kwargs={'pk': self.placement.pk})
        response = self.client.get(url, {'days': 30})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('impressions', data)
        self.assertIn('clicks', data)
        self.assertIn('conversions', data)
        self.assertIn('cost', data)
        self.assertIn('ctr', data)
        self.assertEqual(data['impressions'], 1)


class AdCampaignAPITestCase(BaseAPITestCase, AuthenticationTestMixin, FilteringTestMixin):
    """Test cases for Ad Campaign API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_merchant()
        
        self.campaign = TestDataFactory.create_ad_campaign(
            self.merchant, self.organization
        )
    
    def get_url(self):
        return reverse('ads:adcampaign-list')
    
    def get_list_url(self):
        return self.get_url()
    
    def create_test_objects_for_filtering(self):
        # Create campaigns with different statuses
        TestDataFactory.create_ad_campaign(
            self.merchant, self.organization,
            name="Active Campaign",
            status="active"
        )
        TestDataFactory.create_ad_campaign(
            self.merchant, self.organization,
            name="Paused Campaign", 
            status="paused"
        )
    
    def get_filter_test_cases(self):
        return [
            ('status', 'active', 1),
            ('status', 'paused', 1),
            ('campaign_type', 'search', 2)  # Both are search campaigns
        ]
    
    def test_campaign_list(self):
        """Test listing campaigns"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
        
        # Check merchant can only see their campaigns
        for campaign in data['results']:
            self.assertEqual(campaign['advertiser'], str(self.merchant.id))
    
    def test_create_campaign(self):
        """Test creating ad campaign"""
        data = {
            "name": "New Campaign",
            "description": "Test campaign description",
            "campaign_type": "display",
            "bidding_strategy": "target_cpa",
            "daily_budget": "500.00",
            "total_budget": "15000.00",
            "default_bid": "3.00",
            "target_cpa": "50.00",
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2023-12-31T23:59:59Z",
            "target_keywords": ["electronics", "gadgets"],
            "target_demographics": {
                "age_ranges": ["25-34", "35-44"],
                "genders": ["male", "female"]
            }
        }
        
        response = self.client.post(self.get_url(), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        campaign = AdCampaign.objects.get(name="New Campaign")
        self.assertEqual(campaign.advertiser, self.merchant)
        self.assertEqual(campaign.campaign_type, "display")
        self.assertEqual(campaign.bidding_strategy, "target_cpa")
        self.assertEqual(campaign.target_cpa, Decimal('50.00'))
    
    def test_campaign_approve(self):
        """Test approving campaign"""
        # Set campaign to pending approval
        self.campaign.status = 'pending_approval'
        self.campaign.save()
        
        # Switch to admin authentication
        self.authenticate_admin()
        
        url = reverse('ads:campaign-approve', kwargs={'pk': self.campaign.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'active')
        self.assertIsNotNone(self.campaign.approved_at)
    
    def test_campaign_reject(self):
        """Test rejecting campaign"""
        self.campaign.status = 'pending_approval'
        self.campaign.save()
        
        self.authenticate_admin()
        
        data = {"reason": "Inappropriate content"}
        url = reverse('ads:campaign-reject', kwargs={'pk': self.campaign.pk})
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'rejected')
        self.assertEqual(self.campaign.rejection_reason, "Inappropriate content")
    
    def test_campaign_pause_resume(self):
        """Test pausing and resuming campaign"""
        # Test pause
        url = reverse('ads:campaign-pause', kwargs={'pk': self.campaign.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'paused')
        
        # Test resume
        url = reverse('ads:campaign-resume', kwargs={'pk': self.campaign.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, 'active')
    
    @patch('ads.services.AdReportingService.generate_campaign_report')
    def test_campaign_report(self, mock_report):
        """Test generating campaign report"""
        mock_report.return_value = {
            "campaign_id": str(self.campaign.id),
            "campaign_name": self.campaign.name,
            "period": "2023-01-01 to 2023-01-31",
            "total_impressions": 10000,
            "total_clicks": 500,
            "total_conversions": 25,
            "total_spend": Decimal('2500.00'),
            "total_revenue": Decimal('5000.00'),
            "ctr": Decimal('5.00'),
            "cpc": Decimal('5.00'),
            "cpa": Decimal('100.00'),
            "roas": Decimal('200.00'),
            "time_series": []
        }
        
        data = {
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2023-01-31T23:59:59Z",
            "granularity": "daily"
        }
        
        url = reverse('ads:campaign-report', kwargs={'pk': self.campaign.pk})
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        report_data = response.json()
        self.assertEqual(report_data['total_impressions'], 10000)
        self.assertEqual(report_data['total_clicks'], 500)
        self.assertEqual(str(report_data['ctr']), '5.00')
    
    def test_campaign_dashboard(self):
        """Test campaign dashboard data"""
        url = reverse('ads:campaign-dashboard')
        response = self.client.get(url, {'days': 30})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('total_campaigns', data)
        self.assertIn('active_campaigns', data)
        self.assertIn('total_spend', data)
        self.assertIn('total_revenue', data)
        self.assertIn('overall_ctr', data)
        self.assertIn('campaign_performance', data)


class AdAuctionServiceTestCase(BaseAPITestCase):
    """Test cases for Ad Auction Service"""
    
    def setUp(self):
        super().setUp()
        
        # Create placement and campaign
        self.placement = TestDataFactory.create_ad_placement(
            self.organization,
            placement_type="search_results"
        )
        
        self.campaign = TestDataFactory.create_ad_campaign(
            self.merchant, self.organization,
            status="active",
            daily_budget=Decimal('1000.00'),
            default_bid=Decimal('5.00')
        )
        
        # Create ad group and creative
        self.ad_group = AdGroup.objects.create(
            campaign=self.campaign,
            name="Test Ad Group",
            status="active",
            default_bid=Decimal('4.00')
        )
        
        self.creative = AdCreative.objects.create(
            ad_group=self.ad_group,
            name="Test Creative",
            creative_type="text",
            headline="Test Ad Headline",
            description="Test ad description",
            destination_url="https://example.com",
            status="active"
        )
        
        self.auction_service = AdAuctionService(self.organization)
    
    def test_conduct_auction_success(self):
        """Test successful ad auction"""
        user_context = {
            "session_id": "test_session_123",
            "device_type": "desktop",
            "location": {"lat": 28.05, "lng": 77.05},
            "demographics": {"age_range": "25-34", "gender": "male"}
        }
        
        page_context = {
            "page_url": "https://example.com/search",
            "search_query": "electronics",
            "category": "electronics"
        }
        
        device_context = {
            "user_agent": "Mozilla/5.0 Test Browser",
            "device_type": "desktop",
            "os": "Windows",
            "browser": "Chrome"
        }
        
        auction_result = self.auction_service.conduct_auction(
            placement=self.placement,
            user_context=user_context,
            page_context=page_context,
            device_context=device_context
        )
        
        self.assertIsNotNone(auction_result)
        self.assertIn('auction_id', auction_result)
        self.assertIn('creative', auction_result)
        self.assertIn('bid_amount', auction_result)
        self.assertIn('clearing_price', auction_result)
        
        # Check auction was recorded
        auction = AdAuction.objects.get(id=auction_result['auction_id'])
        self.assertEqual(auction.placement, self.placement)
        self.assertEqual(auction.winner_creative, self.creative)
    
    def test_auction_no_eligible_campaigns(self):
        """Test auction with no eligible campaigns"""
        # Pause the campaign
        self.campaign.status = 'paused'
        self.campaign.save()
        
        user_context = {"session_id": "test_session", "device_type": "mobile"}
        page_context = {"page_url": "https://example.com/search"}
        device_context = {"device_type": "mobile"}
        
        auction_result = self.auction_service.conduct_auction(
            placement=self.placement,
            user_context=user_context,
            page_context=page_context,
            device_context=device_context
        )
        
        self.assertIsNone(auction_result)
    
    def test_multiple_campaigns_auction(self):
        """Test auction with multiple competing campaigns"""
        # Create another campaign with higher bid
        campaign2 = TestDataFactory.create_ad_campaign(
            self.merchant, self.organization,
            name="High Bid Campaign",
            status="active",
            default_bid=Decimal('8.00')
        )
        
        ad_group2 = AdGroup.objects.create(
            campaign=campaign2,
            name="High Bid Group",
            status="active"
        )
        
        creative2 = AdCreative.objects.create(
            ad_group=ad_group2,
            name="High Bid Creative",
            creative_type="text",
            headline="High Bid Ad",
            destination_url="https://example2.com",
            status="active"
        )
        
        user_context = {"session_id": "test_session", "device_type": "desktop"}
        page_context = {"page_url": "https://example.com/search"}
        device_context = {"device_type": "desktop"}
        
        auction_result = self.auction_service.conduct_auction(
            placement=self.placement,
            user_context=user_context,
            page_context=page_context,
            device_context=device_context
        )
        
        # Higher bid campaign should win
        self.assertEqual(auction_result['creative']['id'], str(creative2.id))
        self.assertGreater(auction_result['bid_amount'], Decimal('4.00'))


class AdTrackingAPITestCase(BaseAPITestCase):
    """Test cases for Ad Tracking API"""
    
    def setUp(self):
        super().setUp()
        # No authentication required for tracking endpoints
        
        self.placement = TestDataFactory.create_ad_placement(self.organization)
        self.campaign = TestDataFactory.create_ad_campaign(self.merchant, self.organization)
        
        self.ad_group = AdGroup.objects.create(
            campaign=self.campaign,
            name="Test Group",
            status="active"
        )
        
        self.creative = AdCreative.objects.create(
            ad_group=self.ad_group,
            name="Test Creative",
            creative_type="text",
            headline="Test Ad",
            destination_url="https://example.com",
            status="active"
        )
    
    @patch('ads.services.AdAuctionService.conduct_auction')
    def test_auction_endpoint(self, mock_auction):
        """Test auction tracking endpoint"""
        mock_auction.return_value = {
            "auction_id": str(uuid.uuid4()),
            "creative": {
                "id": str(self.creative.id),
                "headline": "Test Ad",
                "destination_url": "https://example.com"
            },
            "bid_amount": Decimal('5.00'),
            "clearing_price": Decimal('4.50'),
            "request_id": "req_123"
        }
        
        data = {
            "placement_id": str(self.placement.id),
            "user_context": {
                "session_id": "test_session",
                "device_type": "desktop"
            },
            "page_context": {
                "page_url": "https://example.com/search"
            },
            "device_context": {
                "device_type": "desktop"
            }
        }
        
        url = reverse('ads:track-auction')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIn('creative', response_data)
        self.assertIn('bid_amount', response_data)
    
    def test_impression_tracking(self):
        """Test impression tracking endpoint"""
        # First create an impression
        impression = AdImpression.objects.create(
            creative=self.creative,
            placement=self.placement,
            customer=self.customer,
            impression_id="test_imp_track",
            page_url="https://example.com/search",
            bid_amount=Decimal('5.00'),
            cost=Decimal('4.50'),
            organization=self.organization
        )
        
        data = {
            "impression_id": "test_imp_track",
            "viewable": True,
            "view_duration": 5000,
            "scroll_depth": 80.5
        }
        
        url = reverse('ads:track-impression')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check impression was updated
        impression.refresh_from_db()
        self.assertTrue(impression.viewable)
        self.assertEqual(impression.view_duration, 5000)
        self.assertEqual(impression.scroll_depth, Decimal('80.50'))
    
    def test_click_tracking(self):
        """Test click tracking endpoint"""
        impression = AdImpression.objects.create(
            creative=self.creative,
            placement=self.placement,
            customer=self.customer,
            impression_id="test_click_imp",
            page_url="https://example.com/search",
            bid_amount=Decimal('5.00'),
            cost=Decimal('4.50'),
            organization=self.organization
        )
        
        data = {
            "impression_id": "test_click_imp",
            "click_position": {"x": 150, "y": 250},
            "time_to_click": 3,
            "destination_url": "https://example.com/product"
        }
        
        url = reverse('ads:track-click')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIn('click_id', response_data)
        self.assertIn('is_valid', response_data)
        
        # Check click was created
        click = AdClick.objects.get(impression=impression)
        self.assertEqual(click.time_to_click, 3)
        self.assertEqual(click.click_position, {"x": 150, "y": 250})
    
    def test_conversion_tracking(self):
        """Test conversion tracking endpoint"""
        impression = AdImpression.objects.create(
            creative=self.creative,
            placement=self.placement,
            customer=self.customer,
            impression_id="test_conv_imp",
            page_url="https://example.com/search",
            bid_amount=Decimal('5.00'),
            cost=Decimal('4.50'),
            organization=self.organization
        )
        
        click = AdClick.objects.create(
            impression=impression,
            creative=self.creative,
            click_id="test_click_conv",
            destination_url="https://example.com/product",
            cost=Decimal('4.50'),
            is_valid=True
        )
        
        data = {
            "click_id": "test_click_conv",
            "conversion_type": "purchase",
            "conversion_value": "150.00",
            "order_id": str(uuid.uuid4()),
            "attribution_model": "last_click",
            "verification_method": "automatic"
        }
        
        url = reverse('ads:track-conversion')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIn('conversion_id', response_data)
        self.assertIn('conversion_value', response_data)
        
        # Check conversion was created
        conversion = AdConversion.objects.get(click=click)
        self.assertEqual(conversion.conversion_type, "purchase")
        self.assertEqual(conversion.conversion_value, Decimal('150.00'))


class AdKeywordAPITestCase(BaseAPITestCase, AuthenticationTestMixin):
    """Test cases for Ad Keyword API"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_merchant()
        
        self.campaign = TestDataFactory.create_ad_campaign(self.merchant, self.organization)
        self.ad_group = AdGroup.objects.create(
            campaign=self.campaign,
            name="Test Group",
            status="active"
        )
        
        self.keyword = AdKeyword.objects.create(
            ad_group=self.ad_group,
            keyword_text="test keyword",
            match_type="broad",
            bid_amount=Decimal('3.00'),
            status="active"
        )
    
    def get_url(self):
        return reverse('ads:adkeyword-list')
    
    def test_keyword_list(self):
        """Test listing keywords"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    @patch('ads.views.AdKeywordViewSet.suggest')
    def test_keyword_suggestions(self, mock_suggest):
        """Test keyword suggestions"""
        mock_suggestions = [
            {
                "keyword_text": "test keyword online",
                "match_type": "broad",
                "monthly_searches": 5000,
                "competition_level": "medium",
                "suggested_bid": Decimal('4.50'),
                "relevance_score": Decimal('8.5')
            }
        ]
        
        data = {
            "seed_keywords": ["test", "keyword"],
            "match_types": ["broad", "phrase"],
            "max_suggestions": 10
        }
        
        url = reverse('ads:keyword-suggest')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIsInstance(response_data, list)
    
    def test_bulk_update_bids(self):
        """Test bulk updating keyword bids"""
        data = {
            "keywords": [
                {
                    "keyword_id": str(self.keyword.id),
                    "bid_amount": "5.00"
                }
            ]
        }
        
        url = reverse('ads:keyword-bulk-update-bids')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertEqual(response_data['updated_count'], 1)
        
        # Check keyword was updated
        self.keyword.refresh_from_db()
        self.assertEqual(self.keyword.bid_amount, Decimal('5.00'))


class AdBudgetSpendTestCase(BaseAPITestCase, AuthenticationTestMixin):
    """Test cases for Ad Budget Spend tracking"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        self.campaign = TestDataFactory.create_ad_campaign(
            self.merchant, self.organization,
            daily_budget=Decimal('500.00')
        )
        
        # Create budget spend record
        self.budget_spend = AdBudgetSpend.objects.create(
            campaign=self.campaign,
            spend_date=datetime.now().date(),
            daily_budget=Decimal('500.00'),
            total_spend=Decimal('350.00'),
            impressions=5000,
            clicks=250,
            conversions=12,
            revenue=Decimal('1200.00')
        )
    
    def get_url(self):
        return reverse('ads:budgetspend-list')
    
    def test_budget_spend_list(self):
        """Test listing budget spend records"""
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_budget_spend_summary(self):
        """Test budget spend summary"""
        url = reverse('ads:budget-spend-summary')
        response = self.client.get(url, {'days': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('total_budget', data)
        self.assertIn('total_spend', data)
        self.assertIn('budget_utilization', data)
        self.assertIn('total_impressions', data)
        self.assertIn('total_clicks', data)
        self.assertIn('total_conversions', data)
        self.assertIn('total_revenue', data)