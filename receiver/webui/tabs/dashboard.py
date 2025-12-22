"""
Dashboard Tab for WebUI
"""

import gradio as gr
from datetime import datetime
from receiver.webui.services.ui_service import get_ui_service


def create_dashboard_tab():
    """Create the dashboard tab with system overview."""
    with gr.Tab("🏠 Dashboard"):
        gr.Markdown("# 📊 Dashboard")
        gr.Markdown("System overview and quick stats")
        
        with gr.Row():
            with gr.Column():
                vpn_status = gr.Textbox(label="🔒 VPN Status", interactive=False)
                system_status = gr.Textbox(label="⚙️ System Status", interactive=False)
            
            with gr.Column():
                last_sync = gr.Textbox(label="🔄 Last Sync", interactive=False)
                last_download = gr.Textbox(label="📥 Last Download", interactive=False)
        
        refresh_btn = gr.Button("🔄 Refresh Dashboard")
        
        def refresh_dashboard():
            ui_service = get_ui_service()
            
            # Get VPN status
            vpn_info = ui_service.get_vpn_status()
            vpn_status_text = f"Status: {vpn_info.get('status', 'Unknown')}\n"
            vpn_status_text += f"Interface: {vpn_info.get('interface', 'N/A')}\n"
            vpn_status_text += f"IP: {vpn_info.get('ip', 'N/A')}"
            
            # Get system status
            system_info = ui_service.get_system_status()
            system_status_text = f"CPU: {system_info.get('cpu_percent', 0):.1f}%\n"
            system_status_text += f"Memory: {system_info.get('memory_percent', 0):.1f}%\n"
            system_status_text += f"Disk: {system_info.get('disk_percent', 0):.1f}%"
            
            # Get last sync
            last_sync_info = ui_service.get_last_sync_info()
            last_sync_text = "Never" if not last_sync_info else str(last_sync_info)
            
            # Get last download
            last_download_info = ui_service.get_last_download_info()
            last_download_text = "Never" if not last_download_info else str(last_download_info)
            
            return (
                vpn_status_text,
                system_status_text,
                last_sync_text,
                last_download_text
            )
        
        refresh_btn.click(
            fn=refresh_dashboard,
            outputs=[vpn_status, system_status, last_sync, last_download]
        )


