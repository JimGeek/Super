#!/usr/bin/env python
"""
Seed data script for SUPER platform
"""
import os
import sys
import django
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta, date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_core.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Organization, UserAddress
from payments_upi.models import UPIProvider, VirtualPaymentAddress
from settlements.models import LedgerAccount
from orders.models import Order, OrderItem

User = get_user_model()


def create_upi_providers():
    """Create UPI providers"""
    print("🏦 Creating UPI providers...")
    
    demo_provider = UPIProvider.objects.get_or_create(
        code='demo',
        defaults={
            'name': 'Demo UPI Provider',
            'base_url': 'https://demo-upi-api.com',
            'api_key': 'demo_api_key',
            'secret_key': 'demo_secret_key',
            'webhook_secret': 'demo_webhook_secret',
            'supports_intent': True,
            'supports_collect': True,
            'supports_qr': True,
            'supports_mandates': True,
            'is_active': True,
            'is_production': False
        }
    )[0]
    
    print(f"✅ Created UPI provider: {demo_provider.name}")


def create_demo_organizations():
    """Create demo merchant organizations"""
    print("🏪 Creating demo merchants...")
    
    merchants = [
        {
            'name': 'Raj Kirana Store',
            'business_type': 'kirana',
            'email': 'raj@rajkirana.com',
            'phone': '+919876543210',
            'address_line1': 'Shop No. 15, Gandhi Nagar',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400062',
            'location': Point(72.8777, 19.0760),  # Mumbai coordinates
            'status': 'active',
            'delivery_radius': 3.0,
        },
        {
            'name': 'Style Cut Salon',
            'business_type': 'barber',
            'email': 'info@stylecutsalon.com',
            'phone': '+919876543211',
            'address_line1': '2nd Floor, Silver Mall',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400061',
            'location': Point(72.8777, 19.0770),
            'status': 'active',
            'delivery_radius': 5.0,
        },
        {
            'name': 'AutoCare Garage',
            'business_type': 'garage',
            'email': 'service@autocare.com',
            'phone': '+919876543212',
            'address_line1': 'Plot No. 23, Industrial Area',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400063',
            'location': Point(72.8777, 19.0750),
            'status': 'active',
            'delivery_radius': 10.0,
        },
        {
            'name': 'AquaPure Water Solutions',
            'business_type': 'water_purifier',
            'email': 'sales@aquapure.com',
            'phone': '+919876543213',
            'address_line1': 'Office No. 501, Tech Tower',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400064',
            'location': Point(72.8777, 19.0780),
            'status': 'active',
            'delivery_radius': 15.0,
        },
        {
            'name': 'Fresh Mart Grocery',
            'business_type': 'grocery',
            'email': 'manager@freshmart.com',
            'phone': '+919876543214',
            'address_line1': 'Ground Floor, City Center',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400065',
            'location': Point(72.8777, 19.0740),
            'status': 'active',
            'delivery_radius': 5.0,
        }
    ]
    
    created_merchants = []
    for merchant_data in merchants:
        merchant, created = Organization.objects.get_or_create(
            email=merchant_data['email'],
            defaults=merchant_data
        )
        
        if created:
            print(f"✅ Created merchant: {merchant.name}")
        else:
            print(f"📝 Merchant already exists: {merchant.name}")
        
        created_merchants.append(merchant)
    
    return created_merchants


