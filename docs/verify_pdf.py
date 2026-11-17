import os

pdf_path = "CampusAssist_Project_Proposal.pdf"
docx_path = "CampusAssist_Project_Proposal.docx"
md_path = "CampusAssist_Project_Proposal.md"
status_path = "CampusAssist_Project_Status.md"

for p in [pdf_path, docx_path, md_path, status_path]:
    if os.path.exists(p):
        print(f"EXISTS: {p} ({os.path.getsize(p):,} bytes)")
    else:
        print(f"MISSING: {p}")

try:
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    print(f"PDF Page Count: {len(reader.pages)}")
except Exception as e:
    # Estimate from byte streams
    with open(pdf_path, 'rb') as f:
        data = f.read()
    import re
    count = len(re.findall(rb'/Type\s*/Page\b', data))
    print(f"PDF Page Count (raw regex): {count}")
