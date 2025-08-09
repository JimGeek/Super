from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta, datetime
from typing import Dict, List, Optional, Tuple
import logging
import random
import json
from uuid import uuid4

from .models import (
    AdCampaign, AdGroup, AdCreative, AdPlacement, AdAuction,
    AdImpression, AdClick, AdConversion, AdBudgetSpend,
    AdKeyword, AdAudienceSegment, AdReportingData, AdCategory
)
from accounts.models import Organization, Customer, Merchant
from orders.models import Order

logger = logging.getLogger(__name__)


class AdAuctionService:
    """Service for real-time ad auctions"""
    
    def __init__(self, organization: Organization):
        self.organization = organization
    
    def conduct_auction(self, placement: AdPlacement, user_context: Dict, 
                       page_context: Dict, device_context: Dict) -> Optional[Dict]:
        """Conduct real-time ad auction for a placement"""
        
        auction_start = timezone.now()
        request_id = str(uuid4())
        
        try:
            # Get eligible campaigns
            eligible_campaigns = self._get_eligible_campaigns(
                placement, user_context, page_context, device_context
            )
            
            if not eligible_campaigns:
                logger.info(f"No eligible campaigns for placement {placement.id}")
                return None
            
            # Generate bids from eligible campaigns
            bids = self._generate_bids(eligible_campaigns, user_context, page_context)
            
            if not bids:
                logger.info(f"No valid bids for placement {placement.id}")
                return None
            
            # Determine auction winner
            winner = self._determine_winner(bids, placement)
            
            # Calculate clearing price (second-price auction)
            clearing_price = self._calculate_clearing_price(bids, winner)
            
            # Record auction
            auction_duration = (timezone.now() - auction_start).total_seconds() * 1000
            
            auction = AdAuction.objects.create(
                organization=self.organization,
                placement=placement,
                request_id=request_id,
                user_context=user_context,
                page_context=page_context,
                device_context=device_context,
                eligible_campaigns=[str(c.id) for c in eligible_campaigns],
                participating_bids=bids,
                winner_creative=winner['creative'] if winner else None,
                winning_bid=winner['bid_amount'] if winner else None,
                clearing_price=clearing_price,
                total_eligible=len(eligible_campaigns),
                total_participating=len(bids),
                auction_duration_ms=int(auction_duration)
            )
            
            if winner:
                return {
                    'auction_id': auction.id,
                    'creative': winner['creative'],
                    'bid_amount': winner['bid_amount'],
                    'clearing_price': clearing_price,
                    'request_id': request_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Auction error for placement {placement.id}: {str(e)}")
            return None
    
    def _get_eligible_campaigns(self, placement: AdPlacement, user_context: Dict,
                               page_context: Dict, device_context: Dict) -> List[AdCampaign]:
        """Get campaigns eligible for the auction"""
        
        now = timezone.now()
        
        # Base eligibility criteria
        campaigns = AdCampaign.objects.filter(
            organization=self.organization,
            status='active',
            start_date__lte=now
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        ).select_related('advertiser').prefetch_related(
            'ad_groups__creatives', 'target_categories'
        )
        
        eligible = []
        
        for campaign in campaigns:
            # Check budget constraints
            if not self._check_budget_availability(campaign):
                continue
            
            # Check targeting criteria
            if not self._check_targeting(campaign, user_context, page_context, device_context):
                continue
            
            # Check if campaign has active creatives for this placement
            if not self._has_compatible_creatives(campaign, placement):
                continue
            
            eligible.append(campaign)
        
        return eligible
    
    def _check_budget_availability(self, campaign: AdCampaign) -> bool:
        """Check if campaign has available budget"""
        
        # Check total budget
        if campaign.total_budget and campaign.spend >= campaign.total_budget:
            return False
        
        # Check daily budget
        today = timezone.now().date()
        daily_spend = AdBudgetSpend.objects.filter(
            campaign=campaign,
            spend_date=today
        ).first()
        
        if daily_spend and daily_spend.total_spend >= campaign.daily_budget:
            return False
        
        return True
    
    def _check_targeting(self, campaign: AdCampaign, user_context: Dict,
                        page_context: Dict, device_context: Dict) -> bool:
        """Check if campaign targeting matches the context"""
        
        # Geographic targeting
        if campaign.target_locations:
            user_location = user_context.get('location', {})
            if not self._matches_location_targeting(user_location, campaign.target_locations):
                return False
        
        # Device targeting
        if campaign.target_devices:
            device_type = device_context.get('device_type', '')
            if device_type not in campaign.target_devices:
                return False
        
        # Demographic targeting
        if campaign.target_demographics:
            if not self._matches_demographic_targeting(user_context, campaign.target_demographics):
                return False
        
        # Category targeting
        if campaign.target_categories.exists():
            page_category = page_context.get('category')
            if page_category not in [cat.name for cat in campaign.target_categories.all()]:
                return False
        
        # Keyword targeting (for search campaigns)
        if campaign.campaign_type == 'search' and campaign.target_keywords:
            search_query = page_context.get('search_query', '')
            if not self._matches_keyword_targeting(search_query, campaign.target_keywords):
                return False
        
        # Schedule targeting
        if campaign.target_schedule:
            if not self._matches_schedule_targeting(campaign.target_schedule):
                return False
        
        return True
    
    def _has_compatible_creatives(self, campaign: AdCampaign, placement: AdPlacement) -> bool:
        """Check if campaign has creatives compatible with placement"""
        
        supported_formats = placement.supported_formats
        
        for ad_group in campaign.ad_groups.filter(status='active'):
            for creative in ad_group.creatives.filter(status='active'):
                if creative.creative_type in supported_formats:
                    return True
        
        return False
    
    def _generate_bids(self, campaigns: List[AdCampaign], user_context: Dict,
                      page_context: Dict) -> List[Dict]:
        """Generate bids from eligible campaigns"""
        
        bids = []
        
        for campaign in campaigns:
            # Get best creative for this auction
            creative = self._select_best_creative(campaign, user_context, page_context)
            if not creative:
                continue
            
            # Calculate bid amount based on strategy
            bid_amount = self._calculate_bid_amount(campaign, creative, user_context, page_context)
            
            if bid_amount > 0:
                bids.append({
                    'campaign_id': str(campaign.id),
                    'creative': creative,
                    'bid_amount': bid_amount,
                    'quality_score': creative.quality_score or Decimal('5.0'),
                    'ad_rank': bid_amount * (creative.quality_score or Decimal('5.0'))
                })
        
        return bids
    
    def _select_best_creative(self, campaign: AdCampaign, user_context: Dict,
                             page_context: Dict) -> Optional[AdCreative]:
        """Select the best creative for the auction context"""
        
        # Get all active creatives from active ad groups
        creatives = []
        for ad_group in campaign.ad_groups.filter(status='active'):
            for creative in ad_group.creatives.filter(status='active'):
                creatives.append(creative)
        
        if not creatives:
            return None
        
        # Score creatives based on performance and relevance
        scored_creatives = []
        for creative in creatives:
            score = self._calculate_creative_score(creative, user_context, page_context)
            scored_creatives.append((creative, score))
        
        # Return highest scoring creative
        scored_creatives.sort(key=lambda x: x[1], reverse=True)
        return scored_creatives[0][0]
    
    def _calculate_creative_score(self, creative: AdCreative, user_context: Dict,
                                 page_context: Dict) -> Decimal:
        """Calculate relevance score for creative"""
        
        base_score = creative.quality_score or Decimal('5.0')
        
        # Performance factor
        if creative.impressions > 0:
            ctr = (creative.clicks / creative.impressions) * 100
            performance_factor = min(ctr / 2, Decimal('2.0'))  # Cap at 2x
            base_score *= (1 + performance_factor)
        
        # Relevance factors based on context
        # (This would be enhanced with ML models in production)
        
        return base_score
    
    def _calculate_bid_amount(self, campaign: AdCampaign, creative: AdCreative,
                             user_context: Dict, page_context: Dict) -> Decimal:
        """Calculate bid amount based on campaign strategy"""
        
        if campaign.bidding_strategy == 'manual_cpc':
            # Use ad group or campaign default bid
            ad_group = creative.ad_group
            return ad_group.effective_bid
        
        elif campaign.bidding_strategy == 'auto_cpc':
            # Automatic bidding with target CPA
            if campaign.target_cpa:
                # Estimate conversion probability and bid accordingly
                conversion_prob = self._estimate_conversion_probability(
                    campaign, creative, user_context, page_context
                )
                return campaign.target_cpa * conversion_prob
            else:
                return campaign.default_bid
        
        elif campaign.bidding_strategy == 'target_roas':
            # Target return on ad spend bidding
            if campaign.target_roas:
                estimated_value = self._estimate_conversion_value(
                    campaign, user_context, page_context
                )
                target_roas_decimal = campaign.target_roas / 100
                return estimated_value * target_roas_decimal
            else:
                return campaign.default_bid
        
        elif campaign.bidding_strategy == 'maximize_clicks':
            # Bid to maximize clicks within budget
            return self._calculate_maximize_clicks_bid(campaign)
        
        elif campaign.bidding_strategy == 'maximize_conversions':
            # Bid to maximize conversions
            return self._calculate_maximize_conversions_bid(campaign)
        
        else:
            return campaign.default_bid
    
    def _determine_winner(self, bids: List[Dict], placement: AdPlacement) -> Optional[Dict]:
        """Determine auction winner based on ad rank"""
        
        if not bids:
            return None
        
        # Sort by ad rank (bid * quality score)
        sorted_bids = sorted(bids, key=lambda x: x['ad_rank'], reverse=True)
        
        # Check minimum bid requirement
        winner = sorted_bids[0]
        if winner['bid_amount'] < placement.minimum_bid:
            return None
        
        return winner
    
    def _calculate_clearing_price(self, bids: List[Dict], winner: Optional[Dict]) -> Optional[Decimal]:
        """Calculate clearing price for second-price auction"""
        
        if not winner or len(bids) < 2:
            return winner['bid_amount'] if winner else None
        
        # Sort bids by ad rank
        sorted_bids = sorted(bids, key=lambda x: x['ad_rank'], reverse=True)
        
        # Second-price auction: pay just enough to beat second highest bidder
        second_highest = sorted_bids[1]
        winner_quality = winner['quality_score']
        second_quality = second_highest['quality_score']
        
        # Price = (Second Ad Rank / Winner Quality Score) + 0.01
        clearing_price = (second_highest['ad_rank'] / winner_quality) + Decimal('0.01')
        
        # Don't exceed winner's bid
        return min(clearing_price, winner['bid_amount'])
    
    def _matches_location_targeting(self, user_location: Dict, target_locations: List) -> bool:
        """Check if user location matches targeting"""
        # Simplified implementation
        return True  # Would implement proper geo-targeting logic
    
    def _matches_demographic_targeting(self, user_context: Dict, target_demographics: Dict) -> bool:
        """Check if user demographics match targeting"""
        # Simplified implementation
        return True  # Would implement demographic matching logic
    
    def _matches_keyword_targeting(self, search_query: str, target_keywords: List) -> bool:
        """Check if search query matches keyword targeting"""
        if not search_query:
            return False
        
        search_words = search_query.lower().split()
        for keyword in target_keywords:
            keyword_words = keyword.lower().split()
            if all(word in search_words for word in keyword_words):
                return True
        
        return False
    
    def _matches_schedule_targeting(self, target_schedule: Dict) -> bool:
        """Check if current time matches schedule targeting"""
        now = timezone.now()
        current_day = now.strftime('%A').lower()
        current_hour = now.hour
        
        day_schedule = target_schedule.get(current_day, {})
        if not day_schedule:
            return False
        
        start_hour = day_schedule.get('start_hour', 0)
        end_hour = day_schedule.get('end_hour', 23)
        
        return start_hour <= current_hour <= end_hour
    
    def _estimate_conversion_probability(self, campaign: AdCampaign, creative: AdCreative,
                                       user_context: Dict, page_context: Dict) -> Decimal:
        """Estimate probability of conversion (simplified)"""
        
        base_rate = Decimal('0.02')  # 2% base conversion rate
        
        # Adjust based on campaign performance
        if campaign.impressions > 0:
            historical_rate = campaign.conversions / campaign.impressions
            base_rate = (base_rate + Decimal(str(historical_rate))) / 2
        
        # User context adjustments (simplified)
        if user_context.get('returning_user'):
            base_rate *= Decimal('1.5')
        
        return min(base_rate, Decimal('0.20'))  # Cap at 20%
    
    def _estimate_conversion_value(self, campaign: AdCampaign, user_context: Dict,
                                  page_context: Dict) -> Decimal:
        """Estimate conversion value (simplified)"""
        
        # Base on historical campaign performance
        if campaign.conversions > 0:
            avg_value = campaign.revenue / campaign.conversions
            return avg_value
        
        # Default estimate
        return Decimal('500.00')
    
    def _calculate_maximize_clicks_bid(self, campaign: AdCampaign) -> Decimal:
        """Calculate bid to maximize clicks within budget"""
        
        # Simplified implementation
        today = timezone.now().date()
        daily_spend = AdBudgetSpend.objects.filter(
            campaign=campaign,
            spend_date=today
        ).first()
        
        remaining_budget = campaign.daily_budget
        if daily_spend:
            remaining_budget -= daily_spend.total_spend
        
        # Estimate remaining opportunities and bid accordingly
        estimated_opportunities = 100  # Simplified
        return min(remaining_budget / estimated_opportunities, campaign.max_bid or campaign.default_bid)
    
    def _calculate_maximize_conversions_bid(self, campaign: AdCampaign) -> Decimal:
        """Calculate bid to maximize conversions"""
        
        # Use historical CPA as baseline
        if campaign.conversions > 0:
            historical_cpa = campaign.spend / campaign.conversions
            return historical_cpa * Decimal('1.2')  # Bid 20% above historical CPA
        
        return campaign.default_bid


class AdImpressionService:
    """Service for tracking ad impressions"""
    
    def record_impression(self, creative: AdCreative, placement: AdPlacement,
                         auction_result: Dict, user_context: Dict,
                         request_context: Dict) -> AdImpression:
        """Record an ad impression"""
        
        impression_id = str(uuid4())
        
        impression = AdImpression.objects.create(
            creative=creative,
            placement=placement,
            auction_id=auction_result.get('auction_id'),
            customer=user_context.get('customer'),
            session_id=user_context.get('session_id', ''),
            user_agent=request_context.get('user_agent', ''),
            ip_address=request_context.get('ip_address', ''),
            impression_id=impression_id,
            page_url=request_context.get('page_url', ''),
            referrer_url=request_context.get('referrer_url', ''),
            country=user_context.get('country', ''),
            region=user_context.get('region', ''),
            city=user_context.get('city', ''),
            device_type=user_context.get('device_type', ''),
            browser=user_context.get('browser', ''),
            os=user_context.get('os', ''),
            bid_amount=auction_result['bid_amount'],
            cost=auction_result['clearing_price']
        )
        
        # Update campaign metrics
        self._update_campaign_metrics(creative.ad_group.campaign, impressions=1, spend=impression.cost)
        self._update_ad_group_metrics(creative.ad_group, impressions=1, spend=impression.cost)
        self._update_creative_metrics(creative, impressions=1, spend=impression.cost)
        
        # Update daily budget tracking
        self._update_daily_budget(creative.ad_group.campaign, impression.cost)
        
        logger.info(f"Recorded impression {impression_id} for creative {creative.id}")
        return impression
    
    def record_click(self, impression: AdImpression, click_context: Dict) -> AdClick:
        """Record an ad click"""
        
        click_id = str(uuid4())
        
        # Fraud detection
        is_valid, fraud_score, fraud_reason = self._detect_click_fraud(impression, click_context)
        
        cost = impression.cost  # For CPC campaigns
        if not is_valid:
            cost = Decimal('0.00')  # Don't charge for fraudulent clicks
        
        click = AdClick.objects.create(
            impression=impression,
            creative=impression.creative,
            click_id=click_id,
            destination_url=click_context.get('destination_url', impression.creative.destination_url),
            click_position=click_context.get('click_position', {}),
            time_to_click=click_context.get('time_to_click', 0),
            is_valid=is_valid,
            fraud_score=fraud_score,
            fraud_reason=fraud_reason,
            cost=cost
        )
        
        if is_valid:
            # Update campaign metrics
            self._update_campaign_metrics(impression.creative.ad_group.campaign, clicks=1, spend=cost)
            self._update_ad_group_metrics(impression.creative.ad_group, clicks=1, spend=cost)
            self._update_creative_metrics(impression.creative, clicks=1, spend=cost)
            
            # Update daily budget
            self._update_daily_budget(impression.creative.ad_group.campaign, cost)
        
        logger.info(f"Recorded click {click_id} for impression {impression.impression_id}")
        return click
    
    def record_conversion(self, click: AdClick, conversion_data: Dict) -> AdConversion:
        """Record an ad conversion"""
        
        conversion = AdConversion.objects.create(
            click=click,
            creative=click.creative,
            conversion_type=conversion_data.get('conversion_type', 'purchase'),
            conversion_value=Decimal(str(conversion_data.get('conversion_value', '0.00'))),
            attribution_model=conversion_data.get('attribution_model', 'last_click'),
            time_to_conversion=conversion_data.get('time_to_conversion', 0),
            order_id=conversion_data.get('order_id'),
            transaction_id=conversion_data.get('transaction_id', ''),
            conversion_data=conversion_data.get('custom_data', {}),
            is_verified=conversion_data.get('is_verified', True),
            verification_method=conversion_data.get('verification_method', 'automatic')
        )
        
        # Update campaign metrics
        campaign = click.creative.ad_group.campaign
        self._update_campaign_metrics(
            campaign, 
            conversions=1, 
            revenue=conversion.conversion_value
        )
        self._update_ad_group_metrics(
            click.creative.ad_group,
            conversions=1,
            revenue=conversion.conversion_value
        )
        self._update_creative_metrics(
            click.creative,
            conversions=1,
            revenue=conversion.conversion_value
        )
        
        # Update daily budget tracking
        self._update_daily_budget_conversions(campaign, conversion.conversion_value)
        
        logger.info(f"Recorded conversion for click {click.click_id}: {conversion.conversion_type} - ₹{conversion.conversion_value}")
        return conversion
    
    def _detect_click_fraud(self, impression: AdImpression, click_context: Dict) -> Tuple[bool, Decimal, str]:
        """Detect potentially fraudulent clicks"""
        
        fraud_score = Decimal('0.00')
        fraud_reasons = []
        
        # Time-based checks
        time_to_click = click_context.get('time_to_click', 0)
        if time_to_click < 1:  # Less than 1 second
            fraud_score += Decimal('30.0')
            fraud_reasons.append('too_fast')
        
        # IP-based checks
        ip_address = impression.ip_address
        recent_clicks = AdClick.objects.filter(
            impression__ip_address=ip_address,
            clicked_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        if recent_clicks > 5:  # More than 5 clicks from same IP in 1 hour
            fraud_score += Decimal('25.0')
            fraud_reasons.append('ip_frequency')
        
        # User agent checks
        if not impression.user_agent or len(impression.user_agent) < 20:
            fraud_score += Decimal('15.0')
            fraud_reasons.append('suspicious_user_agent')
        
        # Click position checks
        click_pos = click_context.get('click_position', {})
        if not click_pos or (click_pos.get('x', 0) == 0 and click_pos.get('y', 0) == 0):
            fraud_score += Decimal('20.0')
            fraud_reasons.append('invalid_position')
        
        is_valid = fraud_score < Decimal('50.0')  # Threshold for marking as fraudulent
        fraud_reason = ', '.join(fraud_reasons) if fraud_reasons else ''
        
        return is_valid, fraud_score, fraud_reason
    
    def _update_campaign_metrics(self, campaign: AdCampaign, impressions: int = 0,
                                clicks: int = 0, conversions: int = 0,
                                spend: Decimal = Decimal('0.00'),
                                revenue: Decimal = Decimal('0.00')):
        """Update campaign performance metrics"""
        
        campaign.impressions += impressions
        campaign.clicks += clicks
        campaign.conversions += conversions
        campaign.spend += spend
        campaign.revenue += revenue
        campaign.save(update_fields=[
            'impressions', 'clicks', 'conversions', 'spend', 'revenue'
        ])
    
    def _update_ad_group_metrics(self, ad_group: AdGroup, impressions: int = 0,
                                clicks: int = 0, conversions: int = 0,
                                spend: Decimal = Decimal('0.00'),
                                revenue: Decimal = Decimal('0.00')):
        """Update ad group performance metrics"""
        
        ad_group.impressions += impressions
        ad_group.clicks += clicks
        ad_group.conversions += conversions
        ad_group.spend += spend
        ad_group.revenue += revenue
        ad_group.save(update_fields=[
            'impressions', 'clicks', 'conversions', 'spend', 'revenue'
        ])
    
    def _update_creative_metrics(self, creative: AdCreative, impressions: int = 0,
                                clicks: int = 0, conversions: int = 0,
                                spend: Decimal = Decimal('0.00')):
        """Update creative performance metrics"""
        
        creative.impressions += impressions
        creative.clicks += clicks
        creative.conversions += conversions
        creative.spend += spend
        creative.save(update_fields=[
            'impressions', 'clicks', 'conversions', 'spend'
        ])
    
    def _update_daily_budget(self, campaign: AdCampaign, spend: Decimal):
        """Update daily budget tracking"""
        
        today = timezone.now().date()
        daily_spend, created = AdBudgetSpend.objects.get_or_create(
            campaign=campaign,
            spend_date=today,
            defaults={
                'daily_budget': campaign.daily_budget,
                'total_spend': Decimal('0.00'),
                'impressions': 0,
                'clicks': 0,
                'conversions': 0,
                'revenue': Decimal('0.00')
            }
        )
        
        daily_spend.total_spend += spend
        daily_spend.impressions += 1  # Called from impression recording
        
        # Check if budget exceeded
        if daily_spend.total_spend >= daily_spend.daily_budget and not daily_spend.budget_exhausted_at:
            daily_spend.budget_exhausted_at = timezone.now()
            daily_spend.is_budget_exceeded = True
        
        daily_spend.save()
    
    def _update_daily_budget_conversions(self, campaign: AdCampaign, revenue: Decimal):
        """Update conversion data in daily budget tracking"""
        
        today = timezone.now().date()
        daily_spend = AdBudgetSpend.objects.filter(
            campaign=campaign,
            spend_date=today
        ).first()
        
        if daily_spend:
            daily_spend.conversions += 1
            daily_spend.revenue += revenue
            daily_spend.save(update_fields=['conversions', 'revenue'])


class AdReportingService:
    """Service for generating ad performance reports"""
    
    def __init__(self, organization: Organization):
        self.organization = organization
    
    def generate_campaign_report(self, campaign: AdCampaign, start_date: datetime,
                                end_date: datetime, granularity: str = 'daily') -> Dict:
        """Generate comprehensive campaign performance report"""
        
        # Get impressions data
        impressions = AdImpression.objects.filter(
            creative__ad_group__campaign=campaign,
            served_at__gte=start_date,
            served_at__lte=end_date
        )
        
        # Get clicks data
        clicks = AdClick.objects.filter(
            creative__ad_group__campaign=campaign,
            clicked_at__gte=start_date,
            clicked_at__lte=end_date,
            is_valid=True
        )
        
        # Get conversions data
        conversions = AdConversion.objects.filter(
            creative__ad_group__campaign=campaign,
            converted_at__gte=start_date,
            converted_at__lte=end_date,
            is_verified=True
        )
        
        # Aggregate metrics
        metrics = {
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'period': f"{start_date.date()} to {end_date.date()}",
            'total_impressions': impressions.count(),
            'total_clicks': clicks.count(),
            'total_conversions': conversions.count(),
            'total_spend': clicks.aggregate(total=models.Sum('cost'))['total'] or Decimal('0.00'),
            'total_revenue': conversions.aggregate(total=models.Sum('conversion_value'))['total'] or Decimal('0.00'),
        }
        
        # Calculate derived metrics
        if metrics['total_impressions'] > 0:
            metrics['ctr'] = (metrics['total_clicks'] / metrics['total_impressions']) * 100
        else:
            metrics['ctr'] = Decimal('0.00')
        
        if metrics['total_clicks'] > 0:
            metrics['cpc'] = metrics['total_spend'] / metrics['total_clicks']
        else:
            metrics['cpc'] = Decimal('0.00')
        
        if metrics['total_conversions'] > 0:
            metrics['cpa'] = metrics['total_spend'] / metrics['total_conversions']
            metrics['avg_order_value'] = metrics['total_revenue'] / metrics['total_conversions']
        else:
            metrics['cpa'] = Decimal('0.00')
            metrics['avg_order_value'] = Decimal('0.00')
        
        if metrics['total_spend'] > 0:
            metrics['roas'] = (metrics['total_revenue'] / metrics['total_spend']) * 100
        else:
            metrics['roas'] = Decimal('0.00')
        
        # Time series data
        metrics['time_series'] = self._generate_time_series(
            campaign, start_date, end_date, granularity
        )
        
        # Demographic breakdown
        metrics['demographics'] = self._generate_demographic_breakdown(
            impressions, clicks, conversions
        )
        
        # Device breakdown
        metrics['devices'] = self._generate_device_breakdown(
            impressions, clicks, conversions
        )
        
        # Creative performance
        metrics['creatives'] = self._generate_creative_breakdown(
            campaign, start_date, end_date
        )
        
        return metrics
    
    def _generate_time_series(self, campaign: AdCampaign, start_date: datetime,
                             end_date: datetime, granularity: str) -> List[Dict]:
        """Generate time series performance data"""
        
        time_series = []
        current = start_date
        
        if granularity == 'daily':
            delta = timedelta(days=1)
        elif granularity == 'hourly':
            delta = timedelta(hours=1)
        elif granularity == 'weekly':
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(days=1)
        
        while current <= end_date:
            period_end = min(current + delta, end_date)
            
            # Get metrics for this period
            period_impressions = AdImpression.objects.filter(
                creative__ad_group__campaign=campaign,
                served_at__gte=current,
                served_at__lt=period_end
            ).count()
            
            period_clicks = AdClick.objects.filter(
                creative__ad_group__campaign=campaign,
                clicked_at__gte=current,
                clicked_at__lt=period_end,
                is_valid=True
            )
            
            period_conversions = AdConversion.objects.filter(
                creative__ad_group__campaign=campaign,
                converted_at__gte=current,
                converted_at__lt=period_end,
                is_verified=True
            )
            
            click_count = period_clicks.count()
            conversion_count = period_conversions.count()
            spend = period_clicks.aggregate(total=models.Sum('cost'))['total'] or Decimal('0.00')
            revenue = period_conversions.aggregate(total=models.Sum('conversion_value'))['total'] or Decimal('0.00')
            
            time_series.append({
                'date': current.date() if granularity == 'daily' else current.isoformat(),
                'impressions': period_impressions,
                'clicks': click_count,
                'conversions': conversion_count,
                'spend': spend,
                'revenue': revenue,
                'ctr': (click_count / period_impressions * 100) if period_impressions > 0 else 0,
                'cpc': (spend / click_count) if click_count > 0 else 0,
                'cpa': (spend / conversion_count) if conversion_count > 0 else 0,
                'roas': (revenue / spend * 100) if spend > 0 else 0
            })
            
            current = period_end
        
        return time_series
    
    def _generate_demographic_breakdown(self, impressions, clicks, conversions) -> Dict:
        """Generate demographic performance breakdown"""
        
        # Age groups (simplified)
        age_groups = ['18-24', '25-34', '35-44', '45-54', '55+']
        demographics = {}
        
        for age_group in age_groups:
            # This would be based on actual user demographic data
            # For now, using simplified random distribution
            demographics[age_group] = {
                'impressions': impressions.count() // len(age_groups),
                'clicks': clicks.count() // len(age_groups),
                'conversions': conversions.count() // len(age_groups)
            }
        
        return demographics
    
    def _generate_device_breakdown(self, impressions, clicks, conversions) -> Dict:
        """Generate device performance breakdown"""
        
        device_data = {}
        device_types = impressions.values('device_type').distinct()
        
        for device in device_types:
            device_type = device['device_type'] or 'unknown'
            
            device_impressions = impressions.filter(device_type=device_type).count()
            device_clicks = clicks.filter(impression__device_type=device_type).count()
            device_conversions = conversions.filter(
                click__impression__device_type=device_type
            ).count()
            
            device_data[device_type] = {
                'impressions': device_impressions,
                'clicks': device_clicks,
                'conversions': device_conversions,
                'ctr': (device_clicks / device_impressions * 100) if device_impressions > 0 else 0
            }
        
        return device_data
    
    def _generate_creative_breakdown(self, campaign: AdCampaign, start_date: datetime,
                                   end_date: datetime) -> List[Dict]:
        """Generate creative performance breakdown"""
        
        creatives_data = []
        
        for ad_group in campaign.ad_groups.all():
            for creative in ad_group.creatives.all():
                # Get performance data for this creative in the period
                creative_impressions = AdImpression.objects.filter(
                    creative=creative,
                    served_at__gte=start_date,
                    served_at__lte=end_date
                ).count()
                
                creative_clicks = AdClick.objects.filter(
                    creative=creative,
                    clicked_at__gte=start_date,
                    clicked_at__lte=end_date,
                    is_valid=True
                ).count()
                
                creative_conversions = AdConversion.objects.filter(
                    creative=creative,
                    converted_at__gte=start_date,
                    converted_at__lte=end_date,
                    is_verified=True
                ).count()
                
                creatives_data.append({
                    'creative_id': creative.id,
                    'creative_name': creative.name,
                    'creative_type': creative.creative_type,
                    'ad_group': ad_group.name,
                    'impressions': creative_impressions,
                    'clicks': creative_clicks,
                    'conversions': creative_conversions,
                    'ctr': (creative_clicks / creative_impressions * 100) if creative_impressions > 0 else 0,
                    'quality_score': creative.quality_score
                })
        
        return sorted(creatives_data, key=lambda x: x['clicks'], reverse=True)


class AdBiddingOptimizationService:
    """Service for optimizing bid strategies"""
    
    def __init__(self, organization: Organization):
        self.organization = organization
    
    def optimize_campaign_bids(self, campaign: AdCampaign) -> Dict:
        """Optimize bids for a campaign based on performance data"""
        
        if campaign.bidding_strategy not in ['auto_cpc', 'target_cpa', 'target_roas']:
            return {'message': 'Campaign uses manual bidding'}
        
        # Get recent performance data (last 30 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Analyze keyword performance
        keyword_recommendations = self._analyze_keyword_performance(campaign, start_date, end_date)
        
        # Analyze ad group performance
        ad_group_recommendations = self._analyze_ad_group_performance(campaign, start_date, end_date)
        
        # Generate bid recommendations
        recommendations = {
            'campaign_id': campaign.id,
            'optimization_date': timezone.now().isoformat(),
            'bidding_strategy': campaign.bidding_strategy,
            'keyword_recommendations': keyword_recommendations,
            'ad_group_recommendations': ad_group_recommendations,
            'overall_recommendations': []
        }
        
        # Overall campaign recommendations
        if campaign.cpa > 0 and campaign.target_cpa and campaign.cpa > campaign.target_cpa * Decimal('1.2'):
            recommendations['overall_recommendations'].append({
                'type': 'reduce_bids',
                'message': f'CPA (₹{campaign.cpa}) is 20% above target (₹{campaign.target_cpa})',
                'suggested_action': 'Reduce default bid by 15%'
            })
        
        if campaign.ctr < 1.0:
            recommendations['overall_recommendations'].append({
                'type': 'improve_relevance',
                'message': f'Low CTR ({campaign.ctr:.2f}%) indicates poor ad relevance',
                'suggested_action': 'Review ad copy and targeting'
            })
        
        return recommendations
    
    def _analyze_keyword_performance(self, campaign: AdCampaign, start_date: datetime,
                                   end_date: datetime) -> List[Dict]:
        """Analyze keyword performance and suggest bid adjustments"""
        
        recommendations = []
        
        for ad_group in campaign.ad_groups.filter(status='active'):
            for keyword in ad_group.keywords.filter(status='active'):
                # Get keyword performance in the period
                keyword_impressions = AdImpression.objects.filter(
                    creative__ad_group=ad_group,
                    served_at__gte=start_date,
                    served_at__lte=end_date
                ).count()
                
                if keyword_impressions < 100:  # Not enough data
                    continue
                
                keyword_clicks = AdClick.objects.filter(
                    creative__ad_group=ad_group,
                    clicked_at__gte=start_date,
                    clicked_at__lte=end_date,
                    is_valid=True
                ).count()
                
                keyword_conversions = AdConversion.objects.filter(
                    creative__ad_group=ad_group,
                    converted_at__gte=start_date,
                    converted_at__lte=end_date,
                    is_verified=True
                ).count()
                
                ctr = (keyword_clicks / keyword_impressions * 100) if keyword_impressions > 0 else 0
                conversion_rate = (keyword_conversions / keyword_clicks * 100) if keyword_clicks > 0 else 0
                
                current_bid = keyword.effective_bid
                suggested_bid = current_bid
                recommendation = None
                
                # High performing keywords - increase bid
                if ctr > 3.0 and conversion_rate > 2.0:
                    suggested_bid = current_bid * Decimal('1.2')  # Increase by 20%
                    recommendation = 'increase_bid_high_performance'
                
                # Low performing keywords - decrease bid
                elif ctr < 1.0 or (keyword_clicks > 50 and conversion_rate < 0.5):
                    suggested_bid = current_bid * Decimal('0.8')  # Decrease by 20%
                    recommendation = 'decrease_bid_low_performance'
                
                # Keywords with good CTR but low conversions - check landing page
                elif ctr > 2.0 and conversion_rate < 1.0:
                    recommendation = 'check_landing_page'
                
                if recommendation:
                    recommendations.append({
                        'keyword_id': keyword.id,
                        'keyword_text': keyword.keyword_text,
                        'current_bid': current_bid,
                        'suggested_bid': suggested_bid,
                        'recommendation': recommendation,
                        'metrics': {
                            'impressions': keyword_impressions,
                            'clicks': keyword_clicks,
                            'conversions': keyword_conversions,
                            'ctr': ctr,
                            'conversion_rate': conversion_rate
                        }
                    })
        
        return recommendations
    
    def _analyze_ad_group_performance(self, campaign: AdCampaign, start_date: datetime,
                                    end_date: datetime) -> List[Dict]:
        """Analyze ad group performance and suggest bid adjustments"""
        
        recommendations = []
        
        for ad_group in campaign.ad_groups.filter(status='active'):
            # Get ad group performance
            ag_impressions = AdImpression.objects.filter(
                creative__ad_group=ad_group,
                served_at__gte=start_date,
                served_at__lte=end_date
            ).count()
            
            if ag_impressions < 100:  # Not enough data
                continue
            
            ag_clicks = AdClick.objects.filter(
                creative__ad_group=ad_group,
                clicked_at__gte=start_date,
                clicked_at__lte=end_date,
                is_valid=True
            ).count()
            
            ag_conversions = AdConversion.objects.filter(
                creative__ad_group=ad_group,
                converted_at__gte=start_date,
                converted_at__lte=end_date,
                is_verified=True
            ).count()
            
            ag_spend = AdClick.objects.filter(
                creative__ad_group=ad_group,
                clicked_at__gte=start_date,
                clicked_at__lte=end_date,
                is_valid=True
            ).aggregate(total=models.Sum('cost'))['total'] or Decimal('0.00')
            
            ctr = (ag_clicks / ag_impressions * 100) if ag_impressions > 0 else 0
            cpa = (ag_spend / ag_conversions) if ag_conversions > 0 else Decimal('0.00')
            
            current_bid = ad_group.effective_bid
            suggested_bid = current_bid
            recommendation = None
            
            # High performing ad groups - increase bid
            if ctr > 2.5 and ag_conversions > 10 and (not campaign.target_cpa or cpa < campaign.target_cpa):
                suggested_bid = current_bid * Decimal('1.15')  # Increase by 15%
                recommendation = 'increase_bid_good_performance'
            
            # Low performing ad groups - decrease bid
            elif ctr < 1.0 or (campaign.target_cpa and cpa > campaign.target_cpa * Decimal('1.5')):
                suggested_bid = current_bid * Decimal('0.85')  # Decrease by 15%
                recommendation = 'decrease_bid_poor_performance'
            
            if recommendation:
                recommendations.append({
                    'ad_group_id': ad_group.id,
                    'ad_group_name': ad_group.name,
                    'current_bid': current_bid,
                    'suggested_bid': suggested_bid,
                    'recommendation': recommendation,
                    'metrics': {
                        'impressions': ag_impressions,
                        'clicks': ag_clicks,
                        'conversions': ag_conversions,
                        'ctr': ctr,
                        'cpa': cpa,
                        'spend': ag_spend
                    }
                })
        
        return recommendations