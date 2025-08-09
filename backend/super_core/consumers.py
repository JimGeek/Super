"""
WebSocket consumers for real-time features
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class OrderTrackingConsumer(AsyncWebsocketConsumer):
    """Real-time order tracking updates"""
    
    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = f'order_{self.order_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'request_status':
            # Send current order status
            await self.send_order_status()
    
    async def order_update(self, event):
        """Send order update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'data': event['data']
        }))
    
    async def send_order_status(self):
        # Get current order status from database
        order_data = await self.get_order_data()
        await self.send(text_data=json.dumps({
            'type': 'order_status',
            'data': order_data
        }))
    
    @database_sync_to_async
    def get_order_data(self):
        # Implementation to fetch order data
        return {'status': 'processing', 'eta': '30 minutes'}


class DispatchConsumer(AsyncWebsocketConsumer):
    """Real-time dispatch updates for riders"""
    
    async def connect(self):
        self.rider_id = self.scope['url_route']['kwargs']['rider_id']
        self.room_group_name = f'rider_{self.rider_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'location_update':
            # Update rider location
            await self.update_rider_location(data.get('location'))
        elif message_type == 'job_response':
            # Handle job accept/reject
            await self.handle_job_response(data)
    
    async def new_job(self, event):
        """Send new job assignment to rider"""
        await self.send(text_data=json.dumps({
            'type': 'new_job',
            'data': event['data']
        }))
    
    async def job_update(self, event):
        """Send job updates to rider"""
        await self.send(text_data=json.dumps({
            'type': 'job_update',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def update_rider_location(self, location):
        # Update rider location in database
        pass
    
    @database_sync_to_async
    def handle_job_response(self, data):
        # Handle job acceptance/rejection
        pass


class SupportConsumer(AsyncWebsocketConsumer):
    """Real-time chat for support tickets"""
    
    async def connect(self):
        self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
        self.room_group_name = f'support_{self.ticket_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': self.scope['user'].id,
                'timestamp': data.get('timestamp')
            }
        )
    
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """Real-time notifications"""
    
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'user_{self.user_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def notification(self, event):
        """Send notification to user"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))