from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    AdCategory, AdCampaign, AdGroup, AdCreative, AdPlacement,
    AdAuction, AdImpression, AdClick, AdConversion, AdBudgetSpend,
    AdKeyword, AdAudienceSegment, AdReportingData
)
from .serializers import (
    AdCategorySerializer, AdCampaignSerializer, AdGroupSerializer,
    AdCreativeSerializer, AdPlacementSerializer, AdKeywordSerializer,
    AdAudienceSegmentSerializer, AdImpressionSerializer,
    AdClickSerializer, AdConversionSerializer, AdBudgetSpendSerializer,
    AuctionRequestSerializer, AuctionResponseSerializer,
    ImpressionTrackingSerializer, ClickTrackingSerializer,
    ConversionTrackingSerializer, CampaignReportRequestSerializer,
    CampaignReportResponseSerializer, BidOptimizationRequestSerializer,
    BidOptimizationResponseSerializer, AdAnalyticsSerializer,
    KeywordSuggestionRequestSerializer, KeywordSuggestionResponseSerializer
)
from .services import (
    AdAuctionService, AdImpressionService, AdReportingService,
    AdBiddingOptimizationService
)
from .filters import (
    AdCampaignFilter, AdCreativeFilter, AdImpressionFilter,
    AdClickFilter, AdConversionFilter
)
from accounts.permissions import IsOrganizationMember
from accounts.models import Merchant


class AdCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for ad categories"""
    
    serializer_class = AdCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'parent']
    
    def get_queryset(self):
        return AdCategory.objects.filter(
            organization=self.request.user.organization
        ).select_related('parent').order_by('sort_order', 'name')
    
    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get category tree structure"""
        categories = self.get_queryset().filter(parent__isnull=True)
        
        def build_tree(category):
            children = category.children.filter(is_active=True).order_by('sort_order', 'name')
            return {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'is_active': category.is_active,
                'children': [build_tree(child) for child in children]
            }
        
        tree = [build_tree(cat) for cat in categories]
        return Response(tree)


