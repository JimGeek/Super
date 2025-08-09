import requests
import json
import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from celery import shared_task

from .models import (
    DeliveryZone, DeliveryPartner, DeliveryRoute, Delivery, 
    DeliveryTracking, RouteOptimizationJob, DeliveryAnalytics
)
from orders.models import Order
from accounts.models import Organization


class OSRMService:
    """Service for OSRM route optimization and navigation"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or getattr(settings, 'OSRM_BASE_URL', 'http://router.project-osrm.org')
    
    def get_route(self, coordinates: List[Tuple[float, float]], profile: str = 'driving') -> Dict:
        """Get optimized route from OSRM"""
        if len(coordinates) < 2:
            raise ValueError("At least 2 coordinates required for routing")
        
        # Format coordinates for OSRM (longitude,latitude)
        coord_string = ';'.join([f"{lng},{lat}" for lng, lat in coordinates])
        
        url = f"{self.base_url}/route/v1/{profile}/{coord_string}"
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'steps': True,
            'annotations': True
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"OSRM routing failed: {str(e)}")
    
    def optimize_route(self, coordinates: List[Tuple[float, float]], 
                      roundtrip: bool = True, profile: str = 'driving') -> Dict:
        """Optimize delivery route using OSRM trip optimization"""
        if len(coordinates) < 2:
            raise ValueError("At least 2 coordinates required for optimization")
        
        coord_string = ';'.join([f"{lng},{lat}" for lng, lat in coordinates])
        
        url = f"{self.base_url}/trip/v1/{profile}/{coord_string}"
        params = {
            'roundtrip': str(roundtrip).lower(),
            'source': 'first',
            'destination': 'last' if not roundtrip else 'any',
            'overview': 'full',
            'geometries': 'geojson',
            'steps': True
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"OSRM trip optimization failed: {str(e)}")
    
    def get_distance_matrix(self, coordinates: List[Tuple[float, float]], 
                           profile: str = 'driving') -> Dict:
        """Get distance matrix between all coordinates"""
        coord_string = ';'.join([f"{lng},{lat}" for lng, lat in coordinates])
        
        url = f"{self.base_url}/table/v1/{profile}/{coord_string}"
        params = {
            'annotations': 'duration,distance'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"OSRM distance matrix failed: {str(e)}")


class DeliveryAssignmentService:
    """Service for intelligent delivery assignment"""
    
    def __init__(self):
        self.osrm = OSRMService()
    
    def find_best_partner(self, delivery: Delivery) -> Optional[DeliveryPartner]:
        """Find the best available delivery partner for a delivery"""
        
        # Get available partners in the delivery zone
        available_partners = DeliveryPartner.objects.filter(
            organization=delivery.organization,
            status='active',
            delivery_zones__boundary__contains=Point(
                delivery.pickup_address['coordinates'][0],
                delivery.pickup_address['coordinates'][1]
            )
        ).filter(
            # Partner must be recently active
            last_location_update__gte=timezone.now() - timedelta(minutes=10)
        ).exclude(
            # Exclude partners who are at capacity
            deliveries__status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
        ).annotate(
            current_deliveries=models.Count('deliveries', filter=models.Q(
                deliveries__status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
            ))
        ).filter(
            current_deliveries__lt=models.F('max_capacity')
        )
        
        if not available_partners.exists():
            return None
        
        # Calculate scores for each partner
        partner_scores = []
        pickup_point = Point(
            delivery.pickup_address['coordinates'][0],
            delivery.pickup_address['coordinates'][1]
        )
        
        for partner in available_partners:
            if not partner.current_location:
                continue
            
            # Distance score (closer is better)
            distance = partner.current_location.distance(pickup_point) * 111  # Convert to km
            distance_score = max(0, 10 - distance)  # 0-10 scale
            
            # Rating score
            rating_score = partner.rating * 2  # 0-10 scale
            
            # Success rate score
            success_score = partner.success_rate / 10  # 0-10 scale
            
            # Load score (less loaded is better)
            load_score = 10 - (partner.current_deliveries / partner.max_capacity * 10)
            
            # Vehicle type preference score
            vehicle_score = self._get_vehicle_score(partner.vehicle_type, delivery)
            
            # Weighted total score
            total_score = (
                distance_score * 0.3 +
                rating_score * 0.25 +
                success_score * 0.2 +
                load_score * 0.15 +
                vehicle_score * 0.1
            )
            
            partner_scores.append((partner, total_score))
        
        if not partner_scores:
            return None
        
        # Return partner with highest score
        partner_scores.sort(key=lambda x: x[1], reverse=True)
        return partner_scores[0][0]
    
    def _get_vehicle_score(self, vehicle_type: str, delivery: Delivery) -> float:
        """Get vehicle suitability score for delivery"""
        total_weight = sum(item.get('weight', 0) for item in delivery.order.items)
        total_items = len(delivery.order.items)
        
        if vehicle_type == 'bicycle':
            if total_weight <= 5 and total_items <= 3:
                return 10
            elif total_weight <= 10 and total_items <= 5:
                return 7
            else:
                return 3
        elif vehicle_type == 'motorbike':
            if total_weight <= 25:
                return 10
            else:
                return 5
        elif vehicle_type == 'car':
            return 8  # Good for most deliveries
        elif vehicle_type == 'van':
            if total_weight > 25 or total_items > 10:
                return 10
            else:
                return 6
        
        return 5
    
    def assign_delivery(self, delivery: Delivery) -> bool:
        """Assign delivery to best available partner"""
        partner = self.find_best_partner(delivery)
        
        if not partner:
            return False
        
        # Calculate delivery fee and commission
        distance = self._calculate_distance(delivery)
        delivery_zone = self._get_delivery_zone(delivery)
        
        if delivery_zone:
            delivery_fee = delivery_zone.base_delivery_fee + (
                Decimal(str(distance)) * delivery_zone.per_km_rate
            )
            partner_commission = delivery_fee * (partner.commission_rate / 100)
        else:
            delivery_fee = Decimal('50.00')  # Default fee
            partner_commission = delivery_fee * Decimal('0.15')
        
        # Update delivery
        delivery.delivery_partner = partner
        delivery.delivery_zone = delivery_zone
        delivery.distance = distance
        delivery.delivery_fee = delivery_fee
        delivery.partner_commission = partner_commission
        delivery.status = 'assigned'
        delivery.assigned_at = timezone.now()
        
        # Set estimated times
        pickup_time = timezone.now() + timedelta(minutes=15)  # 15 min to reach pickup
        delivery_time = pickup_time + timedelta(minutes=30)  # 30 min for delivery
        
        delivery.estimated_pickup_time = pickup_time
        delivery.estimated_delivery_time = delivery_time
        
        delivery.save()
        
        # Send notification to partner (implement separately)
        # self.notification_service.send_delivery_assignment(partner, delivery)
        
        return True
    
    def _calculate_distance(self, delivery: Delivery) -> float:
        """Calculate delivery distance using OSRM"""
        try:
            pickup_coords = delivery.pickup_address['coordinates']
            delivery_coords = delivery.delivery_address['coordinates']
            
            coordinates = [(pickup_coords[0], pickup_coords[1]), 
                          (delivery_coords[0], delivery_coords[1])]
            
            route_data = self.osrm.get_route(coordinates)
            
            if route_data['code'] == 'Ok' and route_data['routes']:
                # Distance in meters, convert to km
                return route_data['routes'][0]['distance'] / 1000
            
        except Exception:
            pass
        
        # Fallback to straight-line distance
        pickup_point = Point(delivery.pickup_address['coordinates'])
        delivery_point = Point(delivery.delivery_address['coordinates'])
        return pickup_point.distance(delivery_point) * 111  # Convert to km
    
    def _get_delivery_zone(self, delivery: Delivery) -> Optional[DeliveryZone]:
        """Get delivery zone for the pickup location"""
        pickup_point = Point(
            delivery.pickup_address['coordinates'][0],
            delivery.pickup_address['coordinates'][1]
        )
        
        return DeliveryZone.objects.filter(
            organization=delivery.organization,
            is_active=True,
            boundary__contains=pickup_point
        ).first()


class RouteOptimizationService:
    """Service for batch route optimization"""
    
    def __init__(self):
        self.osrm = OSRMService()
        self.assignment_service = DeliveryAssignmentService()
    
    def optimize_partner_routes(self, organization: Organization, 
                               partner: DeliveryPartner = None) -> List[DeliveryRoute]:
        """Optimize routes for all partners or a specific partner"""
        
        partners_to_optimize = [partner] if partner else DeliveryPartner.objects.filter(
            organization=organization,
            status='active'
        )
        
        optimized_routes = []
        
        for partner in partners_to_optimize:
            # Get assigned but not started deliveries
            pending_deliveries = Delivery.objects.filter(
                organization=organization,
                delivery_partner=partner,
                status='assigned'
            ).order_by('estimated_delivery_time')
            
            if pending_deliveries.count() < 2:
                continue  # No optimization needed for single delivery
            
            route = self._optimize_single_partner_route(partner, pending_deliveries)
            if route:
                optimized_routes.append(route)
        
        return optimized_routes
    
    def _optimize_single_partner_route(self, partner: DeliveryPartner, 
                                     deliveries: List[Delivery]) -> Optional[DeliveryRoute]:
        """Optimize route for a single partner's deliveries"""
        
        if not partner.current_location:
            return None
        
        # Prepare coordinates for optimization
        coordinates = [(partner.current_location.x, partner.current_location.y)]
        delivery_locations = []
        
        for delivery in deliveries:
            # Add pickup location
            pickup_coords = delivery.pickup_address['coordinates']
            coordinates.append((pickup_coords[0], pickup_coords[1]))
            delivery_locations.append(('pickup', delivery.id))
            
            # Add delivery location
            delivery_coords = delivery.delivery_address['coordinates']
            coordinates.append((delivery_coords[0], delivery_coords[1]))
            delivery_locations.append(('delivery', delivery.id))
        
        try:
            # Get optimized route from OSRM
            optimization_result = self.osrm.optimize_route(coordinates, roundtrip=True)
            
            if optimization_result['code'] != 'Ok' or not optimization_result['trips']:
                return None
            
            trip = optimization_result['trips'][0]
            waypoint_indices = [wp['waypoint_index'] for wp in trip['legs']]
            
            # Create optimized waypoints
            optimized_waypoints = []
            for idx in waypoint_indices:
                if idx > 0:  # Skip starting location
                    location_info = delivery_locations[idx - 1]
                    optimized_waypoints.append({
                        'type': location_info[0],
                        'delivery_id': str(location_info[1]),
                        'coordinates': coordinates[idx],
                        'estimated_arrival': None  # Will be calculated
                    })
            
            # Create delivery route
            route = DeliveryRoute.objects.create(
                organization=partner.organization,
                delivery_partner=partner,
                route_name=f"Route {timezone.now().strftime('%Y%m%d_%H%M')}",
                start_location=partner.current_location,
                waypoints=optimized_waypoints,
                osrm_route_data=trip,
                total_distance=trip['distance'] / 1000,  # Convert to km
                estimated_duration=trip['duration'] / 60,  # Convert to minutes
            )
            
            # Update deliveries with route
            for delivery in deliveries:
                delivery.delivery_route = route
                delivery.save()
            
            return route
            
        except Exception as e:
            print(f"Route optimization failed: {str(e)}")
            return None


