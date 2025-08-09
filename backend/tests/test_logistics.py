"""
Test cases for logistics app
"""

from django.urls import reverse
from django.contrib.gis.geos import Point
from rest_framework import status
from unittest.mock import patch, Mock
from decimal import Decimal
from datetime import datetime, timedelta
import json

from logistics.models import (
    DeliveryZone, DeliveryBatch, DeliveryTask, RouteOptimization,
    DeliveryPartner, DeliveryTracking
)
from logistics.services import LogisticsService, OSRMService, PorterService
from .base import BaseAPITestCase, TestDataFactory, MockExternalServices


class LogisticsServiceTestCase(BaseAPITestCase):
    """Test cases for Logistics Service"""
    
    def setUp(self):
        super().setUp()
        self.service = LogisticsService(self.organization)
        
        # Create test order
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization,
            delivery_address="123 Test Street, Test City, 123456"
        )
        
        # Create delivery zone
        self.delivery_zone = DeliveryZone.objects.create(
            name="Test Zone",
            organization=self.organization,
            zone_type="city",
            coverage_area={
                "type": "Polygon",
                "coordinates": [[[77.0, 28.0], [77.1, 28.0], [77.1, 28.1], [77.0, 28.1], [77.0, 28.0]]]
            },
            base_fee=Decimal('20.00'),
            per_km_rate=Decimal('5.00'),
            is_active=True
        )
    
    @patch('logistics.services.OSRMService.get_route')
    def test_calculate_delivery_fee(self, mock_route):
        """Test delivery fee calculation"""
        mock_route.return_value = {
            "distance": 5.5,  # 5.5 km
            "duration": 1800,  # 30 minutes
            "geometry": "test_geometry"
        }
        
        pickup_location = Point(77.05, 28.05)
        delivery_location = Point(77.08, 28.08)
        
        fee = self.service.calculate_delivery_fee(
            pickup_location, delivery_location, self.delivery_zone
        )
        
        expected_fee = Decimal('20.00') + (Decimal('5.5') * Decimal('5.00'))  # Base + distance
        self.assertEqual(fee, expected_fee)
    
    def test_find_delivery_zone(self):
        """Test finding delivery zone for location"""
        location = Point(77.05, 28.05)  # Within test zone
        
        zone = self.service.find_delivery_zone(location)
        self.assertEqual(zone, self.delivery_zone)
    
    def test_find_delivery_zone_outside_coverage(self):
        """Test location outside delivery coverage"""
        location = Point(78.0, 29.0)  # Outside test zone
        
        zone = self.service.find_delivery_zone(location)
        self.assertIsNone(zone)
    
    @patch('logistics.services.OSRMService.get_route')
    def test_assign_delivery_task(self, mock_route):
        """Test assigning delivery task to rider"""
        mock_route.return_value = {
            "distance": 3.0,
            "duration": 900,
            "geometry": "test_geometry"
        }
        
        # Create delivery task
        task = self.service.create_delivery_task(
            order=self.order,
            pickup_location=Point(77.05, 28.05),
            delivery_location=Point(77.08, 28.08),
            delivery_zone=self.delivery_zone
        )
        
        # Assign to rider
        assigned_task = self.service.assign_task_to_rider(task, self.rider)
        
        self.assertEqual(assigned_task.rider, self.rider)
        self.assertEqual(assigned_task.status, 'assigned')
        self.assertIsNotNone(assigned_task.assigned_at)
    
    def test_batch_optimization(self):
        """Test batch delivery optimization"""
        # Create multiple orders for batching
        orders = []
        for i in range(3):
            order = TestDataFactory.create_order(
                self.customer, self.merchant, self.organization,
                delivery_address=f"Address {i}, Test City"
            )
            orders.append(order)
        
        # Create delivery tasks
        tasks = []
        for order in orders:
            task = DeliveryTask.objects.create(
                order=order,
                organization=self.organization,
                pickup_location=Point(77.05, 28.05),
                delivery_location=Point(77.08 + (0.01 * len(tasks)), 28.08),
                delivery_zone=self.delivery_zone,
                estimated_distance=3.0 + len(tasks),
                estimated_duration=900 + (len(tasks) * 300),
                status='pending'
            )
            tasks.append(task)
        
        # Create batch
        batch = self.service.create_delivery_batch(tasks, self.rider)
        
        self.assertEqual(batch.task_count, 3)
        self.assertEqual(batch.rider, self.rider)
        self.assertEqual(batch.status, 'created')
        
        # Check all tasks are assigned to batch
        for task in tasks:
            task.refresh_from_db()
            self.assertEqual(task.batch, batch)


