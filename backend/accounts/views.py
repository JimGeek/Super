"""
Views for accounts app
"""
import random
import string
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.gis.geos import Point
from .models import User, Organization, UserAddress, OTPVerification, UserSession
from .serializers import (
    UserProfileSerializer, UserRegistrationSerializer, LoginSerializer,
    OrganizationSerializer, UserAddressSerializer, OTPRequestSerializer,
    OTPVerifySerializer, PasswordChangeSerializer, PasswordResetSerializer,
    PasswordResetConfirmSerializer, MerchantOnboardingSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User operations"""
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'mid_admin']:
            return User.objects.all()
        elif self.request.user.role in ['merchant_owner']:
            return User.objects.filter(organization=self.request.user.organization)
        else:
            return User.objects.filter(id=self.request.user.id)
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user profile"""
        serializer = self.get_serializer(
            request.user, 
            data=request.data, 
            partial=request.method == 'PATCH'
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        serializer = PasswordChangeSerializer(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def update_location(self, request):
        """Update user's current location"""
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude and longitude:
            request.user.last_location = Point(float(longitude), float(latitude))
            request.user.save()
            return Response({'message': 'Location updated successfully'})
        
        return Response(
            {'error': 'Latitude and longitude are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class OrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet for Organization operations"""
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'mid_admin']:
            return Organization.objects.all()
        elif self.request.user.organization:
            return Organization.objects.filter(id=self.request.user.organization.id)
        else:
            return Organization.objects.none()


class UserAddressViewSet(viewsets.ModelViewSet):
    """ViewSet for UserAddress operations"""
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set address as default"""
        address = self.get_object()
        # Remove default from other addresses
        UserAddress.objects.filter(user=request.user).update(is_default=False)
        # Set this as default
        address.is_default = True
        address.save()
        return Response({'message': 'Address set as default'})


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """User registration endpoint"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Registration successful',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with additional user data"""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Get user data
            email = request.data.get('email')
            user = User.objects.get(email=email)
            
            # Create session record
            device_id = request.META.get('HTTP_X_DEVICE_ID', 'unknown')
            device_name = request.META.get('HTTP_X_DEVICE_NAME', '')
            platform = request.META.get('HTTP_X_PLATFORM', 'web')
            app_version = request.META.get('HTTP_X_APP_VERSION', '')
            ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
            
            UserSession.objects.create(
                user=user,
                device_id=device_id,
                device_name=device_name,
                platform=platform,
                app_version=app_version,
                ip_address=ip_address,
                refresh_token=response.data['refresh'],
                expires_at=timezone.now() + timedelta(days=1)
            )
            
            # Add user data to response
            response.data['user'] = UserProfileSerializer(user).data
        
        return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            # Deactivate session
            UserSession.objects.filter(
                user=request.user,
                refresh_token=refresh_token
            ).update(is_active=False)
        
        return Response({'message': 'Logged out successfully'})
    except Exception as e:
        return Response(
            {'error': 'Logout failed'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    """Request OTP for verification"""
    serializer = OTPRequestSerializer(data=request.data)
    if serializer.is_valid():
        identifier = serializer.validated_data['identifier']
        verification_type = serializer.validated_data['verification_type']
        
        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Create OTP record
        OTPVerification.objects.create(
            identifier=identifier,
            verification_type=verification_type,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # TODO: Send OTP via SMS/Email
        # For now, return OTP in response (development only)
        return Response({
            'message': 'OTP sent successfully',
            'otp': otp,  # Remove in production
            'expires_at': (timezone.now() + timedelta(minutes=10)).isoformat()
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """Verify OTP"""
    serializer = OTPVerifySerializer(data=request.data)
    if serializer.is_valid():
        identifier = serializer.validated_data['identifier']
        otp = serializer.validated_data['otp']
        verification_type = serializer.validated_data['verification_type']
        
        try:
            otp_obj = OTPVerification.objects.get(
                identifier=identifier,
                otp=otp,
                verification_type=verification_type,
                is_verified=False,
                expires_at__gt=timezone.now()
            )
            
            # Mark as verified
            otp_obj.is_verified = True
            otp_obj.verified_at = timezone.now()
            otp_obj.save()
            
            # Update user verification status if applicable
            if verification_type == 'phone':
                User.objects.filter(phone=identifier).update(is_phone_verified=True)
            elif verification_type == 'email':
                User.objects.filter(email=identifier).update(is_email_verified=True)
            
            return Response({'message': 'OTP verified successfully'})
        
        except OTPVerification.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired OTP'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """Request password reset"""
    serializer = PasswordResetSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        # Generate OTP for password reset
        otp = ''.join(random.choices(string.digits, k=6))
        
        OTPVerification.objects.create(
            identifier=email,
            verification_type='email',
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # TODO: Send OTP via email
        return Response({
            'message': 'Password reset OTP sent to your email',
            'otp': otp,  # Remove in production
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_confirm(request):
    """Confirm password reset with OTP"""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        try:
            # Verify OTP
            otp_obj = OTPVerification.objects.get(
                identifier=email,
                otp=otp,
                verification_type='email',
                is_verified=False,
                expires_at__gt=timezone.now()
            )
            
            # Reset password
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            # Mark OTP as used
            otp_obj.is_verified = True
            otp_obj.verified_at = timezone.now()
            otp_obj.save()
            
            return Response({'message': 'Password reset successfully'})
        
        except OTPVerification.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired OTP'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def merchant_onboarding(request):
    """Merchant onboarding endpoint"""
    serializer = MerchantOnboardingSerializer(data=request.data)
    if serializer.is_valid():
        result = serializer.save()
        user = result['user']
        organization = result['organization']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Merchant onboarding successful',
            'user': UserProfileSerializer(user).data,
            'organization': OrganizationSerializer(organization).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)