def create_demo_users(merchants):
    """Create demo users"""
    print("👥 Creating demo users...")
    
    # Create super admin
    super_admin, created = User.objects.get_or_create(
        email='admin@super.com',
        defaults={
            'phone': '+919999999999',
            'first_name': 'Super',
            'last_name': 'Admin',
            'role': 'super_admin',
            'is_staff': True,
            'is_superuser': True,
            'is_phone_verified': True,
            'is_email_verified': True,
        }
    )
    
    if created:
        super_admin.set_password('admin123')
        super_admin.save()
        print(f"✅ Created super admin: {super_admin.email}")
    
    # Create merchant owners
    merchant_owners = []
    for i, merchant in enumerate(merchants):
        owner_email = f'owner{i+1}@super.com'
        owner, created = User.objects.get_or_create(
            email=owner_email,
            defaults={
                'phone': f'+919876543{220+i}',
                'first_name': f'Owner{i+1}',
                'last_name': 'Merchant',
                'role': 'merchant_owner',
                'organization': merchant,
                'is_phone_verified': True,
                'is_email_verified': True,
            }
        )
        
        if created:
            owner.set_password('merchant123')
            owner.save()
            print(f"✅ Created merchant owner: {owner.email} for {merchant.name}")
        
        merchant_owners.append(owner)
    
    # Create demo customers
    customers = []
    customer_data = [
        {
            'email': 'customer1@demo.com',
            'phone': '+919876543230',
            'first_name': 'Rahul',
            'last_name': 'Sharma',
        },
        {
            'email': 'customer2@demo.com',
            'phone': '+919876543231',
            'first_name': 'Priya',
            'last_name': 'Patel',
        },
        {
            'email': 'customer3@demo.com',
            'phone': '+919876543232',
            'first_name': 'Amit',
            'last_name': 'Kumar',
        }
    ]
    
    for customer_info in customer_data:
        customer, created = User.objects.get_or_create(
            email=customer_info['email'],
            defaults={
                **customer_info,
                'role': 'consumer',
                'is_phone_verified': True,
                'is_email_verified': True,
            }
        )
        
        if created:
            customer.set_password('customer123')
            customer.save()
            print(f"✅ Created customer: {customer.email}")
            
            # Add address for customer
            UserAddress.objects.get_or_create(
                user=customer,
                label='Home',
                defaults={
                    'address_type': 'home',
                    'address_line1': f'Flat {201+len(customers)}, Sunrise Apartments',
                    'address_line2': 'Near Metro Station',
                    'city': 'Mumbai',
                    'state': 'Maharashtra',
                    'pincode': '400061',
                    'location': Point(72.8777 + (len(customers) * 0.001), 19.0760 + (len(customers) * 0.001)),
                    'is_default': True,
                }
            )
        
        customers.append(customer)
    
    # Create demo rider
    rider, created = User.objects.get_or_create(
        email='rider1@super.com',
        defaults={
            'phone': '+919876543240',
            'first_name': 'Vikash',
            'last_name': 'Singh',
            'role': 'rider',
            'is_phone_verified': True,
            'is_email_verified': True,
        }
    )
    
    if created:
        rider.set_password('rider123')
        rider.save()
        print(f"✅ Created rider: {rider.email}")
    
    return {
        'super_admin': super_admin,
        'merchant_owners': merchant_owners,
        'customers': customers,
        'rider': rider,
    }


def create_demo_vpas(merchants, provider):
    """Create VPAs for merchants"""
    print("💳 Creating VPAs...")
    
    # Platform VPA
    platform_vpa, created = VirtualPaymentAddress.objects.get_or_create(
        vpa='platform@super',
        defaults={
            'holder_name': 'SUPER Platform',
            'purpose': 'platform',
            'provider': provider,
            'is_active': True,
            'is_verified': True,
        }
    )
    
    if created:
        print(f"✅ Created platform VPA: {platform_vpa.vpa}")
    
    # Merchant VPAs
    for merchant in merchants:
        vpa_name = f"{merchant.name.lower().replace(' ', '')}@super"
        vpa, created = VirtualPaymentAddress.objects.get_or_create(
            vpa=vpa_name,
            defaults={
                'holder_name': merchant.name,
                'organization': merchant,
                'purpose': 'merchant',
                'provider': provider,
                'is_active': True,
                'is_verified': True,
            }
        )
        
        if created:
            print(f"✅ Created merchant VPA: {vpa.vpa}")


def create_ledger_accounts(merchants, users):
    """Create ledger accounts"""
    print("📊 Creating ledger accounts...")
    
    # Platform account
    platform_account, created = LedgerAccount.objects.get_or_create(
        account_number='PLAT000001',
        defaults={
            'name': 'Platform Main Account',
            'type': 'platform',
            'is_active': True,
        }
    )
    
    if created:
        print(f"✅ Created platform account: {platform_account.account_number}")
    
    # Merchant accounts
    for i, merchant in enumerate(merchants):
        account_number = f"MERCH{str(i+1).zfill(6)}"
        merchant_account, created = LedgerAccount.objects.get_or_create(
            account_number=account_number,
            defaults={
                'name': f"{merchant.name} - Merchant Account",
                'type': 'merchant',
                'org_id': merchant.id,
                'is_active': True,
            }
        )
        
        if created:
            print(f"✅ Created merchant account: {merchant_account.account_number}")
    
    # Customer wallet accounts
    for i, customer in enumerate(users['customers']):
        account_number = f"CUST{str(i+1).zfill(6)}"
        customer_account, created = LedgerAccount.objects.get_or_create(
            account_number=account_number,
            defaults={
                'name': f"{customer.get_full_name()} - Wallet",
                'type': 'consumer',
                'user_id': customer.id,
                'is_active': True,
            }
        )
        
        if created:
            print(f"✅ Created customer account: {customer_account.account_number}")


