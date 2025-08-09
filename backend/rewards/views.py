from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    SuperCashWallet, SuperCashTransaction, RewardCampaign,
    CustomerRewardUsage, SuperCashRedemption, LoyaltyTier,
    CustomerLoyalty, SuperCashExpiry, RewardsSettings
)
from .serializers import (
    SuperCashWalletSerializer, SuperCashTransactionSerializer,
    RewardCampaignSerializer, CustomerRewardUsageSerializer,
    SuperCashRedemptionSerializer, LoyaltyTierSerializer,
    CustomerLoyaltySerializer, SuperCashExpirySerializer,
    RewardsSettingsSerializer, CashbackCalculationRequestSerializer,
    CashbackCalculationResponseSerializer, RedemptionRequestSerializer,
    ReferralRewardRequestSerializer, WalletSummarySerializer,
    CampaignSimulationRequestSerializer, CampaignSimulationResponseSerializer,
    RewardsAnalyticsSerializer, BulkTransactionSerializer
)
from .services import (
    SuperCashService, RewardCampaignService, LoyaltyService,
    SuperCashExpiryService
)
from .filters import (
    SuperCashTransactionFilter, RewardCampaignFilter,
    SuperCashRedemptionFilter, CustomerLoyaltyFilter
)
from accounts.permissions import IsOrganizationMember
from accounts.models import Customer
from orders.models import Order


class SuperCashWalletViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SuperCash wallets - read-only for admin"""
    
    serializer_class = SuperCashWalletSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'is_frozen']
    
    def get_queryset(self):
        return SuperCashWallet.objects.filter(
            organization=self.request.user.organization
        ).select_related('customer').order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get comprehensive wallet summary"""
        wallet = self.get_object()
        supercash_service = SuperCashService(wallet.organization)
        
        summary = supercash_service.get_wallet_summary(wallet.customer)
        serializer = WalletSummarySerializer(summary)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        """Freeze a wallet"""
        wallet = self.get_object()
        reason = request.data.get('reason', 'Administrative action')
        
        wallet.is_frozen = True
        wallet.freeze_reason = reason
        wallet.save()
        
        return Response({
            'message': 'Wallet frozen successfully',
            'reason': reason
        })
    
    @action(detail=True, methods=['post'])
    def unfreeze(self, request, pk=None):
        """Unfreeze a wallet"""
        wallet = self.get_object()
        
        wallet.is_frozen = False
        wallet.freeze_reason = ''
        wallet.save()
        
        return Response({'message': 'Wallet unfrozen successfully'})


class SuperCashTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for SuperCash transactions"""
    
    serializer_class = SuperCashTransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SuperCashTransactionFilter
    
    def get_queryset(self):
        return SuperCashTransaction.objects.filter(
            organization=self.request.user.organization
        ).select_related('wallet__customer', 'order').order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def calculate_cashback(self, request):
        """Calculate cashback for an order"""
        serializer = CashbackCalculationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                order = Order.objects.get(id=serializer.validated_data['order_id'])
                supercash_service = SuperCashService(request.user.organization)
                
                cashback_amount, campaign = supercash_service.calculate_order_cashback(order)
                
                # Get loyalty multiplier
                multiplier = Decimal('1.00')
                try:
                    loyalty = order.customer.loyalty_status
                    if loyalty.current_tier:
                        multiplier = loyalty.current_tier.cashback_multiplier
                        cashback_amount *= multiplier
                except CustomerLoyalty.DoesNotExist:
                    pass
                
                # Calculate expiry
                expires_at = None
                if cashback_amount > 0:
                    expires_at = timezone.now() + timedelta(
                        days=supercash_service.settings.supercash_expiry_days
                    )
                
                response_data = {
                    'cashback_amount': cashback_amount,
                    'campaign_applied': campaign.name if campaign else None,
                    'campaign_id': campaign.id if campaign else None,
                    'base_cashback': cashback_amount / multiplier,
                    'multiplier_applied': multiplier,
                    'expires_at': expires_at
                }
                
                response_serializer = CashbackCalculationResponseSerializer(response_data)
                return Response(response_serializer.data)
                
            except Order.DoesNotExist:
                return Response(
                    {'error': 'Order not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def award_cashback(self, request):
        """Award cashback for an order"""
        order_id = request.data.get('order_id')
        amount = request.data.get('amount')
        campaign_id = request.data.get('campaign_id')
        
        try:
            order = Order.objects.get(id=order_id)
            supercash_service = SuperCashService(request.user.organization)
            
            campaign = None
            if campaign_id:
                campaign = RewardCampaign.objects.get(id=campaign_id)
            
            transaction = supercash_service.award_cashback(
                order=order,
                amount=Decimal(str(amount)),
                campaign=campaign
            )
            
            serializer = self.get_serializer(transaction)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except (Order.DoesNotExist, RewardCampaign.DoesNotExist) as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def process_referral(self, request):
        """Process referral rewards"""
        serializer = ReferralRewardRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                referrer = Customer.objects.get(id=serializer.validated_data['referrer_id'])
                referee = Customer.objects.get(id=serializer.validated_data['referee_id'])
                referee_order = Order.objects.get(id=serializer.validated_data['referee_order_id'])
                
                supercash_service = SuperCashService(request.user.organization)
                
                referrer_txn, referee_txn = supercash_service.process_referral_reward(
                    referrer=referrer,
                    referee=referee,
                    referee_order=referee_order
                )
                
                return Response({
                    'message': 'Referral rewards processed successfully',
                    'referrer_transaction': SuperCashTransactionSerializer(referrer_txn).data,
                    'referee_transaction': SuperCashTransactionSerializer(referee_txn).data
                }, status=status.HTTP_201_CREATED)
                
            except (Customer.DoesNotExist, Order.DoesNotExist) as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_transaction(self, request):
        """Create bulk transactions for multiple customers"""
        serializer = BulkTransactionSerializer(data=request.data)
        
        if serializer.is_valid():
            customer_ids = serializer.validated_data['customer_ids']
            transaction_type = serializer.validated_data['transaction_type']
            amount = serializer.validated_data['amount']
            description = serializer.validated_data['description']
            expires_in_days = serializer.validated_data.get('expires_in_days')
            
            # Get customers
            customers = Customer.objects.filter(
                id__in=customer_ids,
                organization=request.user.organization
            )
            
            if customers.count() != len(customer_ids):
                return Response(
                    {'error': 'Some customer IDs are invalid'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            supercash_service = SuperCashService(request.user.organization)
            created_transactions = []
            
            expires_at = None
            if expires_in_days:
                expires_at = timezone.now() + timedelta(days=expires_in_days)
            
            for customer in customers:
                wallet = supercash_service.get_or_create_wallet(customer)
                
                transaction = SuperCashTransaction.objects.create(
                    wallet=wallet,
                    organization=request.user.organization,
                    transaction_type=transaction_type,
                    amount=amount,
                    description=description,
                    expires_at=expires_at,
                    balance_before=wallet.available_balance,
                    status='completed'
                )
                
                # Update wallet balance for earn transactions
                if transaction_type.startswith('earn_'):
                    wallet.available_balance += amount
                    wallet.lifetime_earned += amount
                else:
                    wallet.available_balance -= amount
                    wallet.lifetime_spent += amount
                
                transaction.balance_after = wallet.available_balance
                wallet.save()
                transaction.save()
                
                created_transactions.append(transaction)
            
            return Response({
                'message': f'Created {len(created_transactions)} transactions',
                'transactions_created': len(created_transactions)
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RewardCampaignViewSet(viewsets.ModelViewSet):
    """ViewSet for reward campaigns"""
    
    serializer_class = RewardCampaignSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RewardCampaignFilter
    
    def get_queryset(self):
        return RewardCampaign.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related('target_merchants').order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=str(self.request.user.id)
        )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a campaign"""
        campaign = self.get_object()
        
        if campaign.status != 'draft':
            return Response(
                {'error': 'Only draft campaigns can be activated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'active'
        campaign.save()
        
        return Response({'message': 'Campaign activated successfully'})
    
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
    
    @action(detail=True, methods=['get'])
    def usage_stats(self, request, pk=None):
        """Get campaign usage statistics"""
        campaign = self.get_object()
        
        usage_data = CustomerRewardUsage.objects.filter(campaign=campaign).aggregate(
            total_usage=Count('id'),
            total_reward_amount=Sum('reward_amount'),
            total_order_amount=Sum('order_amount'),
            unique_customers=Count('customer', distinct=True)
        )
        
        return Response({
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'total_usage': usage_data['total_usage'] or 0,
            'total_reward_amount': usage_data['total_reward_amount'] or Decimal('0.00'),
            'total_order_amount': usage_data['total_order_amount'] or Decimal('0.00'),
            'unique_customers': usage_data['unique_customers'] or 0,
            'avg_reward_per_usage': (usage_data['total_reward_amount'] / usage_data['total_usage']) if usage_data['total_usage'] else Decimal('0.00'),
            'conversion_rate': (usage_data['total_usage'] / campaign.current_uses * 100) if campaign.current_uses else 0
        })
    
    @action(detail=True, methods=['post'])
    def simulate(self, request, pk=None):
        """Simulate campaign impact"""
        campaign = self.get_object()
        serializer = CampaignSimulationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            days = serializer.validated_data['days_to_simulate']
            
            campaign_service = RewardCampaignService(request.user.organization)
            simulation_result = campaign_service.simulate_campaign_impact(campaign, days)
            
            response_serializer = CampaignSimulationResponseSerializer(simulation_result)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SuperCashRedemptionViewSet(viewsets.ModelViewSet):
    """ViewSet for SuperCash redemptions"""
    
    serializer_class = SuperCashRedemptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SuperCashRedemptionFilter
    
    def get_queryset(self):
        return SuperCashRedemption.objects.filter(
            organization=self.request.user.organization
        ).select_related('wallet__customer', 'order').order_by('-initiated_at')
    
    @action(detail=False, methods=['post'])
    def redeem(self, request):
        """Process SuperCash redemption"""
        serializer = RedemptionRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            customer_id = request.data.get('customer_id')
            
            try:
                customer = Customer.objects.get(id=customer_id)
                supercash_service = SuperCashService(request.user.organization)
                
                order = None
                if serializer.validated_data.get('order_id'):
                    order = Order.objects.get(id=serializer.validated_data['order_id'])
                
                redemption = supercash_service.redeem_supercash(
                    customer=customer,
                    amount=serializer.validated_data['amount'],
                    order=order,
                    redemption_type=serializer.validated_data['redemption_type']
                )
                
                response_serializer = self.get_serializer(redemption)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except (Customer.DoesNotExist, Order.DoesNotExist) as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve pending redemption"""
        redemption = self.get_object()
        
        if redemption.status != 'initiated':
            return Response(
                {'error': 'Only initiated redemptions can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        redemption.status = 'processing'
        redemption.processed_by = str(request.user.id)
        redemption.processed_at = timezone.now()
        redemption.save()
        
        return Response({'message': 'Redemption approved and processing'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark redemption as completed"""
        redemption = self.get_object()
        
        if redemption.status != 'processing':
            return Response(
                {'error': 'Only processing redemptions can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        redemption.status = 'completed'
        redemption.completed_at = timezone.now()
        redemption.save()
        
        return Response({'message': 'Redemption completed successfully'})


class LoyaltyTierViewSet(viewsets.ModelViewSet):
    """ViewSet for loyalty tiers"""
    
    serializer_class = LoyaltyTierSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'tier_level']
    
    def get_queryset(self):
        return LoyaltyTier.objects.filter(
            organization=self.request.user.organization
        ).order_by('tier_level')
    
    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
    
    @action(detail=False, methods=['post'])
    def setup_defaults(self, request):
        """Set up default loyalty tiers"""
        loyalty_service = LoyaltyService(request.user.organization)
        tiers = loyalty_service.setup_default_tiers()
        
        serializer = self.get_serializer(tiers, many=True)
        return Response({
            'message': f'Created {len(tiers)} default tiers',
            'tiers': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def evaluate_all_customers(self, request):
        """Evaluate all customers for tier changes"""
        loyalty_service = LoyaltyService(request.user.organization)
        updated_count = loyalty_service.evaluate_all_customers()
        
        return Response({
            'message': f'Evaluated all customers',
            'customers_updated': updated_count
        })


class CustomerLoyaltyViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for customer loyalty status - read-only"""
    
    serializer_class = CustomerLoyaltySerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomerLoyaltyFilter
    
    def get_queryset(self):
        return CustomerLoyalty.objects.filter(
            organization=self.request.user.organization
        ).select_related('customer', 'current_tier', 'previous_tier').order_by('-ytd_spend')
    
    @action(detail=False, methods=['get'])
    def tier_distribution(self, request):
        """Get distribution of customers across tiers"""
        distribution = self.get_queryset().values(
            'current_tier__name',
            'current_tier__tier_level'
        ).annotate(
            customer_count=Count('id')
        ).order_by('current_tier__tier_level')
        
        return Response({
            'tier_distribution': list(distribution),
            'total_customers': self.get_queryset().count()
        })


class RewardsSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for rewards settings"""
    
    serializer_class = RewardsSettingsSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    
    def get_queryset(self):
        return RewardsSettings.objects.filter(
            organization=self.request.user.organization
        )
    
    def get_object(self):
        """Get or create settings for organization"""
        settings, created = RewardsSettings.objects.get_or_create(
            organization=self.request.user.organization
        )
        return settings
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current settings"""
        settings = self.get_object()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)


class RewardsAnalyticsViewSet(viewsets.ViewSet):
    """ViewSet for rewards analytics"""
    
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get rewards analytics dashboard data"""
        organization = request.user.organization
        days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now() - timedelta(days=days)
        
        # SuperCash metrics
        supercash_metrics = SuperCashTransaction.objects.filter(
            organization=organization,
            created_at__gte=start_date,
            status='completed'
        ).aggregate(
            total_issued=Sum('amount', filter=Q(transaction_type__startswith='earn_')),
            total_redeemed=Sum('amount', filter=Q(transaction_type__startswith='spend_')),
            total_expired=Sum('amount', filter=Q(transaction_type='expire'))
        )
        
        # Outstanding balance
        outstanding_balance = SuperCashWallet.objects.filter(
            organization=organization
        ).aggregate(
            total=Sum('available_balance')
        )['total'] or Decimal('0.00')
        
        # Wallet metrics
        wallet_metrics = SuperCashWallet.objects.filter(
            organization=organization
        ).aggregate(
            active_wallets=Count('id', filter=Q(is_active=True, available_balance__gt=0)),
            avg_balance=Avg('available_balance')
        )
        
        # Transaction count
        transaction_count = SuperCashTransaction.objects.filter(
            organization=organization,
            created_at__gte=start_date
        ).count()
        
        # Referral metrics
        referral_transactions = SuperCashTransaction.objects.filter(
            organization=organization,
            transaction_type='earn_referral',
            created_at__gte=start_date
        )
        
        referral_signups = referral_transactions.count()
        
        # Tier distribution
        tier_distribution = CustomerLoyalty.objects.filter(
            organization=organization
        ).values(
            'current_tier__name'
        ).annotate(
            count=Count('id')
        )
        
        tier_dist_dict = {item['current_tier__name'] or 'No Tier': item['count'] for item in tier_distribution}
        
        # Campaign performance
        campaign_performance = RewardCampaign.objects.filter(
            organization=organization,
            status='active'
        ).values(
            'name', 'campaign_type', 'current_uses', 'spent_amount'
        )
        
        # Redemption methods
        redemption_methods = SuperCashRedemption.objects.filter(
            organization=organization,
            initiated_at__gte=start_date,
            status='completed'
        ).values(
            'redemption_type'
        ).annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        )
        
        redemption_dict = {item['redemption_type']: {
            'count': item['count'],
            'amount': item['total_amount']
        } for item in redemption_methods}
        
        # Monthly trends (last 12 months)
        monthly_trends = []
        for i in range(12):
            month_start = timezone.now().replace(day=1) - timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)
            
            month_data = SuperCashTransaction.objects.filter(
                organization=organization,
                created_at__gte=month_start,
                created_at__lt=month_end,
                status='completed'
            ).aggregate(
                earned=Sum('amount', filter=Q(transaction_type__startswith='earn_')),
                spent=Sum('amount', filter=Q(transaction_type__startswith='spend_'))
            )
            
            monthly_trends.append({
                'month': month_start.strftime('%Y-%m'),
                'earned': month_data['earned'] or Decimal('0.00'),
                'spent': abs(month_data['spent']) if month_data['spent'] else Decimal('0.00')
            })
        
        analytics_data = {
            'total_supercash_issued': supercash_metrics['total_issued'] or Decimal('0.00'),
            'total_supercash_redeemed': abs(supercash_metrics['total_redeemed']) if supercash_metrics['total_redeemed'] else Decimal('0.00'),
            'total_supercash_outstanding': outstanding_balance,
            'total_supercash_expired': abs(supercash_metrics['total_expired']) if supercash_metrics['total_expired'] else Decimal('0.00'),
            'active_wallets': wallet_metrics['active_wallets'] or 0,
            'total_transactions': transaction_count,
            'avg_wallet_balance': wallet_metrics['avg_balance'] or Decimal('0.00'),
            'referral_signups': referral_signups,
            'referral_conversion_rate': Decimal('85.5'),  # Mock data
            'tier_distribution': tier_dist_dict,
            'campaign_performance': list(campaign_performance),
            'redemption_methods': redemption_dict,
            'monthly_trends': monthly_trends[::-1]  # Reverse to show oldest first
        }
        
        serializer = RewardsAnalyticsSerializer(analytics_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiry_report(self, request):
        """Get SuperCash expiry report"""
        organization = request.user.organization
        
        # Next 30 days expiry
        upcoming_expiry = SuperCashTransaction.objects.filter(
            organization=organization,
            expires_at__isnull=False,
            expires_at__gte=timezone.now(),
            expires_at__lte=timezone.now() + timedelta(days=30),
            status='completed',
            transaction_type__startswith='earn_'
        ).values(
            'expires_at__date'
        ).annotate(
            expiring_amount=Sum('amount'),
            customers_count=Count('wallet__customer', distinct=True)
        ).order_by('expires_at__date')
        
        return Response({
            'upcoming_expiry': list(upcoming_expiry),
            'total_expiring': sum(item['expiring_amount'] for item in upcoming_expiry),
            'customers_affected': sum(item['customers_count'] for item in upcoming_expiry)
        })