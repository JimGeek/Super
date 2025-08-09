#!/usr/bin/env python
"""
Comprehensive test runner for SUPER platform
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'super_core.settings'
    django.setup()
    
    # Set test database to use SQLite for speed
    settings.DATABASES['default'] = {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': ':memory:',
    }
    
    # Run specific test suites or all tests
    test_modules = [
        'accounts.tests',
        'payments_upi.tests', 
        'settlements.tests',
        'orders.tests',
        'flows.tests',
    ]
    
    if len(sys.argv) > 1:
        # Run specific test module
        execute_from_command_line(['manage.py', 'test'] + sys.argv[1:])
    else:
        # Run all tests
        print("Running comprehensive test suite for SUPER platform...")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for module in test_modules:
            print(f"\n🧪 Running tests for {module}")
            print("-" * 40)
            
            try:
                execute_from_command_line(['manage.py', 'test', module, '--verbosity=2'])
                print(f"✅ {module} tests passed")
                total_passed += 1
            except SystemExit as e:
                if e.code == 0:
                    print(f"✅ {module} tests passed")
                    total_passed += 1
                else:
                    print(f"❌ {module} tests failed")
                    total_failed += 1
            except Exception as e:
                print(f"❌ {module} tests failed with error: {e}")
                total_failed += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Test Summary:")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   📈 Success Rate: {(total_passed/(total_passed+total_failed)*100):.1f}%")
        print("=" * 60)