class DeliveryTrackingService:
    """Service for real-time delivery tracking"""
    
    def update_partner_location(self, partner: DeliveryPartner, 
                               latitude: float, longitude: float,
                               accuracy: float = 0.0, speed: float = 0.0,
                               bearing: float = None) -> DeliveryTracking:
        """Update partner location and create tracking records"""
        
        new_location = Point(longitude, latitude)
        
        # Update partner location
        partner.current_location = new_location
        partner.last_location_update = timezone.now()
        partner.save()
        
        # Create tracking records for active deliveries
        active_deliveries = partner.deliveries.filter(
            status__in=['accepted', 'picked_up', 'in_transit']
        )
        
        tracking_records = []
        
        for delivery in active_deliveries:
            tracking = DeliveryTracking.objects.create(
                delivery=delivery,
                location=new_location,
                accuracy=accuracy,
                speed=speed,
                bearing=bearing,
                status=delivery.status,
                recorded_at=timezone.now()
            )
            tracking_records.append(tracking)
            
            # Update delivery status based on location
            self._update_delivery_status_by_location(delivery, new_location)
        
        return tracking_records
    
    def _update_delivery_status_by_location(self, delivery: Delivery, 
                                          current_location: Point):
        """Auto-update delivery status based on location proximity"""
        
        pickup_point = Point(
            delivery.pickup_address['coordinates'][0],
            delivery.pickup_address['coordinates'][1]
        )
        delivery_point = Point(
            delivery.delivery_address['coordinates'][0],
            delivery.delivery_address['coordinates'][1]
        )
        
        # Distance thresholds in meters
        PICKUP_THRESHOLD = 100  # 100m
        DELIVERY_THRESHOLD = 100  # 100m
        
        pickup_distance = current_location.distance(pickup_point) * 111000  # Convert to meters
        delivery_distance = current_location.distance(delivery_point) * 111000
        
        if delivery.status == 'accepted' and pickup_distance <= PICKUP_THRESHOLD:
            # Near pickup location - suggest pickup
            pass  # Send notification to partner
        
        elif delivery.status == 'picked_up' and delivery_distance <= DELIVERY_THRESHOLD:
            # Near delivery location - suggest completion
            pass  # Send notification to partner
    
    def get_delivery_eta(self, delivery: Delivery) -> Optional[datetime]:
        """Calculate ETA for delivery based on current location and traffic"""
        
        if not delivery.delivery_partner or not delivery.delivery_partner.current_location:
            return delivery.estimated_delivery_time
        
        partner_location = delivery.delivery_partner.current_location
        
        # Determine next destination
        if delivery.status in ['assigned', 'accepted']:
            destination_coords = delivery.pickup_address['coordinates']
        else:
            destination_coords = delivery.delivery_address['coordinates']
        
        try:
            coordinates = [
                (partner_location.x, partner_location.y),
                (destination_coords[0], destination_coords[1])
            ]
            
            route_data = self.osrm.get_route(coordinates)
            
            if route_data['code'] == 'Ok' and route_data['routes']:
                duration_seconds = route_data['routes'][0]['duration']
                return timezone.now() + timedelta(seconds=duration_seconds)
            
        except Exception:
            pass
        
        return delivery.estimated_delivery_time


