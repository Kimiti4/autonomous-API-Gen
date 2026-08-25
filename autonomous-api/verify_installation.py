"""
Quick verification script to check all production hardening components.
Run this before deployment to ensure everything is properly configured.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def check_file_exists(filepath, description):
    """Check if a file exists"""
    full_path = project_root / filepath
    if full_path.exists():
        size = full_path.stat().st_size
        print(f"✅ {description}: {filepath} ({size:,} bytes)")
        return True
    else:
        print(f"❌ {description}: {filepath} - MISSING")
        return False


def check_import(module_path, description):
    """Check if a module can be imported"""
    try:
        __import__(module_path)
        print(f"✅ {description}: {module_path}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_path} - {e}")
        return False


def main():
    print("\n" + "="*60)
    print("  PRODUCTION HARDENING VERIFICATION")
    print("="*60)
    
    results = []
    
    # Check core files
    print_section("1. Core Components")
    
    results.append(check_file_exists(
        "app/core/config.py",
        "Configuration module"
    ))
    results.append(check_file_exists(
        "app/core/logger.py",
        "Logger configuration"
    ))
    results.append(check_file_exists(
        "app/core/error_handler.py",
        "Error handling utilities"
    ))
    
    # Check middleware
    print_section("2. Middleware")
    
    results.append(check_file_exists(
        "app/middleware/__init__.py",
        "Middleware package init"
    ))
    results.append(check_file_exists(
        "app/middleware/rate_limit.py",
        "Rate limiting middleware"
    ))
    results.append(check_file_exists(
        "app/middleware/security.py",
        "Security headers middleware"
    ))
    
    # Check schemas
    print_section("3. Validation Schemas")
    
    results.append(check_file_exists(
        "app/schemas/__init__.py",
        "Schemas package init"
    ))
    results.append(check_file_exists(
        "app/schemas/evolution.py",
        "Evolution validation models"
    ))
    
    # Check updated files
    print_section("4. Updated Files")
    
    results.append(check_file_exists(
        "app/main.py",
        "Main application (with middleware)"
    ))
    results.append(check_file_exists(
        "app/api/routes.py",
        "API routes (with validation)"
    ))
    
    # Check documentation
    print_section("5. Documentation")
    
    results.append(check_file_exists(
        "FINAL_SUMMARY.md",
        "Final summary guide"
    ))
    results.append(check_file_exists(
        "IMPLEMENTATION_COMPLETE.md",
        "Implementation details"
    ))
    results.append(check_file_exists(
        "PRODUCTION_HARDENING.md",
        "Production hardening guide"
    ))
    results.append(check_file_exists(
        "DEPLOYMENT_GUIDE.md",
        "Deployment instructions"
    ))
    results.append(check_file_exists(
        "CHECKLIST_COMPLETE.md",
        "Completion checklist"
    ))
    
    # Check test suite
    print_section("6. Testing")
    
    results.append(check_file_exists(
        "test_production.py",
        "Automated test suite"
    ))
    
    # Test imports
    print_section("7. Import Verification")
    
    results.append(check_import(
        "app.core.config",
        "Configuration"
    ))
    results.append(check_import(
        "app.core.logger",
        "Logger"
    ))
    results.append(check_import(
        "app.core.error_handler",
        "Error handler"
    ))
    results.append(check_import(
        "app.middleware.rate_limit",
        "Rate limiter"
    ))
    results.append(check_import(
        "app.middleware.security",
        "Security middleware"
    ))
    results.append(check_import(
        "app.schemas.evolution",
        "Validation schemas"
    ))
    
    # Check dependencies
    print_section("8. Dependencies")
    
    dependencies = [
        ("loguru", "Logging"),
        ("pydantic", "Validation"),
        ("pydantic_settings", "Configuration"),
        ("psutil", "System monitoring"),
        ("fastapi", "Web framework"),
    ]
    
    for package, description in dependencies:
        try:
            __import__(package)
            print(f"✅ {description}: {package}")
            results.append(True)
        except ImportError:
            print(f"❌ {description}: {package} - NOT INSTALLED")
            results.append(False)
    
    # Check directories
    print_section("9. Directory Structure")
    
    required_dirs = [
        "logs",
        "app/core",
        "app/middleware",
        "app/schemas",
        "app/api",
        "app/engine",
        "app/storage",
    ]
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"✅ {dir_path}/")
            results.append(True)
        else:
            print(f"❌ {dir_path}/ - MISSING")
            results.append(False)
    
    # Summary
    print_section("VERIFICATION SUMMARY")
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"\nTotal checks: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    
    if failed == 0:
        print("\n🎉 All checks passed! System is ready for deployment.")
        print("\nNext steps:")
        print("  1. Review DEPLOYMENT_GUIDE.md for deployment instructions")
        print("  2. Run: python test_production.py to test all features")
        print("  3. Start server: uvicorn app.main:app --reload")
        print("  4. Access docs: http://localhost:8000/docs")
        return True
    else:
        print(f"\n⚠️ {failed} check(s) failed. Please review the issues above.")
        print("\nTo fix missing dependencies:")
        print("  pip install loguru pydantic-settings psutil")
        print("\nTo create missing directories:")
        print("  mkdir logs")
        return False


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