class AdPlacementViewSet(viewsets.ModelViewSet):
    """ViewSet for ad placements"""
    
    serializer_class = AdPlacementSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'placement_type']
    
    def get_queryset(self):
        return AdPlacement.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related('allowed_categories').order_by('name')
    
    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get placement performance metrics"""
        placement = self.get_object()
        days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Get performance metrics
        impressions_data = AdImpression.objects.filter(
            placement=placement,
            served_at__gte=start_date
        ).aggregate(
            total_impressions=Count('id'),
            total_cost=Sum('cost')
        )
        
        clicks_data = AdClick.objects.filter(
            impression__placement=placement,
            clicked_at__gte=start_date,
            is_valid=True
        ).aggregate(
            total_clicks=Count('id'),
            total_click_cost=Sum('cost')
        )
        
        conversions_data = AdConversion.objects.filter(
            click__impression__placement=placement,
            converted_at__gte=start_date,
            is_verified=True
        ).aggregate(
            total_conversions=Count('id'),
            total_revenue=Sum('conversion_value')
        )
        
        # Calculate metrics
        total_impressions = impressions_data['total_impressions'] or 0
        total_clicks = clicks_data['total_clicks'] or 0
        total_conversions = conversions_data['total_conversions'] or 0
        total_cost = impressions_data['total_cost'] or Decimal('0.00')
        total_revenue = conversions_data['total_revenue'] or Decimal('0.00')
        
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        cpc = (total_cost / total_clicks) if total_clicks > 0 else Decimal('0.00')
        conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        roas = (total_revenue / total_cost * 100) if total_cost > 0 else Decimal('0.00')
        
        return Response({
            'placement_id': placement.id,
            'placement_name': placement.name,
            'period_days': days,
            'impressions': total_impressions,
            'clicks': total_clicks,
            'conversions': total_conversions,
            'cost': total_cost,
            'revenue': total_revenue,
            'ctr': round(ctr, 2),
            'cpc': cpc,
            'conversion_rate': round(conversion_rate, 2),
            'roas': roas
        })


class AdCampaignViewSet(viewsets.ModelViewSet):
    """ViewSet for ad campaigns"""
    
    serializer_class = AdCampaignSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AdCampaignFilter
    
    def get_queryset(self):
        return AdCampaign.objects.filter(
            organization=self.request.user.organization
        ).select_related('advertiser').prefetch_related(
            'target_categories'
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=str(self.request.user.id)
        )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a campaign"""
        campaign = self.get_object()
        
        if campaign.status != 'pending_approval':
            return Response(
                {'error': 'Only campaigns pending approval can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'active'
        campaign.approved_by = str(request.user.id)
        campaign.approved_at = timezone.now()
        campaign.save()
        
        return Response({
            'message': 'Campaign approved successfully',
            'campaign_id': campaign.id
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a campaign"""
        campaign = self.get_object()
        rejection_reason = request.data.get('reason', '')
        
        if campaign.status not in ['pending_approval', 'draft']:
            return Response(
                {'error': 'Only pending or draft campaigns can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'rejected'
        campaign.rejection_reason = rejection_reason
        campaign.save()
        
        return Response({
            'message': 'Campaign rejected',
            'reason': rejection_reason
        })
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause an active campaign"""
        campaign = self.get_object()
        
        if campaign.status != 'active':
            return Response(
                {'error': 'Only active campaigns can be paused'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'paused'
        campaign.save()
        
        return Response({'message': 'Campaign paused successfully'})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused campaign"""
        campaign = self.get_object()
        
        if campaign.status != 'paused':
            return Response(
                {'error': 'Only paused campaigns can be resumed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'active'
        campaign.save()
        
        return Response({'message': 'Campaign resumed successfully'})
    
    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """Generate campaign performance report"""
        campaign = self.get_object()
        serializer = CampaignReportRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            reporting_service = AdReportingService(self.request.user.organization)
            
            report_data = reporting_service.generate_campaign_report(
                campaign=campaign,
                start_date=serializer.validated_data['start_date'],
                end_date=serializer.validated_data['end_date'],
                granularity=serializer.validated_data['granularity']
            )
            
            response_serializer = CampaignReportResponseSerializer(report_data)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def optimize_bids(self, request, pk=None):
        """Optimize campaign bids"""
        campaign = self.get_object()
        serializer = BidOptimizationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            optimization_service = AdBiddingOptimizationService(self.request.user.organization)
            
            recommendations = optimization_service.optimize_campaign_bids(campaign)
            
            response_serializer = BidOptimizationResponseSerializer(recommendations)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get campaigns dashboard data"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        campaigns = self.get_queryset().filter(
            created_at__gte=start_date
        )
        
        # Aggregate metrics
        metrics = campaigns.aggregate(
            total_campaigns=Count('id'),
            active_campaigns=Count('id', filter=Q(status='active')),
            total_spend=Sum('spend'),
            total_revenue=Sum('revenue'),
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks'),
            total_conversions=Sum('conversions')
        )
        
        # Calculate derived metrics
        total_impressions = metrics['total_impressions'] or 0
        total_clicks = metrics['total_clicks'] or 0
        total_conversions = metrics['total_conversions'] or 0
        total_spend = metrics['total_spend'] or Decimal('0.00')
        total_revenue = metrics['total_revenue'] or Decimal('0.00')
        
        overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        overall_cpc = (total_spend / total_clicks) if total_clicks > 0 else Decimal('0.00')
        overall_cpa = (total_spend / total_conversions) if total_conversions > 0 else Decimal('0.00')
        overall_roas = (total_revenue / total_spend * 100) if total_spend > 0 else Decimal('0.00')
        
        # Top performing campaigns
        top_campaigns = list(campaigns.filter(
            impressions__gt=100
        ).order_by('-revenue')[:5].values(
            'id', 'name', 'impressions', 'clicks', 'conversions',
            'spend', 'revenue'
        ))
        
        dashboard_data = {
            'total_campaigns': metrics['total_campaigns'] or 0,
            'active_campaigns': metrics['active_campaigns'] or 0,
            'total_spend': total_spend,
            'total_revenue': total_revenue,
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'overall_ctr': round(overall_ctr, 2),
            'overall_cpc': overall_cpc,
            'overall_cpa': overall_cpa,
            'overall_roas': overall_roas,
            'campaign_performance': top_campaigns,
            'placement_performance': [],  # Would be populated with placement data
            'device_breakdown': {},  # Would be populated with device data
            'hourly_performance': []  # Would be populated with hourly data
        }
        
        serializer = AdAnalyticsSerializer(dashboard_data)
        return Response(serializer.data)


class AdGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for ad groups"""
    
    serializer_class = AdGroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['campaign', 'status']
    
    def get_queryset(self):
        return AdGroup.objects.filter(
            campaign__organization=self.request.user.organization
        ).select_related('campaign').order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause ad group"""
        ad_group = self.get_object()
        ad_group.status = 'paused'
        ad_group.save()
        
        return Response({'message': 'Ad group paused successfully'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate ad group"""
        ad_group = self.get_object()
        ad_group.status = 'active'
        ad_group.save()
        
        return Response({'message': 'Ad group activated successfully'})


class AdCreativeViewSet(viewsets.ModelViewSet):
    """ViewSet for ad creatives"""
    
    serializer_class = AdCreativeSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AdCreativeFilter
    
    def get_queryset(self):
        return AdCreative.objects.filter(
            ad_group__campaign__organization=self.request.user.organization
        ).select_related('ad_group__campaign').order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review and approve/reject creative"""
        creative = self.get_object()
        action_type = request.data.get('action')  # 'approve' or 'reject'
        review_notes = request.data.get('notes', '')
        
        if action_type == 'approve':
            creative.compliance_status = 'approved'
            creative.status = 'active'
            message = 'Creative approved'
        elif action_type == 'reject':
            creative.compliance_status = 'rejected'
            creative.status = 'rejected'
            message = 'Creative rejected'
        else:
            return Response(
                {'error': 'Invalid action. Use "approve" or "reject"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        creative.review_notes = review_notes
        creative.save()
        
        return Response({'message': message, 'notes': review_notes})
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get creative performance metrics"""
        creative = self.get_object()
        days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Get performance data
        impressions = AdImpression.objects.filter(
            creative=creative,
            served_at__gte=start_date
        ).count()
        
        clicks = AdClick.objects.filter(
            creative=creative,
            clicked_at__gte=start_date,
            is_valid=True
        ).count()
        
        conversions = AdConversion.objects.filter(
            creative=creative,
            converted_at__gte=start_date,
            is_verified=True
        ).count()
        
        spend = AdClick.objects.filter(
            creative=creative,
            clicked_at__gte=start_date,
            is_valid=True
        ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        
        revenue = AdConversion.objects.filter(
            creative=creative,
            converted_at__gte=start_date,
            is_verified=True
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0.00')
        
        # Calculate metrics
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cpc = (spend / clicks) if clicks > 0 else Decimal('0.00')
        conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
        cpa = (spend / conversions) if conversions > 0 else Decimal('0.00')
        roas = (revenue / spend * 100) if spend > 0 else Decimal('0.00')
        
        return Response({
            'creative_id': creative.id,
            'creative_name': creative.name,
            'period_days': days,
            'impressions': impressions,
            'clicks': clicks,
            'conversions': conversions,
            'spend': spend,
            'revenue': revenue,
            'ctr': round(ctr, 2),
            'cpc': cpc,
            'conversion_rate': round(conversion_rate, 2),
            'cpa': cpa,
            'roas': roas,
            'quality_score': creative.quality_score
        })


class AdKeywordViewSet(viewsets.ModelViewSet):
    """ViewSet for ad keywords"""
    
    serializer_class = AdKeywordSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ad_group', 'status', 'match_type']
    
    def get_queryset(self):
        return AdKeyword.objects.filter(
            ad_group__campaign__organization=self.request.user.organization
        ).select_related('ad_group__campaign').order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def suggest(self, request):
        """Get keyword suggestions"""
        serializer = KeywordSuggestionRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            seed_keywords = serializer.validated_data['seed_keywords']
            match_types = serializer.validated_data['match_types']
            max_suggestions = serializer.validated_data['max_suggestions']
            
            # Generate keyword suggestions (simplified implementation)
            suggestions = []
            
            for seed in seed_keywords:
                for match_type in match_types:
                    # In a real implementation, this would use keyword research APIs
                    # For now, generating basic variations
                    variations = [
                        f"{seed} online",
                        f"best {seed}",
                        f"{seed} buy",
                        f"{seed} cheap",
                        f"{seed} delivery"
                    ]
                    
                    for variation in variations[:max_suggestions//len(seed_keywords)]:
                        suggestions.append({
                            'keyword_text': variation,
                            'match_type': match_type,
                            'monthly_searches': 1000 + hash(variation) % 5000,  # Mock data
                            'competition_level': 'medium',
                            'suggested_bid': Decimal('10.00') + (hash(variation) % 50),
                            'relevance_score': Decimal('7.5')
                        })
            
            response_serializer = KeywordSuggestionResponseSerializer(
                suggestions[:max_suggestions], many=True
            )
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_update_bids(self, request):
        """Bulk update keyword bids"""
        keyword_updates = request.data.get('keywords', [])
        updated_count = 0
        
        for update in keyword_updates:
            try:
                keyword_id = update.get('keyword_id')
                new_bid = Decimal(str(update.get('bid_amount')))
                
                keyword = AdKeyword.objects.get(
                    id=keyword_id,
                    ad_group__campaign__organization=self.request.user.organization
                )
                
                keyword.bid_amount = new_bid
                keyword.save()
                updated_count += 1
                
            except (AdKeyword.DoesNotExist, ValueError):
                continue
        
        return Response({
            'message': f'Updated {updated_count} keyword bids',
            'updated_count': updated_count
        })


class AdAudienceSegmentViewSet(viewsets.ModelViewSet):
    """ViewSet for audience segments"""
    
    serializer_class = AdAudienceSegmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'segment_type']
    
    def get_queryset(self):
        return AdAudienceSegment.objects.filter(
            organization=self.request.user.organization
        ).select_related('created_by').order_by('-created_at')
    
    def perform_create(self, serializer):
        # Get the merchant (advertiser) from the request user
        try:
            merchant = Merchant.objects.get(user=self.request.user)
            serializer.save(
                organization=self.request.user.organization,
                created_by=merchant
            )
        except Merchant.DoesNotExist:
            # If user is not a merchant, use admin creation
            serializer.save(organization=self.request.user.organization)
    
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """Refresh audience segment data"""
        segment = self.get_object()
        
        # In a real implementation, this would recalculate the segment
        # For now, just update the refresh timestamp and mock size
        segment.last_refreshed = timezone.now()
        segment.size_estimate = 10000 + hash(str(segment.id)) % 50000  # Mock size
        segment.save()
        
        return Response({
            'message': 'Segment refreshed successfully',
            'size_estimate': segment.size_estimate,
            'last_refreshed': segment.last_refreshed
        })


class AdTrackingViewSet(viewsets.ViewSet):
    """ViewSet for ad tracking endpoints"""
    
    permission_classes = []  # Public endpoints for tracking
    
    @action(detail=False, methods=['post'])
    def auction(self, request):
        """Conduct ad auction"""
        serializer = AuctionRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Get organization from placement
                placement = AdPlacement.objects.get(id=serializer.validated_data['placement_id'])
                
                auction_service = AdAuctionService(placement.organization)
                
                auction_result = auction_service.conduct_auction(
                    placement=placement,
                    user_context=serializer.validated_data['user_context'],
                    page_context=serializer.validated_data['page_context'],
                    device_context=serializer.validated_data['device_context']
                )
                
                if auction_result:
                    response_serializer = AuctionResponseSerializer(auction_result)
                    return Response(response_serializer.data)
                else:
                    return Response({'message': 'No ads available'}, status=status.HTTP_204_NO_CONTENT)
                    
            except AdPlacement.DoesNotExist:
                return Response({'error': 'Placement not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def impression(self, request):
        """Track ad impression"""
        impression_id = request.data.get('impression_id')
        serializer = ImpressionTrackingSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                impression = AdImpression.objects.get(impression_id=impression_id)
                
                # Update impression tracking data
                impression.viewable = serializer.validated_data['viewable']
                impression.view_duration = serializer.validated_data['view_duration']
                impression.scroll_depth = serializer.validated_data['scroll_depth']
                impression.save()
                
                return Response({'message': 'Impression tracked successfully'})
                
            except AdImpression.DoesNotExist:
                return Response({'error': 'Impression not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def click(self, request):
        """Track ad click"""
        serializer = ClickTrackingSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                impression = AdImpression.objects.get(
                    impression_id=serializer.validated_data['impression_id']
                )
                
                impression_service = AdImpressionService()
                
                click_context = {
                    'destination_url': serializer.validated_data.get('destination_url'),
                    'click_position': serializer.validated_data['click_position'],
                    'time_to_click': serializer.validated_data['time_to_click']
                }
                
                click = impression_service.record_click(impression, click_context)
                
                return Response({
                    'message': 'Click tracked successfully',
                    'click_id': click.click_id,
                    'is_valid': click.is_valid
                })
                
            except AdImpression.DoesNotExist:
                return Response({'error': 'Impression not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def conversion(self, request):
        """Track ad conversion"""
        serializer = ConversionTrackingSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                click = AdClick.objects.get(
                    click_id=serializer.validated_data['click_id']
                )
                
                impression_service = AdImpressionService()
                
                conversion_data = {
                    'conversion_type': serializer.validated_data['conversion_type'],
                    'conversion_value': serializer.validated_data['conversion_value'],
                    'order_id': serializer.validated_data.get('order_id'),
                    'transaction_id': serializer.validated_data.get('transaction_id'),
                    'custom_data': serializer.validated_data.get('custom_data'),
                    'attribution_model': serializer.validated_data['attribution_model'],
                    'verification_method': serializer.validated_data['verification_method'],
                    'time_to_conversion': 0  # Would be calculated from click time
                }
                
                conversion = impression_service.record_conversion(click, conversion_data)
                
                return Response({
                    'message': 'Conversion tracked successfully',
                    'conversion_id': conversion.id,
                    'conversion_value': conversion.conversion_value
                })
                
            except AdClick.DoesNotExist:
                return Response({'error': 'Click not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdBudgetSpendViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for budget spend tracking - read-only"""
    
    serializer_class = AdBudgetSpendSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['campaign', 'spend_date', 'is_budget_exceeded']
    
    def get_queryset(self):
        return AdBudgetSpend.objects.filter(
            campaign__organization=self.request.user.organization
        ).select_related('campaign').order_by('-spend_date')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get budget spend summary"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now().date() - timedelta(days=days)
        
        spends = self.get_queryset().filter(spend_date__gte=start_date)
        
        summary = spends.aggregate(
            total_budget=Sum('daily_budget'),
            total_spend=Sum('total_spend'),
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks'),
            total_conversions=Sum('conversions'),
            total_revenue=Sum('revenue'),
            days_budget_exceeded=Count('id', filter=Q(is_budget_exceeded=True))
        )
        
        budget_utilization = 0
        if summary['total_budget'] and summary['total_budget'] > 0:
            budget_utilization = (summary['total_spend'] / summary['total_budget']) * 100
        
        return Response({
            'period_days': days,
            'total_budget': summary['total_budget'] or Decimal('0.00'),
            'total_spend': summary['total_spend'] or Decimal('0.00'),
            'budget_utilization': round(budget_utilization, 2),
            'total_impressions': summary['total_impressions'] or 0,
            'total_clicks': summary['total_clicks'] or 0,
            'total_conversions': summary['total_conversions'] or 0,
            'total_revenue': summary['total_revenue'] or Decimal('0.00'),
            'days_budget_exceeded': summary['days_budget_exceeded'] or 0
        })