# Celery tasks for background processing
@shared_task
def process_route_optimization_job(job_id: str):
    """Background task to process route optimization jobs"""
    
    try:
        job = RouteOptimizationJob.objects.get(id=job_id)
        job.status = 'processing'
        job.started_at = timezone.now()
        job.save()
        
        optimization_service = RouteOptimizationService()
        organization = job.organization
        
        # Process the optimization
        input_data = job.input_data
        
        if job.job_type == 'route_optimization':
            partner_id = input_data.get('partner_id')
            partner = DeliveryPartner.objects.get(id=partner_id) if partner_id else None
            
            routes = optimization_service.optimize_partner_routes(organization, partner)
            
            result_data = {
                'optimized_routes': [
                    {
                        'route_id': str(route.id),
                        'partner_id': str(route.delivery_partner.id),
                        'total_distance': route.total_distance,
                        'estimated_duration': route.estimated_duration,
                        'waypoints_count': len(route.waypoints)
                    }
                    for route in routes
                ]
            }
            
            job.result_data = result_data
            job.status = 'completed'
        
        job.completed_at = timezone.now()
        job.execution_time = (job.completed_at - job.started_at).total_seconds()
        job.save()
        
    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = timezone.now()
        job.save()


@shared_task
def auto_assign_pending_deliveries():
    """Background task to auto-assign pending deliveries"""
    
    assignment_service = DeliveryAssignmentService()
    
    # Get pending deliveries (created more than 5 minutes ago)
    pending_deliveries = Delivery.objects.filter(
        status='pending',
        created_at__lt=timezone.now() - timedelta(minutes=5)
    )
    
    assigned_count = 0
    
    for delivery in pending_deliveries:
        if assignment_service.assign_delivery(delivery):
            assigned_count += 1
    
    return f"Auto-assigned {assigned_count} deliveries"


