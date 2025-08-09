"""
Custom middleware for SUPER platform
"""
import uuid
import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db import connection
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantMiddleware(MiddlewareMixin):
    """
    Multi-tenant middleware to set organization context
    """
    
    def process_request(self, request):
        # Extract organization from headers or user context
        org_id = None
        
        # Try to get from header first
        if 'X-Org-ID' in request.headers:
            org_id = request.headers.get('X-Org-ID')
        elif hasattr(request, 'user') and request.user.is_authenticated:
            # Get from user's organization
            if hasattr(request.user, 'organization'):
                org_id = request.user.organization.id
        
        # Set organization context
        request.org_id = org_id
        
        return None


class AuditMiddleware(MiddlewareMixin):
    """
    Audit middleware to log API requests and user actions
    """
    
    def process_request(self, request):
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())
        
        # Log request
        if request.path.startswith('/api/'):
            logger.info(
                f"API Request - {request.request_id} - "
                f"{request.method} {request.path} - "
                f"User: {getattr(request.user, 'id', 'Anonymous')} - "
                f"Org: {getattr(request, 'org_id', 'None')}"
            )
        
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log response for API calls
            if request.path.startswith('/api/'):
                logger.info(
                    f"API Response - {getattr(request, 'request_id', 'Unknown')} - "
                    f"Status: {response.status_code} - "
                    f"Duration: {duration:.3f}s"
                )
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Rate limit storage (in production, use Redis)
        self.rate_limit_storage = {}
    
    def __call__(self, request):
        # Check rate limit for authenticated users
        if request.user.is_authenticated:
            user_id = str(request.user.id)
            current_time = time.time()
            
            # Clean old entries (older than 1 hour)
            cutoff_time = current_time - 3600
            self.rate_limit_storage = {
                k: v for k, v in self.rate_limit_storage.items() 
                if v['timestamp'] > cutoff_time
            }
            
            # Check current user's rate limit
            if user_id in self.rate_limit_storage:
                user_data = self.rate_limit_storage[user_id]
                if user_data['count'] >= 100:  # 100 requests per hour
                    return JsonResponse(
                        {'error': 'Rate limit exceeded'}, 
                        status=429
                    )
                user_data['count'] += 1
            else:
                self.rate_limit_storage[user_id] = {
                    'count': 1,
                    'timestamp': current_time
                }
        
        response = self.get_response(request)
        return response


class DatabaseQueryLoggingMiddleware(MiddlewareMixin):
    """
    Log database queries for debugging (dev only)
    """
    
    def process_request(self, request):
        self.queries_before = len(connection.queries)
        return None
    
    def process_response(self, request, response):
        if hasattr(self, 'queries_before'):
            queries_count = len(connection.queries) - self.queries_before
            if queries_count > 10:  # Log only if many queries
                logger.warning(
                    f"High DB query count - {getattr(request, 'request_id', 'Unknown')} - "
                    f"Queries: {queries_count} - "
                    f"Path: {request.path}"
                )
        
        return response