def create_demo_orders(merchants, customers):
    """Create demo orders"""
    print("📦 Creating demo orders...")
    
    # Kirana order
    kirana = merchants[0]  # Raj Kirana Store
    customer = customers[0]  # Rahul Sharma
    
    kirana_order = Order.objects.create(
        order_number='KIRAN20241201001',
        customer=customer,
        merchant=kirana,
        vertical='kirana',
        order_type='delivery',
        status='completed',
        subtotal=Decimal('450.00'),
        tax_amount=Decimal('81.00'),
        delivery_fee=Decimal('30.00'),
        total_amount=Decimal('561.00'),
        payment_method='prepaid',
        payment_status='paid',
        delivery_address={
            'address_line1': 'Flat 201, Sunrise Apartments',
            'city': 'Mumbai',
            'pincode': '400061'
        },
        customer_rating=5,
        customer_review='Great quality products and fast delivery!',
        placed_at=timezone.now() - timedelta(hours=2),
        completed_at=timezone.now() - timedelta(minutes=30),
    )
    
    # Add items to kirana order
    OrderItem.objects.create(
        order=kirana_order,
        name='Basmati Rice',
        description='1kg Premium Basmati Rice',
        unit_price=Decimal('180.00'),
        quantity=Decimal('1.000'),
        total_price=Decimal('180.00'),
    )
    
    OrderItem.objects.create(
        order=kirana_order,
        name='Toor Dal',
        description='500g Organic Toor Dal',
        unit_price=Decimal('135.00'),
        quantity=Decimal('2.000'),
        total_price=Decimal('270.00'),
    )
    
    print(f"✅ Created kirana order: {kirana_order.order_number}")
    
    # Salon order
    salon = merchants[1]  # Style Cut Salon
    customer = customers[1]  # Priya Patel
    
    salon_order = Order.objects.create(
        order_number='SALON20241201001',
        customer=customer,
        merchant=salon,
        vertical='barber',
        order_type='in_store_appointment',
        status='completed',
        subtotal=Decimal('800.00'),
        tax_amount=Decimal('144.00'),
        total_amount=Decimal('944.00'),
        payment_method='prepaid',
        payment_status='paid',
        scheduled_for=timezone.now() - timedelta(hours=1),
        customer_rating=4,
        customer_review='Professional service, will come again!',
        placed_at=timezone.now() - timedelta(hours=3),
        completed_at=timezone.now() - timedelta(minutes=15),
    )
    
    # Add services to salon order
    OrderItem.objects.create(
        order=salon_order,
        item_type='service',
        name='Hair Cut & Styling',
        description='Premium hair cut with styling',
        unit_price=Decimal('500.00'),
        quantity=Decimal('1.000'),
        total_price=Decimal('500.00'),
        duration_minutes=45,
    )
    
    OrderItem.objects.create(
        order=salon_order,
        item_type='service',
        name='Hair Spa Treatment',
        description='Nourishing hair spa treatment',
        unit_price=Decimal('300.00'),
        quantity=Decimal('1.000'),
        total_price=Decimal('300.00'),
        duration_minutes=30,
    )
    
    print(f"✅ Created salon order: {salon_order.order_number}")
    
    # Pending garage order
    garage = merchants[2]  # AutoCare Garage
    customer = customers[2]  # Amit Kumar
    
    garage_order = Order.objects.create(
        order_number='GARAGE20241201001',
        customer=customer,
        merchant=garage,
        vertical='garage',
        order_type='at_home_service',
        status='confirmed',
        subtotal=Decimal('2500.00'),
        tax_amount=Decimal('450.00'),
        service_fee=Decimal('200.00'),
        total_amount=Decimal('3150.00'),
        payment_method='postpaid',
        payment_status='pending',
        scheduled_for=timezone.now() + timedelta(hours=2),
        customer_notes='Please call 15 minutes before arriving',
        placed_at=timezone.now() - timedelta(minutes=45),
        confirmed_at=timezone.now() - timedelta(minutes=30),
    )
    
    # Add services to garage order
    OrderItem.objects.create(
        order=garage_order,
        item_type='service',
        name='Car Service (Full)',
        description='Complete car servicing package',
        unit_price=Decimal('2000.00'),
        quantity=Decimal('1.000'),
        total_price=Decimal('2000.00'),
        duration_minutes=180,
    )
    
    OrderItem.objects.create(
        order=garage_order,
        item_type='product',
        name='Engine Oil',
        description='5W-30 Synthetic Engine Oil',
        unit_price=Decimal('500.00'),
        quantity=Decimal('1.000'),
        total_price=Decimal('500.00'),
    )
    
    print(f"✅ Created garage order: {garage_order.order_number}")


def main():
    """Main seeding function"""
    print("🌱 Starting SUPER platform seeding...")
    print("=" * 60)
    
    try:
        # Create UPI providers
        create_upi_providers()
        
        # Create demo merchants
        merchants = create_demo_organizations()
        
        # Create demo users
        users = create_demo_users(merchants)
        
        # Create VPAs
        provider = UPIProvider.objects.get(code='demo')
        create_demo_vpas(merchants, provider)
        
        # Create ledger accounts
        create_ledger_accounts(merchants, users)
        
        # Create demo orders
        create_demo_orders(merchants, users['customers'])
        
        print("\n" + "=" * 60)
        print("🎉 Seeding completed successfully!")
        print("\n📋 Demo Credentials:")
        print("   Super Admin: admin@super.com / admin123")
        print("   Merchant1: owner1@super.com / merchant123")
        print("   Customer1: customer1@demo.com / customer123")
        print("   Rider: rider1@super.com / rider123")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Seeding failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()