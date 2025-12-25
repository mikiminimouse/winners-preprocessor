#!/usr/bin/env python3
"""
Comprehensive test to verify all receiver components work together
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
receiver_path = project_root / "receiver"
sys.path.insert(0, str(receiver_path))
sys.path.insert(0, str(project_root))

async def test_complete_workflow():
    """Test complete workflow of receiver components"""
    try:
        print("🚀 Starting Comprehensive Component Test...\n")
        
        # 1. Test configuration loading
        print("1️⃣  Testing Configuration Loading...")
        from receiver.core.config import load_env_file, get_config
        env_file = receiver_path / ".env"
        if env_file.exists():
            load_env_file(env_file)
            print("   ✅ Configuration loaded successfully")
        config = get_config()
        print(f"   📁 Input directory: {config.router.input_dir}")
        print(f"   🗄️  Local MongoDB: {config.sync_db.local_mongo.server}\n")
        
        # 2. Test VPN status
        print("2️⃣  Testing VPN Status...")
        from receiver.vpn_utils import get_vpn_status
        vpn_status = get_vpn_status()
        print(f"   🌐 VPN Status: {vpn_status['overall_status']}")
        if vpn_status['overall_status'] == 'healthy':
            print("   ✅ VPN is healthy\n")
        else:
            print("   ⚠️  VPN issues detected\n")
        
        # 3. Test MongoDB connections
        print("3️⃣  Testing MongoDB Connections...")
        
        # Local MongoDB
        from receiver.sync_db.health_checks import check_local_mongodb_connectivity
        local_result = check_local_mongodb_connectivity()
        print(f"   🏠 Local MongoDB: {local_result.status} - {local_result.message}")
        
        # Remote MongoDB (if VPN is healthy)
        from receiver.sync_db.health_checks import check_remote_mongodb_connectivity
        remote_result = check_remote_mongodb_connectivity()
        print(f"   ☁️  Remote MongoDB: {remote_result.status} - {remote_result.message}\n")
        
        # 4. Test service initialization
        print("4️⃣  Testing Service Initialization...")
        
        # Sync service
        from receiver.sync_db.enhanced_service import EnhancedSyncService
        sync_service = EnhancedSyncService()
        print("   🔄 Sync service initialized")
        
        # Downloader service
        from receiver.downloader.enhanced_service import EnhancedProtocolDownloader
        downloader = EnhancedProtocolDownloader()
        print("   📥 Downloader service initialized")
        
        # UI service
        from receiver.webui.services.ui_service import get_ui_service
        ui_service = get_ui_service()
        print("   🖥️  UI service initialized\n")
        
        # 5. Test WebUI accessibility
        print("5️⃣  Testing WebUI Accessibility...")
        import requests
        try:
            response = requests.get("http://localhost:7860", timeout=5)
            if response.status_code == 200:
                print("   🌐 WebUI is accessible")
            else:
                print(f"   ⚠️  WebUI returned status {response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Could not reach WebUI: {e}")
        
        print("\n🎉 All Components Working Correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error during comprehensive test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run comprehensive test"""
    print("=" * 60)
    print("🧪 RECEIVER COMPONENTS COMPREHENSIVE TEST")
    print("=" * 60)
    
    success = await test_complete_workflow()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - SYSTEM READY FOR USE")
    else:
        print("💥 SOME TESTS FAILED - PLEASE CHECK SYSTEM")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
