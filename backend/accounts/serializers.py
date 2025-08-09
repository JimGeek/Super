"""
Serializers for accounts app
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Organization, UserAddress, OTPVerification


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'business_type', 'status', 'registration_number',
            'gstin', 'email', 'phone', 'address_line1', 'address_line2',
            'city', 'state', 'pincode', 'location', 'delivery_radius',
            'service_zones', 'business_hours', 'platform_fee_percentage',
            'commission_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class UserAddressSerializer(serializers.ModelSerializer):
    """Serializer for UserAddress model"""
    
    class Meta:
        model = UserAddress
        fields = [
            'id', 'label', 'address_type', 'address_line1', 'address_line2',
            'landmark', 'city', 'state', 'pincode', 'location', 'is_default',
            'is_active'
        ]
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for User profile"""
    addresses = UserAddressSerializer(many=True, read_only=True)
    organization = OrganizationSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name', 'role',
            'user_type', 'organization', 'avatar', 'date_of_birth', 'gender',
            'preferred_language', 'timezone', 'company_name', 'company_gstin',
            'is_phone_verified', 'is_email_verified', 'last_location',
            'addresses', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'role', 'is_phone_verified', 'is_email_verified',
            'created_at', 'updated_at'
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'phone', 'first_name', 'last_name', 'password',
            'confirm_password', 'user_type', 'preferred_language', 'timezone'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              email=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('Account is deactivated')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password')


class OTPRequestSerializer(serializers.Serializer):
    """Serializer for OTP request"""
    identifier = serializers.CharField(help_text="Phone number or email")
    verification_type = serializers.ChoiceField(choices=OTPVerification.VERIFICATION_TYPES)


class OTPVerifySerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    identifier = serializers.CharField()
    otp = serializers.CharField(max_length=6)
    verification_type = serializers.ChoiceField(choices=OTPVerification.VERIFICATION_TYPES)


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs


class MerchantOnboardingSerializer(serializers.Serializer):
    """Serializer for merchant onboarding"""
    # User details
    email = serializers.EmailField()
    phone = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    
    # Organization details
    organization_name = serializers.CharField()
    business_type = serializers.ChoiceField(choices=Organization.MERCHANT_TYPES)
    registration_number = serializers.CharField(required=False)
    gstin = serializers.CharField(required=False)
    
    # Address
    address_line1 = serializers.CharField()
    address_line2 = serializers.CharField(required=False)
    city = serializers.CharField()
    state = serializers.CharField()
    pincode = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    
    # Business settings
    delivery_radius = serializers.FloatField(default=5.0)
    business_hours = serializers.JSONField(required=False)
    
    def create(self, validated_data):
        from django.contrib.gis.geos import Point
        from django.db import transaction
        
        with transaction.atomic():
            # Create organization
            org_data = {
                'name': validated_data['organization_name'],
                'business_type': validated_data['business_type'],
                'registration_number': validated_data.get('registration_number', ''),
                'gstin': validated_data.get('gstin', ''),
                'email': validated_data['email'],
                'phone': validated_data['phone'],
                'address_line1': validated_data['address_line1'],
                'address_line2': validated_data.get('address_line2', ''),
                'city': validated_data['city'],
                'state': validated_data['state'],
                'pincode': validated_data['pincode'],
                'location': Point(validated_data['longitude'], validated_data['latitude']),
                'delivery_radius': validated_data.get('delivery_radius', 5.0),
                'business_hours': validated_data.get('business_hours', {})
            }
            
            organization = Organization.objects.create(**org_data)
            
            # Create user
            user_data = {
                'email': validated_data['email'],
                'phone': validated_data['phone'],
                'first_name': validated_data['first_name'],
                'last_name': validated_data['last_name'],
                'password': validated_data['password'],
                'role': 'merchant_owner',
                'organization': organization
            }
            
            user = User.objects.create_user(**user_data)
            
            return {'user': user, 'organization': organization}