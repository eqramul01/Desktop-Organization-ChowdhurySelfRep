import os
import shutil
from pathlib import Path

def triage_desktop():
    # 1. Define Paths
    desktop = Path.home() / "Desktop"
    triage_master = desktop / "Desktop_Triage"
    
    staging = triage_master / "AI_Staging_Ground"
    docs_dir = staging / "Documents"
    img_dir = staging / "Images"
    
    quarantine = triage_master / "Quarantine_Bin"
    existing_folders = triage_master / "Existing_Folders"

    # 2. Create the strict whitelist directories [cite: 784]
    for directory in [docs_dir, img_dir, quarantine, existing_folders]:
        directory.mkdir(parents=True, exist_ok=True)

    # 3. Define AI-Digestible Extensions 
    doc_exts = {'.pdf', '.docx', '.txt', '.csv', '.rtf', '.md', '.odt'}
    img_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    moved_count = 0

    # 4. Execute the Sieve
    for item in desktop.iterdir():
        # Skip hidden files and the triage folder itself
        if item.name.startswith('.') or item.name == "Desktop_Triage":
            continue

        # Handle Directories (e.g., SnowLeopard_Legal_Kit, Archive)
        if item.is_dir():
            shutil.move(str(item), str(existing_folders / item.name))
            moved_count += 1
            continue

        # Handle Files
        ext = item.suffix.lower()
        
        if ext in doc_exts:
            shutil.move(str(item), str(docs_dir / item.name))
        elif ext in img_exts:
            shutil.move(str(item), str(img_dir / item.name))
        else:
            # Outliers (e.g., .mov, .h, .dmg) go to Quarantine [cite: 807]
            shutil.move(str(item), str(quarantine / item.name))
        
        moved_count += 1

    print(f"✅ Triage Complete! Safely organized {moved_count} items into 'Desktop_Triage'.")

if __name__ == "__main__":
    triage_desktop()