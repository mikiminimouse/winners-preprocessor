#!/usr/bin/env python3
"""
Test script to verify WebUI components initialization
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
receiver_path = project_root / "receiver"
sys.path.insert(0, str(receiver_path))
sys.path.insert(0, str(project_root))

def test_imports():
    """Test importing key components"""
    try:
        # Test config loading
        from receiver.core.config import load_env_file, get_config
        env_file = receiver_path / ".env"
        if env_file.exists():
            load_env_file(env_file)
            print("✅ Configuration loaded successfully")
        else:
            print("⚠️  .env file not found")
            
        config = get_config()
        print("✅ Config object loaded successfully")
        
        # Test VPN utilities
        from receiver.vpn_utils import get_vpn_status
        vpn_status = get_vpn_status()
        print(f"✅ VPN Status: {vpn_status['overall_status']}")
        
        # Test sync service
        from receiver.sync_db.enhanced_service import EnhancedSyncService
        sync_service = EnhancedSyncService()
        print("✅ Sync service initialized")
        
        # Test downloader service
        from receiver.downloader.enhanced_service import EnhancedProtocolDownloader
        downloader = EnhancedProtocolDownloader()
        print("✅ Downloader service initialized")
        
        # Test UI service
        from receiver.webui.services.ui_service import get_ui_service
        ui_service = get_ui_service()
        print("✅ UI service initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during import tests: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run component tests"""
    print("🧪 Testing WebUI Components...")
    success = test_imports()
    
    if success:
        print("\n🎉 All components initialized successfully!")
        return 0
    else:
        print("\n💥 Component initialization failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())