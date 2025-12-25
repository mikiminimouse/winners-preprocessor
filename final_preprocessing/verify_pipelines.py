import sys
import logging
from pathlib import Path
from docling_integration.runner import run_docling_conversion
from docling_integration.exporters.markdown import export_to_markdown

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add project root to sys.path
sys.path.insert(0, str(Path.cwd()))

def test_file(file_path):
    print(f"\n{'='*50}")
    print(f"Testing {file_path}...")
    try:
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return False
            
        print("Running conversion...")
        result = run_docling_conversion(file_path, check_limit=False)
        
        if not result:
            print(f"Conversion failed (returned None)")
            return False
        
        print("Conversion successful.")

        # Export to markdown
        output_md = Path(f"output_{file_path.name}.md")
        export_to_markdown(result, output_md)
        print(f"Exported to {output_md}")
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

# Define files to test
# Note: Using absolute paths or relative to cwd
files = [
    Path("sample.pptx"),
    Path("sample.xlsx"),
    Path("sample.xml"),
    # Search for the specific DOCX file we found earlier
    list(Path("Data/2025-03-20/Ready2Docling").rglob("*.docx"))[0] if list(Path("Data/2025-03-20/Ready2Docling").rglob("*.docx")) else Path("missing.docx"),
    # Search for the specific HTML file
    list(Path("Data/2025-03-20/Input").rglob("*.html"))[0] if list(Path("Data/2025-03-20/Input").rglob("*.html")) else Path("missing.html")
]

success_count = 0
for f in files:
    if test_file(f):
        success_count += 1

print(f"\n{'='*50}")
print(f"Total Success: {success_count}/{len(files)}")
