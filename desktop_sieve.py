import os
import shutil
import subprocess
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
    heic_originals = triage_master / "Original_HEICs" # Safe storage for original iPhone photos

    # 2. Create the strict whitelist directories
    for directory in [docs_dir, img_dir, quarantine, existing_folders, heic_originals]:
        directory.mkdir(parents=True, exist_ok=True)

    # 3. Define AI-Digestible Extensions
    doc_exts = {'.pdf', '.docx', '.txt', '.csv', '.rtf', '.md', '.odt'}
    img_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    moved_count = 0
    converted_count = 0

    # 4. Execute the Sieve
    for item in desktop.iterdir():
        # Skip hidden files, the triage folder itself, and your new GitHub repo folder
        if item.name.startswith('.') or item.name == "Desktop_Triage" or item.name == "Desktop-Organization-ChowdhurySelfRep":
            continue

        # Handle Directories (e.g., SnowLeopard_Legal_Kit)
        if item.is_dir():
            shutil.move(str(item), str(existing_folders / item.name))
            moved_count += 1
            continue

        # Handle Files
        ext = item.suffix.lower()
        
        # --- NEW: HEIC Conversion Logic ---
        if ext == '.heic':
            # Define new JPG path
            new_jpg_name = item.stem + ".jpg"
            new_jpg_path = img_dir / new_jpg_name
            
            # Run macOS 'sips' command to seamlessly convert to JPEG
            print(f"Converting {item.name} to JPG...")
            subprocess.run(['sips', '-s', 'format', 'jpeg', str(item), '--out', str(new_jpg_path)], capture_output=True)
            
            # Move the original HEIC file to safe storage (no deletions!)
            shutil.move(str(item), str(heic_originals / item.name))
            converted_count += 1
            moved_count += 1
            continue
        # ----------------------------------

        # Handle Standard Files
        if ext in doc_exts:
            shutil.move(str(item), str(docs_dir / item.name))
        elif ext in img_exts:
            shutil.move(str(item), str(img_dir / item.name))
        else:
            # Outliers (e.g., .mov, .h, .dmg) go to Quarantine
            shutil.move(str(item), str(quarantine / item.name))
        
        moved_count += 1

    print(f"✅ Triage Complete! Organized {moved_count} items and converted {converted_count} HEIC photos.")

if __name__ == "__main__":
    triage_desktop()