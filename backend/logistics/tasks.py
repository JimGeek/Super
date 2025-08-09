from celery import shared_task
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from datetime import timedelta
from decimal import Decimal
import logging

from .models import (
    Delivery, DeliveryPartner, DeliveryAnalytics, 
    RouteOptimizationJob, DeliveryRoute
)
from .services import (
    DeliveryAssignmentService, RouteOptimizationService,
    DeliveryTrackingService
)
from accounts.models import Organization

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def auto_assign_delivery(self, delivery_id):
    """Auto-assign a single delivery to the best available partner"""
    
    try:
        delivery = Delivery.objects.get(id=delivery_id)
        
        if delivery.status != 'pending':
            logger.info(f"Delivery {delivery_id} is no longer pending, skipping assignment")
            return f"Delivery {delivery_id} already processed"
        
        assignment_service = DeliveryAssignmentService()
        
        if assignment_service.assign_delivery(delivery):
            logger.info(f"Successfully assigned delivery {delivery_id} to partner {delivery.delivery_partner.id}")
            return f"Assigned delivery {delivery_id} to {delivery.delivery_partner.name}"
        else:
            logger.warning(f"No available partners for delivery {delivery_id}")
            return f"No available partners for delivery {delivery_id}"
            
    except Delivery.DoesNotExist:
        logger.error(f"Delivery {delivery_id} not found")
        raise self.retry(countdown=300)  # Retry after 5 minutes
    
    except Exception as exc:
        logger.error(f"Error assigning delivery {delivery_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)


@shared_task
def batch_auto_assign_deliveries():
    """Auto-assign all pending deliveries"""
    
    assignment_service = DeliveryAssignmentService()
    
    # Get pending deliveries older than 5 minutes
    cutoff_time = timezone.now() - timedelta(minutes=5)
    pending_deliveries = Delivery.objects.filter(
        status='pending',
        created_at__lt=cutoff_time
    ).select_related('organization')
    
    results = {
        'total_pending': 0,
        'assigned': 0,
        'failed': 0,
        'errors': []
    }
    
    for delivery in pending_deliveries:
        results['total_pending'] += 1
        
        try:
            if assignment_service.assign_delivery(delivery):
                results['assigned'] += 1
                logger.info(f"Auto-assigned delivery {delivery.id}")
            else:
                results['failed'] += 1
                logger.warning(f"Failed to assign delivery {delivery.id} - no available partners")
                
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"Delivery {delivery.id}: {str(e)}")
            logger.error(f"Error auto-assigning delivery {delivery.id}: {str(e)}")
    
    logger.info(f"Batch assignment completed: {results}")
    return results


