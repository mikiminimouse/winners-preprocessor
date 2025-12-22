"""
Health Check Tab for WebUI
"""

import gradio as gr
from receiver.webui.services.ui_service import get_ui_service


def create_health_check_tab():
    """Create the health check tab."""
    with gr.Tab("🏥 Health Check"):
        gr.Markdown("# 🏥 Health Check")
        gr.Markdown("Comprehensive system health monitoring")
        
        with gr.Row():
            with gr.Column():
                vpn_check = gr.Textbox(label="🔒 VPN Connection", interactive=False, lines=3)
                mongodb_check = gr.Textbox(label="🍃 MongoDB Connection", interactive=False, lines=3)
                zakupki_check = gr.Textbox(label="🌐 Zakupki.gov.ru Access", interactive=False, lines=3)
            
            with gr.Column():
                disk_space = gr.Textbox(label="💾 Disk Space", interactive=False, lines=3)
                memory_usage = gr.Textbox(label="🧠 Memory Usage", interactive=False, lines=3)
                cpu_usage = gr.Textbox(label="⚙️ CPU Usage", interactive=False, lines=3)
        
        run_health_check_btn = gr.Button("🔍 Run Health Check", variant="primary")
        health_results = gr.Textbox(label="📋 Detailed Results", interactive=False, lines=10)
        
        def run_health_check():
            ui_service = get_ui_service()
            health_results = ui_service.run_health_check()
            
            # Format individual checks
            vpn_status = f"Status: {health_results.get('vpn', {}).get('status', 'Unknown')}\n"
            vpn_status += f"Details: {health_results.get('vpn', {}).get('details', '')}"
            
            mongodb_status = f"Status: {health_results.get('mongodb', {}).get('status', 'Unknown')}\n"
            mongodb_status += f"Details: {health_results.get('mongodb', {}).get('details', '')}"
            
            zakupki_status = f"Status: {health_results.get('zakupki', {}).get('status', 'Unknown')}\n"
            zakupki_status += f"Details: {health_results.get('zakupki', {}).get('details', '')}"
            
            disk_status = f"Status: {health_results.get('disk', {}).get('status', 'Unknown')}\n"
            disk_status += f"Used: {health_results.get('disk', {}).get('used_percent', 0):.1f}%"
            
            memory_status = f"Status: {health_results.get('memory', {}).get('status', 'Unknown')}\n"
            memory_status += f"Used: {health_results.get('memory', {}).get('used_percent', 0):.1f}%"
            
            cpu_status = f"Status: {health_results.get('cpu', {}).get('status', 'Unknown')}\n"
            cpu_status += f"Load: {health_results.get('cpu', {}).get('load_average', 0):.2f}"
            
            # Format detailed results
            detailed_results = ""
            for check_name, check_result in health_results.items():
                detailed_results += f"{check_name.upper()}:\n"
                for key, value in check_result.items():
                    detailed_results += f"  {key}: {value}\n"
                detailed_results += "\n"
            
            return (
                vpn_status,
                mongodb_status,
                zakupki_status,
                disk_status,
                memory_status,
                cpu_status,
                detailed_results
            )
        
        run_health_check_btn.click(
            fn=run_health_check,
            inputs=[],
            outputs=[
                vpn_check,
                mongodb_check,
                zakupki_check,
                disk_space,
                memory_usage,
                cpu_usage,
                health_results
            ]
        )


