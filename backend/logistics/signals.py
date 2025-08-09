from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Delivery, DeliveryPartner, DeliveryTracking
from orders.models import Order


@receiver(post_save, sender=Order)
def create_delivery_on_order_confirmation(sender, instance, created, **kwargs):
    """Create delivery record when order is confirmed"""
    
    if instance.status == 'confirmed' and not hasattr(instance, 'delivery'):
        # Extract addresses from order
        pickup_address = {
            'address_line1': instance.merchant.address_line1,
            'address_line2': instance.merchant.address_line2,
            'city': instance.merchant.city,
            'state': instance.merchant.state,
            'pincode': instance.merchant.pincode,
            'coordinates': [
                float(instance.merchant.longitude),
                float(instance.merchant.latitude)
            ],
            'landmark': instance.merchant.landmark,
            'phone': instance.merchant.phone_number,
            'contact_name': instance.merchant.business_name
        }
        
        delivery_address = {
            'address_line1': instance.delivery_address.get('address_line1', ''),
            'address_line2': instance.delivery_address.get('address_line2', ''),
            'city': instance.delivery_address.get('city', ''),
            'state': instance.delivery_address.get('state', ''),
            'pincode': instance.delivery_address.get('pincode', ''),
            'coordinates': [
                float(instance.delivery_address.get('longitude', 0)),
                float(instance.delivery_address.get('latitude', 0))
            ],
            'landmark': instance.delivery_address.get('landmark', ''),
            'phone': instance.customer.phone_number,
            'contact_name': instance.customer.full_name
        }
        
        # Determine delivery priority based on order type
        priority = 'normal'
        if instance.order_type == 'express':
            priority = 'high'
        elif instance.order_type == 'scheduled':
            priority = 'low'
        
        # Create delivery record
        delivery = Delivery.objects.create(
            organization=instance.organization,
            order=instance,
            status='pending',
            priority=priority,
            pickup_address=pickup_address,
            delivery_address=delivery_address,
            pickup_instructions=instance.special_instructions or '',
            delivery_instructions=instance.delivery_notes or '',
        )
        
        # Trigger auto-assignment after a short delay
        from .tasks import auto_assign_delivery
        auto_assign_delivery.apply_async(
            args=[str(delivery.id)],
            countdown=60  # Wait 1 minute before auto-assignment
        )


@receiver(post_save, sender=Delivery)
def update_delivery_timestamps(sender, instance, created, **kwargs):
    """Update delivery timestamps based on status changes"""
    
    if not created:
        # Check if status changed
        if instance.tracker.has_changed('status'):
            now = timezone.now()
            
            if instance.status == 'assigned' and not instance.assigned_at:
                instance.assigned_at = now
                
                # Set estimated times
                pickup_time = now + timezone.timedelta(minutes=20)
                delivery_time = pickup_time + timezone.timedelta(minutes=45)
                instance.estimated_pickup_time = pickup_time
                instance.estimated_delivery_time = delivery_time
                
                instance.save(update_fields=[
                    'assigned_at', 'estimated_pickup_time', 'estimated_delivery_time'
                ])
            
            elif instance.status == 'picked_up' and not instance.actual_pickup_time:
                instance.actual_pickup_time = now
                instance.save(update_fields=['actual_pickup_time'])
            
            elif instance.status == 'delivered' and not instance.actual_delivery_time:
                instance.actual_delivery_time = now
                instance.save(update_fields=['actual_delivery_time'])
                
                # Update partner performance metrics
                if instance.delivery_partner:
                    partner = instance.delivery_partner
                    partner.total_deliveries += 1
                    partner.successful_deliveries += 1
                    
                    # Calculate average delivery time
                    if instance.actual_pickup_time:
                        delivery_duration = (
                            instance.actual_delivery_time - instance.actual_pickup_time
                        ).total_seconds() / 60  # Convert to minutes
                        
                        # Update rolling average
                        current_avg = partner.average_delivery_time
                        total_deliveries = partner.total_deliveries
                        
                        new_avg = (
                            (current_avg * (total_deliveries - 1) + delivery_duration) /
                            total_deliveries
                        )
                        partner.average_delivery_time = new_avg
                    
                    partner.save(update_fields=[
                        'total_deliveries', 'successful_deliveries', 'average_delivery_time'
                    ])