class OSRMServiceTestCase(BaseAPITestCase):
    """Test cases for OSRM Service"""
    
    def setUp(self):
        super().setUp()
        self.service = OSRMService()
    
    @patch('requests.get')
    def test_get_route_success(self, mock_get):
        """Test successful route calculation"""
        mock_response = Mock()
        mock_response.json.return_value = MockExternalServices.mock_osrm_response()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        start_point = Point(77.05, 28.05)
        end_point = Point(77.08, 28.08)
        
        route = self.service.get_route(start_point, end_point)
        
        self.assertEqual(route['duration'], 1800)
        self.assertEqual(route['distance'], 15000)
        self.assertIn('geometry', route)
    
    @patch('requests.get')
    def test_get_route_failure(self, mock_get):
        """Test route calculation failure"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        start_point = Point(77.05, 28.05)
        end_point = Point(77.08, 28.08)
        
        route = self.service.get_route(start_point, end_point)
        self.assertIsNone(route)
    
    @patch('requests.get')
    def test_get_multiple_routes(self, mock_get):
        """Test getting routes to multiple destinations"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "routes": [
                {"duration": 900, "distance": 5000, "geometry": "route1"},
                {"duration": 1200, "distance": 7000, "geometry": "route2"},
                {"duration": 1500, "distance": 9000, "geometry": "route3"}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        start_point = Point(77.05, 28.05)
        destinations = [
            Point(77.08, 28.08),
            Point(77.09, 28.09),
            Point(77.10, 28.10)
        ]
        
        routes = self.service.get_multiple_routes(start_point, destinations)
        
        self.assertEqual(len(routes), 3)
        self.assertEqual(routes[0]['duration'], 900)
        self.assertEqual(routes[1]['duration'], 1200)
        self.assertEqual(routes[2]['duration'], 1500)
    
    @patch('requests.get')
    def test_optimize_route_order(self, mock_get):
        """Test route optimization for multiple stops"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "trips": [{
                "legs": [
                    {"duration": 600, "distance": 3000},
                    {"duration": 800, "distance": 4000},
                    {"duration": 700, "distance": 3500}
                ],
                "duration": 2100,
                "distance": 10500
            }],
            "waypoints": [
                {"waypoint_index": 0, "trips_index": 0, "hint": "hint1"},
                {"waypoint_index": 1, "trips_index": 0, "hint": "hint2"},
                {"waypoint_index": 2, "trips_index": 0, "hint": "hint3"}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        locations = [
            Point(77.05, 28.05),
            Point(77.08, 28.08),
            Point(77.10, 28.10),
            Point(77.06, 28.06)
        ]
        
        optimization = self.service.optimize_route(locations)
        
        self.assertIn('duration', optimization)
        self.assertIn('distance', optimization)
        self.assertIn('optimized_order', optimization)


class PorterServiceTestCase(BaseAPITestCase):
    """Test cases for Porter Service"""
    
    def setUp(self):
        super().setUp()
        self.service = PorterService()
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization
        )
    
    @patch('requests.post')
    def test_create_porter_order(self, mock_post):
        """Test creating Porter order"""
        mock_response = Mock()
        mock_response.json.return_value = MockExternalServices.mock_porter_response()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        pickup_details = {
            "address": "123 Pickup Street",
            "lat": 28.05,
            "lng": 77.05,
            "contact_name": "Merchant",
            "contact_phone": "+919876543211"
        }
        
        delivery_details = {
            "address": "456 Delivery Avenue",
            "lat": 28.08,
            "lng": 77.08,
            "contact_name": "Customer",
            "contact_phone": "+919876543210"
        }
        
        porter_order = self.service.create_order(
            order=self.order,
            pickup_details=pickup_details,
            delivery_details=delivery_details
        )
        
        self.assertEqual(porter_order['order_id'], "PORTER_123")
        self.assertEqual(porter_order['status'], "confirmed")
        self.assertIn('fare', porter_order)
        self.assertIn('driver', porter_order)
    
    @patch('requests.get')
    def test_track_porter_order(self, mock_get):
        """Test tracking Porter order"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "order_id": "PORTER_123",
            "status": "in_transit",
            "driver_location": {
                "lat": 28.06,
                "lng": 77.06
            },
            "eta_minutes": 15
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        tracking = self.service.track_order("PORTER_123")
        
        self.assertEqual(tracking['status'], "in_transit")
        self.assertIn('driver_location', tracking)
        self.assertEqual(tracking['eta_minutes'], 15)
    
    @patch('requests.post')
    def test_cancel_porter_order(self, mock_post):
        """Test cancelling Porter order"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "order_id": "PORTER_123",
            "status": "cancelled",
            "cancellation_fee": 25.0
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = self.service.cancel_order("PORTER_123", "Customer request")
        
        self.assertEqual(result['status'], "cancelled")
        self.assertEqual(result['cancellation_fee'], 25.0)


class DeliveryAPITestCase(BaseAPITestCase):
    """Test cases for Delivery API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization
        )
        
        self.delivery_task = DeliveryTask.objects.create(
            order=self.order,
            organization=self.organization,
            pickup_location=Point(77.05, 28.05),
            delivery_location=Point(77.08, 28.08),
            delivery_zone=self.delivery_zone,
            estimated_distance=5.0,
            estimated_duration=1800,
            status='pending'
        )
    
    def test_delivery_zone_list(self):
        """Test listing delivery zones"""
        url = reverse('delivery-zone-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_delivery_zone_create(self):
        """Test creating delivery zone"""
        data = {
            "name": "New Zone",
            "zone_type": "suburb",
            "coverage_area": {
                "type": "Polygon",
                "coordinates": [[[77.2, 28.2], [77.3, 28.2], [77.3, 28.3], [77.2, 28.3], [77.2, 28.2]]]
            },
            "base_fee": "25.00",
            "per_km_rate": "6.00",
            "is_active": True
        }
        
        url = reverse('delivery-zone-list')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        zone = DeliveryZone.objects.get(name="New Zone")
        self.assertEqual(zone.zone_type, "suburb")
        self.assertEqual(zone.base_fee, Decimal('25.00'))
    
    def test_delivery_task_list(self):
        """Test listing delivery tasks"""
        url = reverse('delivery-task-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_delivery_task_assign(self):
        """Test assigning delivery task"""
        url = reverse('delivery-task-assign', kwargs={'pk': self.delivery_task.pk})
        data = {"rider_id": str(self.rider.id)}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.delivery_task.refresh_from_db()
        self.assertEqual(self.delivery_task.rider, self.rider)
        self.assertEqual(self.delivery_task.status, 'assigned')
    
    def test_delivery_task_update_status(self):
        """Test updating delivery task status"""
        # First assign task to rider
        self.delivery_task.rider = self.rider
        self.delivery_task.status = 'assigned'
        self.delivery_task.save()
        
        url = reverse('delivery-task-update-status', kwargs={'pk': self.delivery_task.pk})
        data = {
            "status": "picked_up",
            "notes": "Package collected from merchant"
        }
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.delivery_task.refresh_from_db()
        self.assertEqual(self.delivery_task.status, 'picked_up')
    
    @patch('logistics.services.OSRMService.get_route')
    def test_calculate_delivery_fee_endpoint(self, mock_route):
        """Test delivery fee calculation endpoint"""
        mock_route.return_value = {
            "distance": 8.5,
            "duration": 2400
        }
        
        data = {
            "pickup_lat": 77.05,
            "pickup_lng": 28.05,
            "delivery_lat": 77.12,
            "delivery_lng": 28.12
        }
        
        url = reverse('delivery-calculate-fee')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_data = response.json()
        self.assertIn('delivery_fee', response_data)
        self.assertIn('distance', response_data)
        self.assertIn('duration', response_data)
        self.assertIn('delivery_zone', response_data)


class DeliveryTrackingTestCase(BaseAPITestCase):
    """Test cases for Delivery Tracking"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_customer()
        
        self.order = TestDataFactory.create_order(
            self.customer, self.merchant, self.organization
        )
        
        self.delivery_task = DeliveryTask.objects.create(
            order=self.order,
            organization=self.organization,
            pickup_location=Point(77.05, 28.05),
            delivery_location=Point(77.08, 28.08),
            delivery_zone=self.delivery_zone,
            rider=self.rider,
            status='in_transit'
        )
    
    def test_track_delivery_customer(self):
        """Test customer tracking their delivery"""
        # Create tracking data
        DeliveryTracking.objects.create(
            delivery_task=self.delivery_task,
            current_location=Point(77.06, 28.06),
            status='in_transit',
            estimated_arrival=datetime.now() + timedelta(minutes=20)
        )
        
        url = reverse('delivery-track', kwargs={'order_id': self.order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['status'], 'in_transit')
        self.assertIn('current_location', data)
        self.assertIn('estimated_arrival', data)
        self.assertIn('rider_info', data)
    
    def test_track_delivery_other_customer(self):
        """Test customer cannot track other's delivery"""
        # Create another customer
        other_customer = Customer.objects.create(
            user=self.admin_user,  # Using admin user as another customer
            organization=self.organization,
            phone_number="+919876543299"
        )
        
        other_order = TestDataFactory.create_order(
            other_customer, self.merchant, self.organization
        )
        
        url = reverse('delivery-track', kwargs={'order_id': other_order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_rider_location_update(self):
        """Test rider updating their location"""
        self.authenticate_user(self.rider_user)
        
        data = {
            "lat": 77.065,
            "lng": 28.065,
            "status": "in_transit"
        }
        
        url = reverse('delivery-rider-location-update', kwargs={'task_id': self.delivery_task.id})
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check tracking was updated
        tracking = DeliveryTracking.objects.get(delivery_task=self.delivery_task)
        self.assertEqual(float(tracking.current_location.x), 77.065)
        self.assertEqual(float(tracking.current_location.y), 28.065)


class DeliveryBatchTestCase(BaseAPITestCase):
    """Test cases for Delivery Batch optimization"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_admin()
        
        # Create multiple delivery tasks for batching
        self.delivery_tasks = []
        for i in range(4):
            order = TestDataFactory.create_order(
                self.customer, self.merchant, self.organization,
                delivery_address=f"Address {i}, Test City"
            )
            
            task = DeliveryTask.objects.create(
                order=order,
                organization=self.organization,
                pickup_location=Point(77.05, 28.05),
                delivery_location=Point(77.08 + (0.01 * i), 28.08 + (0.01 * i)),
                delivery_zone=self.delivery_zone,
                estimated_distance=3.0 + i,
                estimated_duration=900 + (i * 300),
                status='pending'
            )
            self.delivery_tasks.append(task)
    
    @patch('logistics.services.OSRMService.optimize_route')
    def test_create_delivery_batch(self, mock_optimize):
        """Test creating optimized delivery batch"""
        mock_optimize.return_value = {
            "duration": 3600,
            "distance": 15000,
            "optimized_order": [0, 2, 1, 3]
        }
        
        data = {
            "rider_id": str(self.rider.id),
            "task_ids": [str(task.id) for task in self.delivery_tasks]
        }
        
        url = reverse('delivery-batch-create')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        response_data = response.json()
        self.assertEqual(response_data['task_count'], 4)
        self.assertEqual(response_data['rider'], str(self.rider.id))
        self.assertIn('optimized_route', response_data)
        
        # Check batch was created
        batch = DeliveryBatch.objects.get(rider=self.rider)
        self.assertEqual(batch.task_count, 4)
        self.assertEqual(batch.total_distance, 15.0)  # 15000m = 15km
        self.assertEqual(batch.estimated_duration, 3600)
    
    def test_batch_list(self):
        """Test listing delivery batches"""
        # Create test batch
        batch = DeliveryBatch.objects.create(
            rider=self.rider,
            organization=self.organization,
            task_count=2,
            total_distance=10.0,
            estimated_duration=2400,
            status='created'
        )
        
        url = reverse('delivery-batch-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) >= 1)
    
    def test_batch_start(self):
        """Test starting delivery batch"""
        batch = DeliveryBatch.objects.create(
            rider=self.rider,
            organization=self.organization,
            task_count=2,
            status='created'
        )
        
        url = reverse('delivery-batch-start', kwargs={'pk': batch.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'in_progress')
        self.assertIsNotNone(batch.started_at)
    
    def test_batch_complete(self):
        """Test completing delivery batch"""
        batch = DeliveryBatch.objects.create(
            rider=self.rider,
            organization=self.organization,
            task_count=2,
            status='in_progress',
            started_at=datetime.now()
        )
        
        url = reverse('delivery-batch-complete', kwargs={'pk': batch.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'completed')
        self.assertIsNotNone(batch.completed_at)