@shared_task(bind=True, max_retries=3)
def optimize_partner_routes(self, organization_id, partner_ids=None, priority=0):
    """Optimize routes for delivery partners"""
    
    try:
        organization = Organization.objects.get(id=organization_id)
        optimization_service = RouteOptimizationService()
        
        if partner_ids:
            partners = DeliveryPartner.objects.filter(
                id__in=partner_ids,
                organization=organization,
                status='active'
            )
        else:
            partners = DeliveryPartner.objects.filter(
                organization=organization,
                status='active'
            )
        
        optimized_routes = []
        
        for partner in partners:
            try:
                # Get pending deliveries for this partner
                pending_deliveries = Delivery.objects.filter(
                    organization=organization,
                    delivery_partner=partner,
                    status='assigned'
                ).order_by('estimated_delivery_time')
                
                if pending_deliveries.count() >= 2:  # Only optimize if multiple deliveries
                    route = optimization_service._optimize_single_partner_route(
                        partner, 
                        list(pending_deliveries)
                    )
                    
                    if route:
                        optimized_routes.append({
                            'partner_id': str(partner.id),
                            'partner_name': partner.name,
                            'route_id': str(route.id),
                            'deliveries_count': pending_deliveries.count(),
                            'total_distance': route.total_distance,
                            'estimated_duration': route.estimated_duration
                        })
                        
                        logger.info(f"Optimized route for partner {partner.name}: {route.total_distance}km")
                
            except Exception as e:
                logger.error(f"Failed to optimize route for partner {partner.id}: {str(e)}")
                continue
        
        result = {
            'organization_id': str(organization_id),
            'partners_processed': len(partners),
            'routes_optimized': len(optimized_routes),
            'routes': optimized_routes,
            'completed_at': timezone.now().isoformat()
        }
        
        logger.info(f"Route optimization completed for organization {organization_id}: {len(optimized_routes)} routes optimized")
        return result
        
    except Organization.DoesNotExist:
        logger.error(f"Organization {organization_id} not found")
        raise self.retry(countdown=300)
    
    except Exception as exc:
        logger.error(f"Error optimizing routes for organization {organization_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=600)


@shared_task
def update_delivery_analytics():
    """Update delivery analytics for all organizations"""
    
    from django.db import models
    
    # Update analytics for each organization
    organizations = Organization.objects.all()
    updated_count = 0
    
    for organization in organizations:
        try:
            # Update daily analytics
            today = timezone.now().date()
            period_start = timezone.datetime.combine(
                today, 
                timezone.datetime.min.time()
            ).replace(tzinfo=timezone.get_current_timezone())
            
            period_end = period_start + timedelta(days=1) - timedelta(microseconds=1)
            
            # Get deliveries for today
            today_deliveries = Delivery.objects.filter(
                organization=organization,
                created_at__date=today
            )
            
            if not today_deliveries.exists():
                continue
            
            # Calculate metrics
            metrics = today_deliveries.aggregate(
                total=Count('id'),
                successful=Count('id', filter=Q(status='delivered')),
                failed=Count('id', filter=Q(status='failed')),
                cancelled=Count('id', filter=Q(status='cancelled')),
                avg_delivery_time=Avg(
                    models.F('actual_delivery_time') - models.F('actual_pickup_time'),
                    filter=Q(
                        actual_delivery_time__isnull=False,
                        actual_pickup_time__isnull=False
                    )
                ),
                avg_distance=Avg('distance', filter=Q(distance__isnull=False)),
                total_distance=Sum('distance', filter=Q(distance__isnull=False)),
                total_fees=Sum('delivery_fee', filter=Q(delivery_fee__isnull=False)),
                total_commissions=Sum('partner_commission', filter=Q(partner_commission__isnull=False)),
                avg_rating=Avg('customer_rating', filter=Q(customer_rating__isnull=False)),
                total_ratings=Count('customer_rating', filter=Q(customer_rating__isnull=False))
            )
            
            # Convert timedelta to minutes for avg_delivery_time
            avg_delivery_minutes = 0.0
            if metrics['avg_delivery_time']:
                avg_delivery_minutes = metrics['avg_delivery_time'].total_seconds() / 60
            
            # Update or create analytics record
            analytics, created = DeliveryAnalytics.objects.update_or_create(
                organization=organization,
                delivery_partner=None,
                delivery_zone=None,
                period_type='daily',
                period_start=period_start,
                defaults={
                    'period_end': period_end,
                    'total_deliveries': metrics['total'] or 0,
                    'successful_deliveries': metrics['successful'] or 0,
                    'failed_deliveries': metrics['failed'] or 0,
                    'cancelled_deliveries': metrics['cancelled'] or 0,
                    'average_delivery_time': avg_delivery_minutes,
                    'average_distance': float(metrics['avg_distance'] or 0.0),
                    'total_distance': float(metrics['total_distance'] or 0.0),
                    'total_delivery_fees': metrics['total_fees'] or Decimal('0.00'),
                    'total_commissions': metrics['total_commissions'] or Decimal('0.00'),
                    'average_rating': float(metrics['avg_rating'] or 5.0),
                    'total_ratings': metrics['total_ratings'] or 0,
                }
            )
            
            updated_count += 1
            
            # Also update partner-specific analytics
            active_partners = DeliveryPartner.objects.filter(
                organization=organization,
                status='active'
            )
            
            for partner in active_partners:
                partner_deliveries = today_deliveries.filter(delivery_partner=partner)
                
                if not partner_deliveries.exists():
                    continue
                
                partner_metrics = partner_deliveries.aggregate(
                    total=Count('id'),
                    successful=Count('id', filter=Q(status='delivered')),
                    failed=Count('id', filter=Q(status='failed')),
                    cancelled=Count('id', filter=Q(status='cancelled')),
                    avg_delivery_time=Avg(
                        models.F('actual_delivery_time') - models.F('actual_pickup_time'),
                        filter=Q(
                            actual_delivery_time__isnull=False,
                            actual_pickup_time__isnull=False
                        )
                    ),
                    avg_distance=Avg('distance', filter=Q(distance__isnull=False)),
                    total_distance=Sum('distance', filter=Q(distance__isnull=False)),
                    total_fees=Sum('delivery_fee', filter=Q(delivery_fee__isnull=False)),
                    total_commissions=Sum('partner_commission', filter=Q(partner_commission__isnull=False)),
                    avg_rating=Avg('customer_rating', filter=Q(customer_rating__isnull=False)),
                    total_ratings=Count('customer_rating', filter=Q(customer_rating__isnull=False))
                )
                
                partner_avg_delivery_minutes = 0.0
                if partner_metrics['avg_delivery_time']:
                    partner_avg_delivery_minutes = partner_metrics['avg_delivery_time'].total_seconds() / 60
                
                DeliveryAnalytics.objects.update_or_create(
                    organization=organization,
                    delivery_partner=partner,
                    delivery_zone=None,
                    period_type='daily',
                    period_start=period_start,
                    defaults={
                        'period_end': period_end,
                        'total_deliveries': partner_metrics['total'] or 0,
                        'successful_deliveries': partner_metrics['successful'] or 0,
                        'failed_deliveries': partner_metrics['failed'] or 0,
                        'cancelled_deliveries': partner_metrics['cancelled'] or 0,
                        'average_delivery_time': partner_avg_delivery_minutes,
                        'average_distance': float(partner_metrics['avg_distance'] or 0.0),
                        'total_distance': float(partner_metrics['total_distance'] or 0.0),
                        'total_delivery_fees': partner_metrics['total_fees'] or Decimal('0.00'),
                        'total_commissions': partner_metrics['total_commissions'] or Decimal('0.00'),
                        'average_rating': float(partner_metrics['avg_rating'] or 5.0),
                        'total_ratings': partner_metrics['total_ratings'] or 0,
                    }
                )
            
            logger.info(f"Updated analytics for organization {organization.name}")
            
        except Exception as e:
            logger.error(f"Error updating analytics for organization {organization.id}: {str(e)}")
            continue
    
    logger.info(f"Updated analytics for {updated_count} organizations")
    return f"Updated analytics for {updated_count} organizations"


@shared_task
def cleanup_old_tracking_data():
    """Clean up old tracking data to prevent database bloat"""
    
    from .models import DeliveryTracking
    
    # Delete tracking records older than 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    
    deleted_count, _ = DeliveryTracking.objects.filter(
        recorded_at__lt=cutoff_date
    ).delete()
    
    logger.info(f"Cleaned up {deleted_count} old tracking records")
    return f"Cleaned up {deleted_count} tracking records"


@shared_task
def process_failed_deliveries():
    """Process failed deliveries and trigger retry logic"""
    
    # Get deliveries that failed within last 4 hours and have retry attempts left
    cutoff_time = timezone.now() - timedelta(hours=4)
    
    failed_deliveries = Delivery.objects.filter(
        status='failed',
        updated_at__gte=cutoff_time,
        retry_count__lt=3  # Max 3 retry attempts
    ).select_related('delivery_partner', 'organization')
    
    retry_results = {
        'processed': 0,
        'retried': 0,
        'abandoned': 0,
        'errors': []
    }
    
    assignment_service = DeliveryAssignmentService()
    
    for delivery in failed_deliveries:
        retry_results['processed'] += 1
        
        try:
            # Reset delivery status and try to reassign
            delivery.status = 'pending'
            delivery.delivery_partner = None
            delivery.assigned_at = None
            delivery.retry_count += 1
            delivery.save()
            
            # Try to assign to a different partner
            if assignment_service.assign_delivery(delivery):
                retry_results['retried'] += 1
                logger.info(f"Retried delivery {delivery.id} - attempt {delivery.retry_count}")
            else:
                # If no partners available, mark as abandoned
                delivery.status = 'cancelled'
                delivery.failure_reason = f"No available partners after {delivery.retry_count} attempts"
                delivery.save()
                retry_results['abandoned'] += 1
                logger.warning(f"Abandoned delivery {delivery.id} after {delivery.retry_count} attempts")
                
        except Exception as e:
            retry_results['errors'].append(f"Delivery {delivery.id}: {str(e)}")
            logger.error(f"Error processing failed delivery {delivery.id}: {str(e)}")
    
    logger.info(f"Processed failed deliveries: {retry_results}")
    return retry_results


@shared_task
def send_delivery_notifications():
    """Send various delivery notifications"""
    
    # This would integrate with notification services
    # For now, we'll just log what notifications should be sent
    
    now = timezone.now()
    
    # 1. Notify customers about deliveries running late
    overdue_deliveries = Delivery.objects.filter(
        status__in=['assigned', 'accepted', 'picked_up', 'in_transit'],
        estimated_delivery_time__lt=now - timedelta(minutes=30)
    ).select_related('order__customer')
    
    late_notifications = 0
    for delivery in overdue_deliveries:
        # Send SMS/email notification about delay
        logger.info(f"Should notify customer about late delivery {delivery.id}")
        late_notifications += 1
    
    # 2. Notify partners about new assignments (older than 5 minutes, not accepted)
    unaccepted_deliveries = Delivery.objects.filter(
        status='assigned',
        assigned_at__lt=now - timedelta(minutes=5)
    ).select_related('delivery_partner')
    
    assignment_reminders = 0
    for delivery in unaccepted_deliveries:
        # Send push notification to partner
        logger.info(f"Should remind partner {delivery.delivery_partner.id} about delivery {delivery.id}")
        assignment_reminders += 1
    
    # 3. Daily summary for admins
    if now.hour == 18:  # 6 PM summary
        organizations = Organization.objects.all()
        for org in organizations:
            today_stats = Delivery.objects.filter(
                organization=org,
                created_at__date=now.date()
            ).aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='delivered')),
                pending=Count('id', filter=Q(status__in=['pending', 'assigned', 'accepted', 'picked_up', 'in_transit']))
            )
            
            logger.info(f"Daily summary for {org.name}: {today_stats}")
    
    return {
        'late_notifications': late_notifications,
        'assignment_reminders': assignment_reminders
    }


