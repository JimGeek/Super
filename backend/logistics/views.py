from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    DeliveryZone, DeliveryPartner, DeliveryRoute, Delivery,
    DeliveryTracking, RouteOptimizationJob, DeliveryAnalytics
)
from .serializers import (
    DeliveryZoneSerializer, DeliveryPartnerSerializer, DeliveryRouteSerializer,
    DeliverySerializer, DeliveryTrackingSerializer, RouteOptimizationJobSerializer,
    DeliveryAnalyticsSerializer, DeliveryPartnerLocationUpdateSerializer,
    DeliveryStatusUpdateSerializer, RouteOptimizationRequestSerializer,
    DeliveryAssignmentRequestSerializer, DeliveryETARequestSerializer,
    DeliveryETAResponseSerializer, DeliveryStatsSerializer
)
from .services import (
    OSRMService, DeliveryAssignmentService, RouteOptimizationService,
    DeliveryTrackingService, process_route_optimization_job
)
from .filters import DeliveryFilter, DeliveryPartnerFilter
from accounts.permissions import IsOrganizationMember


class DeliveryZoneViewSet(viewsets.ModelViewSet):
    """ViewSet for managing delivery zones"""
    
    serializer_class = DeliveryZoneSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    def get_queryset(self):
        return DeliveryZone.objects.filter(
            organization=self.request.user.organization
        ).order_by('name')
    
    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Toggle zone active status"""
        zone = self.get_object()
        zone.is_active = not zone.is_active
        zone.save()
        
        return Response({
            'id': zone.id,
            'is_active': zone.is_active,
            'message': f"Zone {'activated' if zone.is_active else 'deactivated'} successfully"
        })


class DeliveryPartnerViewSet(viewsets.ModelViewSet):
    """ViewSet for managing delivery partners"""
    
    serializer_class = DeliveryPartnerSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DeliveryPartnerFilter
    
    def get_queryset(self):
        return DeliveryPartner.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related('delivery_zones').order_by('name')
    
    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
    
    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        """Update partner's current location"""
        partner = self.get_object()
        serializer = DeliveryPartnerLocationUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            tracking_service = DeliveryTrackingService()
            tracking_records = tracking_service.update_partner_location(
                partner=partner,
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                accuracy=serializer.validated_data.get('accuracy', 0.0),
                speed=serializer.validated_data.get('speed', 0.0),
                bearing=serializer.validated_data.get('bearing'),
            )
            
            return Response({
                'message': 'Location updated successfully',
                'tracking_records_created': len(tracking_records),
                'current_location': {
                    'latitude': partner.current_location.y,
                    'longitude': partner.current_location.x
                },
                'last_update': partner.last_location_update
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def deliveries(self, request, pk=None):
        """Get partner's deliveries"""
        partner = self.get_object()
        status_filter = request.query_params.get('status')
        
        deliveries = partner.deliveries.all().select_related(
            'order', 'delivery_zone'
        ).order_by('-created_at')
        
        if status_filter:
            deliveries = deliveries.filter(status=status_filter)
        
        # Pagination
        page = self.paginate_queryset(deliveries)
        if page is not None:
            serializer = DeliverySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DeliverySerializer(deliveries, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get partner statistics"""
        partner = self.get_object()
        
        # Get date range
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        deliveries = partner.deliveries.filter(created_at__gte=start_date)
        
        stats = deliveries.aggregate(
            total_deliveries=Count('id'),
            successful_deliveries=Count('id', filter=Q(status='delivered')),
            failed_deliveries=Count('id', filter=Q(status='failed')),
            cancelled_deliveries=Count('id', filter=Q(status='cancelled')),
            total_distance=Sum('distance'),
            total_earnings=Sum('partner_commission'),
            avg_rating=Avg('customer_rating', filter=Q(customer_rating__isnull=False))
        )
        
        success_rate = 0
        if stats['total_deliveries'] > 0:
            success_rate = (stats['successful_deliveries'] / stats['total_deliveries']) * 100
        
        return Response({
            'partner_id': partner.id,
            'period_days': days,
            'total_deliveries': stats['total_deliveries'] or 0,
            'successful_deliveries': stats['successful_deliveries'] or 0,
            'failed_deliveries': stats['failed_deliveries'] or 0,
            'cancelled_deliveries': stats['cancelled_deliveries'] or 0,
            'success_rate': round(success_rate, 2),
            'total_distance': float(stats['total_distance'] or 0),
            'total_earnings': stats['total_earnings'] or Decimal('0.00'),
            'average_rating': float(stats['avg_rating'] or 5.0),
            'current_status': partner.status,
            'is_available': partner.is_available
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve delivery partner"""
        partner = self.get_object()
        
        if partner.status != 'pending':
            return Response(
                {'error': 'Only pending partners can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        partner.status = 'active'
        partner.save()
        
        return Response({'message': 'Partner approved successfully'})
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend delivery partner"""
        partner = self.get_object()
        reason = request.data.get('reason', '')
        
        partner.status = 'suspended'
        partner.save()
        
        return Response({
            'message': 'Partner suspended successfully',
            'reason': reason
        })


class DeliveryRouteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing delivery routes"""
    
    serializer_class = DeliveryRouteSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'delivery_partner']
    
    def get_queryset(self):
        return DeliveryRoute.objects.filter(
            organization=self.request.user.organization
        ).select_related('delivery_partner').order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start route execution"""
        route = self.get_object()
        
        if route.status != 'planned':
            return Response(
                {'error': 'Only planned routes can be started'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        route.status = 'active'
        route.started_at = timezone.now()
        route.save()
        
        return Response({
            'message': 'Route started successfully',
            'started_at': route.started_at
        })
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete route execution"""
        route = self.get_object()
        
        if route.status != 'active':
            return Response(
                {'error': 'Only active routes can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update route
        route.status = 'completed'
        route.completed_at = timezone.now()
        
        # Calculate actual metrics
        if route.started_at:
            duration = (route.completed_at - route.started_at).total_seconds() / 60
            route.actual_duration = int(duration)
        
        route.save()
        
        return Response({
            'message': 'Route completed successfully',
            'completed_at': route.completed_at,
            'actual_duration': route.actual_duration
        })


class DeliveryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing deliveries"""
    
    serializer_class = DeliverySerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DeliveryFilter
    
    def get_queryset(self):
        return Delivery.objects.filter(
            organization=self.request.user.organization
        ).select_related(
            'order', 'delivery_partner', 'delivery_zone'
        ).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Manually assign delivery to partner"""
        delivery = self.get_object()
        serializer = DeliveryAssignmentRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            partner = serializer.validated_data['partner']
            force_assign = serializer.validated_data.get('force_assign', False)
            
            assignment_service = DeliveryAssignmentService()
            
            # Manual assignment logic
            delivery.delivery_partner = partner
            delivery.status = 'assigned'
            delivery.assigned_at = timezone.now()
            
            # Calculate delivery metrics
            distance = assignment_service._calculate_distance(delivery)
            delivery_zone = assignment_service._get_delivery_zone(delivery)
            
            if delivery_zone:
                delivery_fee = delivery_zone.base_delivery_fee + (
                    Decimal(str(distance)) * delivery_zone.per_km_rate
                )
                partner_commission = delivery_fee * (partner.commission_rate / 100)
            else:
                delivery_fee = Decimal('50.00')
                partner_commission = delivery_fee * Decimal('0.15')
            
            delivery.delivery_zone = delivery_zone
            delivery.distance = distance
            delivery.delivery_fee = delivery_fee
            delivery.partner_commission = partner_commission
            
            delivery.save()
            
            return Response({
                'message': 'Delivery assigned successfully',
                'delivery_id': delivery.id,
                'partner_id': partner.id,
                'delivery_fee': delivery_fee,
                'estimated_distance': distance
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update delivery status"""
        delivery = self.get_object()
        serializer = DeliveryStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            notes = serializer.validated_data.get('notes', '')
            proof_images = serializer.validated_data.get('proof_images', [])
            customer_signature = serializer.validated_data.get('customer_signature')
            failure_reason = serializer.validated_data.get('failure_reason')
            otp = serializer.validated_data.get('otp')
            
            # Validate OTP for delivery completion
            if new_status == 'delivered' and delivery.delivery_otp:
                if otp != delivery.delivery_otp:
                    return Response(
                        {'error': 'Invalid OTP provided'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Update delivery
            old_status = delivery.status
            delivery.status = new_status
            
            # Update timestamps
            now = timezone.now()
            if new_status == 'picked_up':
                delivery.actual_pickup_time = now
            elif new_status == 'delivered':
                delivery.actual_delivery_time = now
                
                # Update proof of delivery
                proof_data = {
                    'images': proof_images,
                    'signature': customer_signature,
                    'completed_at': now.isoformat(),
                    'otp_verified': bool(otp)
                }
                delivery.proof_of_delivery = proof_data
            elif new_status == 'failed':
                delivery.failure_reason = failure_reason
                delivery.retry_count += 1
            
            if notes:
                delivery.customer_notes = notes
            
            delivery.save()
            
            # Update partner metrics
            if delivery.delivery_partner and new_status == 'delivered':
                partner = delivery.delivery_partner
                partner.successful_deliveries += 1
                partner.total_earnings += delivery.partner_commission or Decimal('0.00')
                partner.save()
            
            return Response({
                'message': f'Delivery status updated from {old_status} to {new_status}',
                'delivery_id': delivery.id,
                'new_status': new_status,
                'updated_at': now
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def tracking(self, request, pk=None):
        """Get delivery tracking history"""
        delivery = self.get_object()
        
        tracking_data = delivery.tracking_data.all().order_by('-recorded_at')
        
        # Pagination
        page = self.paginate_queryset(tracking_data)
        if page is not None:
            serializer = DeliveryTrackingSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DeliveryTrackingSerializer(tracking_data, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def eta(self, request, pk=None):
        """Get updated ETA for delivery"""
        delivery = self.get_object()
        
        tracking_service = DeliveryTrackingService()
        updated_eta = tracking_service.get_delivery_eta(delivery)
        
        delay_minutes = None
        if updated_eta and delivery.estimated_delivery_time:
            delay = updated_eta - delivery.estimated_delivery_time
            delay_minutes = int(delay.total_seconds() / 60)
        
        partner_location = None
        if delivery.delivery_partner and delivery.delivery_partner.current_location:
            partner_location = {
                'latitude': delivery.delivery_partner.current_location.y,
                'longitude': delivery.delivery_partner.current_location.x,
                'last_update': delivery.delivery_partner.last_location_update
            }
        
        return Response({
            'delivery_id': delivery.id,
            'current_eta': updated_eta,
            'original_eta': delivery.estimated_delivery_time,
            'delay_minutes': delay_minutes,
            'partner_location': partner_location,
            'status': delivery.status
        })
    
    @action(detail=False, methods=['post'])
    def auto_assign(self, request):
        """Auto-assign pending deliveries"""
        assignment_service = DeliveryAssignmentService()
        
        pending_deliveries = Delivery.objects.filter(
            organization=request.user.organization,
            status='pending'
        )
        
        assigned_count = 0
        failed_assignments = []
        
        for delivery in pending_deliveries:
            if assignment_service.assign_delivery(delivery):
                assigned_count += 1
            else:
                failed_assignments.append(str(delivery.id))
        
        return Response({
            'message': f'Auto-assignment completed',
            'assigned_count': assigned_count,
            'total_pending': pending_deliveries.count(),
            'failed_assignments': failed_assignments
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get delivery statistics"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        deliveries = self.get_queryset().filter(created_at__gte=start_date)
        
        stats = deliveries.aggregate(
            total_deliveries=Count('id'),
            pending_deliveries=Count('id', filter=Q(status='pending')),
            active_deliveries=Count('id', filter=Q(status__in=['assigned', 'accepted', 'picked_up', 'in_transit'])),
            completed_deliveries=Count('id', filter=Q(status='delivered')),
            failed_deliveries=Count('id', filter=Q(status='failed')),
            cancelled_deliveries=Count('id', filter=Q(status='cancelled')),
            total_distance=Sum('distance'),
            total_revenue=Sum('delivery_fee'),
            avg_delivery_time=Avg('actual_delivery_time', filter=Q(actual_delivery_time__isnull=False)),
            avg_rating=Avg('customer_rating', filter=Q(customer_rating__isnull=False))
        )
        
        success_rate = 0
        if stats['total_deliveries'] > 0:
            success_rate = (stats['completed_deliveries'] / stats['total_deliveries']) * 100
        
        active_partners = DeliveryPartner.objects.filter(
            organization=request.user.organization,
            status='active'
        ).count()
        
        serializer = DeliveryStatsSerializer({
            'total_deliveries': stats['total_deliveries'] or 0,
            'pending_deliveries': stats['pending_deliveries'] or 0,
            'active_deliveries': stats['active_deliveries'] or 0,
            'completed_deliveries': stats['completed_deliveries'] or 0,
            'failed_deliveries': stats['failed_deliveries'] or 0,
            'cancelled_deliveries': stats['cancelled_deliveries'] or 0,
            'success_rate': round(success_rate, 2),
            'average_delivery_time': float(stats['avg_delivery_time'] or 0),
            'total_distance': float(stats['total_distance'] or 0),
            'total_revenue': stats['total_revenue'] or Decimal('0.00'),
            'active_partners': active_partners,
            'average_rating': float(stats['avg_rating'] or 5.0)
        })
        
        return Response(serializer.data)


class RouteOptimizationJobViewSet(viewsets.ModelViewSet):
    """ViewSet for route optimization jobs"""
    
    serializer_class = RouteOptimizationJobSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'job_type']
    
    def get_queryset(self):
        return RouteOptimizationJob.objects.filter(
            organization=self.request.user.organization
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
    
    @action(detail=False, methods=['post'])
    def optimize_routes(self, request):
        """Create route optimization job"""
        serializer = RouteOptimizationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            partner_ids = serializer.validated_data.get('partner_ids', [])
            priority = serializer.validated_data.get('priority', 0)
            schedule_time = serializer.validated_data.get('schedule_time', timezone.now())
            
            # Create optimization job
            job = RouteOptimizationJob.objects.create(
                organization=request.user.organization,
                job_type='route_optimization',
                priority=priority,
                scheduled_at=schedule_time,
                input_data={
                    'partner_ids': [str(pid) for pid in partner_ids] if partner_ids else [],
                    'optimization_type': 'batch_route_optimization',
                    'requested_by': str(request.user.id),
                    'request_time': timezone.now().isoformat()
                }
            )
            
            # Queue the job for processing
            if schedule_time <= timezone.now():
                process_route_optimization_job.delay(str(job.id))
            
            return Response({
                'job_id': job.id,
                'status': job.status,
                'scheduled_at': job.scheduled_at,
                'message': 'Route optimization job created successfully'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeliveryAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for delivery analytics"""
    
    serializer_class = DeliveryAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['period_type', 'delivery_partner', 'delivery_zone']
    
    def get_queryset(self):
        return DeliveryAnalytics.objects.filter(
            organization=self.request.user.organization
        ).select_related('delivery_partner', 'delivery_zone').order_by('-period_start')
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard analytics summary"""
        period = request.query_params.get('period', 'daily')
        days = int(request.query_params.get('days', 30))
        
        start_date = timezone.now() - timedelta(days=days)
        
        analytics = self.get_queryset().filter(
            period_type=period,
            period_start__gte=start_date
        )
        
        # Aggregate metrics
        summary = analytics.aggregate(
            total_deliveries=Sum('total_deliveries'),
            successful_deliveries=Sum('successful_deliveries'),
            failed_deliveries=Sum('failed_deliveries'),
            cancelled_deliveries=Sum('cancelled_deliveries'),
            total_distance=Sum('total_distance'),
            total_fees=Sum('total_delivery_fees'),
            total_commissions=Sum('total_commissions'),
            avg_delivery_time=Avg('average_delivery_time'),
            avg_rating=Avg('average_rating')
        )
        
        success_rate = 0
        if summary['total_deliveries']:
            success_rate = (summary['successful_deliveries'] / summary['total_deliveries']) * 100
        
        # Get trend data (last 7 periods)
        trend_data = list(analytics.order_by('-period_start')[:7].values(
            'period_start', 'total_deliveries', 'successful_deliveries', 'average_delivery_time'
        ))
        
        return Response({
            'period': period,
            'days': days,
            'summary': {
                'total_deliveries': summary['total_deliveries'] or 0,
                'successful_deliveries': summary['successful_deliveries'] or 0,
                'failed_deliveries': summary['failed_deliveries'] or 0,
                'cancelled_deliveries': summary['cancelled_deliveries'] or 0,
                'success_rate': round(success_rate, 2),
                'total_distance': float(summary['total_distance'] or 0),
                'total_fees': summary['total_fees'] or Decimal('0.00'),
                'total_commissions': summary['total_commissions'] or Decimal('0.00'),
                'average_delivery_time': float(summary['avg_delivery_time'] or 0),
                'average_rating': float(summary['avg_rating'] or 5.0)
            },
            'trend_data': trend_data
        })