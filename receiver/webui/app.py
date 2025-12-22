"""
Main Gradio WebUI Application
Assembles UI from modular components
"""

import os
import sys
import gradio as gr
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
from receiver.core.config import load_env_file, get_config
env_file = project_root / ".env"
if env_file.exists():
    load_env_file(env_file)
    logger.info(f"✅ Loaded configuration from {env_file}")
else:
    logger.warning(f"⚠️  .env file not found: {env_file}")

config = get_config()

# Import UI components
from receiver.webui.tabs.dashboard import create_dashboard_tab
from receiver.webui.tabs.sync_control import create_sync_control_tab
from receiver.webui.tabs.sync_manager import create_sync_manager_tab
from receiver.webui.tabs.download_control import create_download_control_tab
from receiver.webui.tabs.health_check import create_health_check_tab
from receiver.webui.tabs.configuration import create_configuration_tab

# Import services
from receiver.webui.services.ui_service import get_ui_service

def initialize_services():
    """Initialize all required services."""
    try:
        ui_service = get_ui_service()
        logger.info("✅ UI services initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize UI services: {e}")
        return False

def main():
    """Main application entry point."""
    # Initialize services
    if not initialize_services():
        logger.error("❌ Failed to initialize services")
        return
    
    # Create Gradio interface
    with gr.Blocks(title="Receiver Control Panel", theme=gr.themes.Default()) as demo:
        gr.Markdown("# 🎛 Receiver Control Panel")
        gr.Markdown("Unified interface for managing receiver components")
        
        # Create tabs
        create_dashboard_tab()
        create_sync_control_tab()
        create_sync_manager_tab()
        create_download_control_tab()
        create_health_check_tab()
        create_configuration_tab()
    
    # Launch the app
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        quiet=False
    )

if __name__ == "__main__":
    main()