@shared_task
def update_partner_performance_metrics():
    """Update performance metrics for all delivery partners"""
    
    partners = DeliveryPartner.objects.filter(status='active')
    updated_count = 0
    
    for partner in partners:
        try:
            # Get recent deliveries (last 30 days)
            recent_deliveries = partner.deliveries.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            )
            
            if not recent_deliveries.exists():
                continue
            
            # Calculate metrics
            total_recent = recent_deliveries.count()
            successful_recent = recent_deliveries.filter(status='delivered').count()
            
            # Calculate average delivery time for completed deliveries
            completed_deliveries = recent_deliveries.filter(
                status='delivered',
                actual_pickup_time__isnull=False,
                actual_delivery_time__isnull=False
            )
            
            if completed_deliveries.exists():
                total_time = sum([
                    (delivery.actual_delivery_time - delivery.actual_pickup_time).total_seconds()
                    for delivery in completed_deliveries
                ])
                avg_time_minutes = (total_time / completed_deliveries.count()) / 60
            else:
                avg_time_minutes = partner.average_delivery_time
            
            # Calculate new rating based on recent customer ratings
            recent_ratings = recent_deliveries.filter(
                customer_rating__isnull=False
            ).aggregate(avg_rating=Avg('customer_rating'))
            
            new_rating = recent_ratings['avg_rating'] or partner.rating
            
            # Update partner metrics
            partner.average_delivery_time = avg_time_minutes
            partner.rating = new_rating
            partner.save(update_fields=['average_delivery_time', 'rating'])
            
            updated_count += 1
            logger.info(f"Updated metrics for partner {partner.name}")
            
        except Exception as e:
            logger.error(f"Error updating metrics for partner {partner.id}: {str(e)}")
            continue
    
    logger.info(f"Updated performance metrics for {updated_count} partners")
    return f"Updated metrics for {updated_count} partners"


# Periodic task scheduling (to be added to celery beat schedule)
@shared_task
def schedule_periodic_tasks():
    """Schedule all periodic logistics tasks"""
    
    # This would be called by celery beat to schedule other tasks
    
    # Auto-assign deliveries every 5 minutes
    batch_auto_assign_deliveries.delay()
    
    # Update analytics every hour
    if timezone.now().minute == 0:
        update_delivery_analytics.delay()
    
    # Route optimization every 30 minutes during business hours
    current_hour = timezone.now().hour
    if 9 <= current_hour <= 21 and timezone.now().minute % 30 == 0:
        organizations = Organization.objects.all()
        for org in organizations:
            optimize_partner_routes.delay(str(org.id))
    
    # Cleanup and maintenance tasks
    if timezone.now().hour == 2:  # 2 AM daily
        cleanup_old_tracking_data.delay()
        process_failed_deliveries.delay()
        update_partner_performance_metrics.delay()
    
    # Notification tasks every 15 minutes
    if timezone.now().minute % 15 == 0:
        send_delivery_notifications.delay()
    
    return "Scheduled periodic tasks"