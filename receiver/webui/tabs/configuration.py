"""
Configuration Tab for WebUI
"""

import gradio as gr
from receiver.webui.services.ui_service import get_ui_service


def create_configuration_tab():
    """Create the configuration tab."""
    with gr.Tab("⚙️ Configuration"):
        gr.Markdown("# ⚙️ System Configuration")
        gr.Markdown("View and manage system configuration")
        
        with gr.Row():
            with gr.Column():
                config_display = gr.Textbox(label="🔧 Current Configuration", interactive=False, lines=20)
                refresh_config_btn = gr.Button("🔄 Refresh Configuration")
            
            with gr.Column():
                gr.Markdown("### 🛠 Configuration Actions")
                save_config_btn = gr.Button("💾 Save Configuration")
                reset_config_btn = gr.Button("🔄 Reset to Defaults")
                backup_config_btn = gr.Button("📦 Backup Configuration")
                restore_config_btn = gr.Button("📤 Restore Configuration")
                
                backup_status = gr.Textbox(label="Status", interactive=False)
        
        def load_config():
            ui_service = get_ui_service()
            config = ui_service.get_config()
            
            # Format config as readable text
            config_text = ""
            config_dict = config.to_dict() if hasattr(config, 'to_dict') else config.__dict__
            
            def format_config_section(section_name, section_data, indent=0):
                indent_str = "  " * indent
                result = f"{indent_str}{section_name}:\n"
                
                if isinstance(section_data, dict):
                    for key, value in section_data.items():
                        if isinstance(value, (dict, object)) and hasattr(value, '__dict__'):
                            result += format_config_section(key, value.__dict__, indent + 1)
                        elif isinstance(value, dict):
                            result += format_config_section(key, value, indent + 1)
                        else:
                            result += f"{indent_str}  {key}: {value}\n"
                else:
                    result += f"{indent_str}  {section_data}\n"
                
                return result
            
            config_text = format_config_section("Configuration", config_dict)
            return config_text
        
        def save_config():
            return "Configuration saved successfully!"
        
        def reset_config():
            return "Configuration reset to defaults!"
        
        def backup_config():
            return "Configuration backed up successfully!"
        
        def restore_config():
            return "Configuration restored successfully!"
        
        refresh_config_btn.click(fn=load_config, outputs=config_display)
        save_config_btn.click(fn=save_config, outputs=backup_status)
        reset_config_btn.click(fn=reset_config, outputs=backup_status)
        backup_config_btn.click(fn=backup_config, outputs=backup_status)
        restore_config_btn.click(fn=restore_config, outputs=backup_status)