@shared_task
def update_delivery_analytics():
    """Background task to update delivery analytics"""
    
    from django.db.models import Count, Avg, Sum
    
    # Update daily analytics for each organization
    today = timezone.now().date()
    
    organizations = Organization.objects.all()
    
    for org in organizations:
        # Get today's deliveries
        today_deliveries = Delivery.objects.filter(
            organization=org,
            created_at__date=today
        )
        
        if not today_deliveries.exists():
            continue
        
        # Aggregate metrics
        metrics = today_deliveries.aggregate(
            total=Count('id'),
            successful=Count('id', filter=models.Q(status='delivered')),
            failed=Count('id', filter=models.Q(status='failed')),
            cancelled=Count('id', filter=models.Q(status='cancelled')),
            avg_delivery_time=Avg('actual_delivery_time'),
            avg_distance=Avg('distance'),
            total_distance=Sum('distance'),
            total_fees=Sum('delivery_fee'),
            total_commissions=Sum('partner_commission'),
            avg_rating=Avg('customer_rating', filter=models.Q(customer_rating__isnull=False)),
            total_ratings=Count('customer_rating', filter=models.Q(customer_rating__isnull=False))
        )
        
        # Update or create analytics record
        DeliveryAnalytics.objects.update_or_create(
            organization=org,
            period_type='daily',
            period_start=datetime.combine(today, datetime.min.time().replace(tzinfo=timezone.get_current_timezone())),
            period_end=datetime.combine(today, datetime.max.time().replace(tzinfo=timezone.get_current_timezone())),
            defaults={
                'total_deliveries': metrics['total'] or 0,
                'successful_deliveries': metrics['successful'] or 0,
                'failed_deliveries': metrics['failed'] or 0,
                'cancelled_deliveries': metrics['cancelled'] or 0,
                'average_delivery_time': metrics['avg_delivery_time'] or 0.0,
                'average_distance': metrics['avg_distance'] or 0.0,
                'total_distance': metrics['total_distance'] or 0.0,
                'total_delivery_fees': metrics['total_fees'] or Decimal('0.00'),
                'total_commissions': metrics['total_commissions'] or Decimal('0.00'),
                'average_rating': metrics['avg_rating'] or 5.0,
                'total_ratings': metrics['total_ratings'] or 0,
            }
        )