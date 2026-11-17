import re

with open("CampusAssist_Project_Presentation.pdf", "rb") as f:
    data = f.read()

pages = re.findall(rb'/Type\s*/Page\b', data)
print(f"Presentation PDF Page Count (Regex): {len(pages)}")
assert len(pages) == 15, f"Expected 15 pages, got {len(pages)}"
print("[+] Verification passed: Exactly 15 slides/pages present in PDF!")

