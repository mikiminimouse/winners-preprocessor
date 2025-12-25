from docling.datamodel.document import DoclingDocument
try:
    attrs = dir(DoclingDocument)
    with open("docling_attrs.txt", "w") as f:
        f.write("\n".join(attrs))
    print("Attributes written to docling_attrs.txt")
except Exception as e:
    print(f"Error: {e}")