@receiver(post_save, sender=DeliveryTracking)
def update_delivery_status_from_tracking(sender, instance, created, **kwargs):
    """Update delivery status based on location tracking"""
    
    if created:
        delivery = instance.delivery
        
        # Auto-update status based on location proximity
        from django.contrib.gis.measure import Distance
        from django.contrib.gis.geos import Point
        
        current_location = instance.location
        
        # Check proximity to pickup location
        pickup_coords = delivery.pickup_address.get('coordinates', [0, 0])
        pickup_point = Point(pickup_coords[0], pickup_coords[1])
        pickup_distance = current_location.distance(pickup_point)
        
        # Check proximity to delivery location
        delivery_coords = delivery.delivery_address.get('coordinates', [0, 0])
        delivery_point = Point(delivery_coords[0], delivery_coords[1])
        delivery_distance = current_location.distance(delivery_point)
        
        # Distance threshold (100 meters)
        threshold = Distance(m=100)
        
        # Auto-update status based on proximity
        status_updated = False
        
        if (delivery.status == 'accepted' and 
            pickup_distance <= threshold and 
            instance.speed < 5):  # Stationary or slow
            
            # Near pickup location and not moving fast - suggest pickup
            # This could trigger a notification to the partner
            pass
        
        elif (delivery.status == 'picked_up' and 
              delivery_distance <= threshold and
              instance.speed < 5):
            
            # Near delivery location and not moving fast - suggest completion
            # This could trigger a notification to the partner
            pass


@receiver(pre_save, sender=DeliveryPartner)
def update_partner_availability(sender, instance, **kwargs):
    """Update partner availability based on location and activity"""
    
    # Check if location or status changed
    if instance.pk:
        try:
            old_instance = DeliveryPartner.objects.get(pk=instance.pk)
            
            # If location was updated, check availability
            if (instance.current_location != old_instance.current_location or
                instance.last_location_update != old_instance.last_location_update):
                
                # Partner is available if:
                # 1. Status is active
                # 2. Has current location
                # 3. Location was updated recently (within 10 minutes)
                now = timezone.now()
                
                is_location_fresh = (
                    instance.last_location_update and
                    now - instance.last_location_update <= timezone.timedelta(minutes=10)
                )
                
                instance._is_available_cache = (
                    instance.status == 'active' and
                    instance.current_location is not None and
                    is_location_fresh
                )
                
        except DeliveryPartner.DoesNotExist:
            pass


# Additional signals for analytics and notifications
@receiver(post_save, sender=Delivery)
def trigger_delivery_notifications(sender, instance, created, **kwargs):
    """Send notifications for delivery events"""
    
    if created:
        # New delivery created - notify admin/dispatcher
        pass
    
    elif instance.tracker.has_changed('status'):
        # Status changed - notify relevant parties
        
        if instance.status == 'assigned' and instance.delivery_partner:
            # Notify partner of new assignment
            pass
        
        elif instance.status == 'picked_up':
            # Notify customer that order is picked up
            pass
        
        elif instance.status == 'in_transit':
            # Send tracking link to customer
            pass
        
        elif instance.status == 'delivered':
            # Notify merchant and customer of successful delivery
            # Request customer rating
            pass
        
        elif instance.status == 'failed':
            # Notify admin and customer of failed delivery
            # Trigger retry logic
            pass


@receiver(post_save, sender=Delivery)
def update_order_status_from_delivery(sender, instance, **kwargs):
    """Update order status based on delivery status"""
    
    order = instance.order
    
    # Map delivery status to order status
    status_mapping = {
        'pending': 'confirmed',
        'assigned': 'confirmed',
        'accepted': 'processing',
        'picked_up': 'out_for_delivery',
        'in_transit': 'out_for_delivery',
        'delivered': 'delivered',
        'failed': 'failed',
        'cancelled': 'cancelled'
    }
    
    new_order_status = status_mapping.get(instance.status)
    
    if new_order_status and order.status != new_order_status:
        order.status = new_order_status
        order.save(update_fields=['status'])


# Cleanup signals
@receiver(post_save, sender=DeliveryTracking)
def cleanup_old_tracking_data(sender, instance, created, **kwargs):
    """Clean up old tracking data to prevent database bloat"""
    
    if created:
        # Keep only last 1000 tracking records per delivery
        delivery = instance.delivery
        
        old_records = delivery.tracking_data.order_by('-recorded_at')[1000:]
        old_record_ids = list(old_records.values_list('id', flat=True))
        
        if old_record_ids:
            DeliveryTracking.objects.filter(id__in=old_record_ids).delete()