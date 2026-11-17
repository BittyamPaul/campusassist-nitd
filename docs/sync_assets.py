import shutil
from pathlib import Path

src_dir = Path("docs/proposal_assets")
dst_dir = Path("CampusAssist_Presentation_Assets")
dst_dir.mkdir(parents=True, exist_ok=True)

if src_dir.exists():
    for f in src_dir.glob("*.png"):
        shutil.copy2(f, dst_dir / f.name)
        print(f"Copied {f.name} -> {dst_dir}")

print("Assets synced to CampusAssist_Presentation_Assets!")

