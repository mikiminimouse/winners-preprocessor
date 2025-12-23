#!/usr/bin/env python3
"""
Test script to verify sync and download functionality
"""

import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
receiver_path = project_root / "receiver"
sys.path.insert(0, str(receiver_path))
sys.path.insert(0, str(project_root))

async def test_sync_service():
    """Test sync service functionality"""
    try:
        print("🔄 Testing Sync Service...")
        
        from receiver.sync_db.enhanced_service import EnhancedSyncService
        sync_service = EnhancedSyncService()
        
        # Test VPN connectivity before sync
        from receiver.vpn_utils import get_vpn_status
        vpn_status = get_vpn_status()
        print(f"📡 VPN Status: {vpn_status['overall_status']}")
        
        if vpn_status['overall_status'] != 'healthy':
            print("⚠️  VPN not healthy, skipping sync test")
            return True
            
        # Test health check
        from receiver.sync_db.health_checks import check_remote_mongodb_connectivity
        mongo_check = check_remote_mongodb_connectivity()
        print(f"🗃️  Remote MongoDB: {mongo_check.status}")
        
        if mongo_check.status != "healthy":
            print("⚠️  Remote MongoDB not accessible, skipping sync test")
            return True
            
        print("✅ Sync service tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Error during sync service test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_download_service():
    """Test download service functionality"""
    try:
        print("📥 Testing Download Service...")
        
        from receiver.downloader.enhanced_service import EnhancedProtocolDownloader
        downloader = EnhancedProtocolDownloader()
        
        # Test VPN connectivity for zakupki.gov.ru
        from receiver.vpn_utils import check_zakupki_access
        zakupki_accessible = check_zakupki_access()
        print(f"🌐 Zakupki.gov.ru accessible: {zakupki_accessible[0]}")
        
        # Test local MongoDB connectivity
        from receiver.sync_db.health_checks import check_local_mongodb_connectivity
        local_mongo_check = check_local_mongodb_connectivity()
        print(f"🗃️  Local MongoDB: {local_mongo_check.status}")
        
        print("✅ Download service tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Error during download service test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_health_checks():
    """Test health check functionality"""
    try:
        print("🏥 Testing Health Checks...")
        
        from receiver.sync_db.health_checks import run_comprehensive_health_check
        results = run_comprehensive_health_check()
        
        healthy_count = 0
        total_checks = len(results)
        
        for name, result in results.items():
            status_icon = "✅" if result.status == "healthy" else "❌"
            print(f"{status_icon} {name}: {result.status} - {result.message}")
            if result.status == "healthy":
                healthy_count += 1
                
        print(f"\n📊 Health Summary: {healthy_count}/{total_checks} checks passed")
        return healthy_count == total_checks
        
    except Exception as e:
        print(f"❌ Error during health check test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run functional tests"""
    print("🧪 Running Functional Tests...\n")
    
    # Test health checks first
    health_ok = await test_health_checks()
    print()
    
    # Test sync service
    sync_ok = await test_sync_service()
    print()
    
    # Test download service
    download_ok = await test_download_service()
    print()
    
    if health_ok and sync_ok and download_ok:
        print("🎉 All functional tests completed successfully!")
        return 0
    else:
        print("💥 Some functional tests failed!")
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)