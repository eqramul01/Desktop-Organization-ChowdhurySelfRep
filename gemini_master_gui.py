import os
import json
import re
import csv
import time
import shutil
import tempfile
import subprocess
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# Professional Imaging Libraries
from PIL import Image
from pillow_heif import register_heif_opener

# Enable Apple HEIC support
register_heif_opener()

# --- 1. AUTHENTICATION ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("CRITICAL ERROR: Could not find GEMINI_API_KEY. Check your .env file.")
    exit()

client = genai.Client(api_key=api_key)
SUPPORTED_EXTS = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.heic']

# --- 2. GUI ROUTING ---
def get_directories():
    print("[SYSTEM] Summoning native macOS folder selection...")
    def ask_mac_folder(prompt_text):
        script = f'set folderPath to choose folder with prompt "{prompt_text}"\nPOSIX path of folderPath'
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    source_dir = ask_mac_folder("Select SOURCE Folder (The badly named files)")
    if not source_dir:
        print("No source folder selected. Exiting.")
        exit()
        
    target_dir = ask_mac_folder("Select TARGET Folder (Where the clean files go)")
    if not target_dir:
        print("No target folder selected. Exiting.")
        exit()
        
    return source_dir, target_dir

# --- 3. SANITIZATION & GHOST UPLOAD ---
def sanitize_text(text):
    """Replaces slashes and illegal characters to prevent folder creation crashes."""
    if not text or text == "N/A":
        return "Unknown"
    # Replace slashes, colons, backslashes with dashes
    clean = re.sub(r'[\\/*?:"<>|]', '-', str(text))
    return clean.strip()

def prepare_safe_upload(file_path):
    """
    Creates a strictly ASCII-named temporary copy for the Google SDK.
    This permanently fixes crashes caused by dashes, smart quotes, or emojis in filenames.
    Converts TIFF/HEIC to PDF for Gemini.
    """
    ext = os.path.splitext(file_path)[1].lower()
    temp_dir = tempfile.gettempdir()
    # Create a safe, random ASCII filename
    safe_filename = f"safe_upload_{int(time.time() * 1000)}"
    
    if ext in ['.tiff', '.tif', '.heic']:
        print(f"   -> [SYSTEM] Converting {ext.upper()} to temporary PDF...")
        temp_path = os.path.join(temp_dir, safe_filename + ".pdf")
        try:
            image = Image.open(file_path)
            images = []
            if getattr(image, "is_animated", False) or hasattr(image, "n_frames"):
                for i in range(image.n_frames):
                    image.seek(i)
                    images.append(image.convert("RGB"))
            else:
                images.append(image.convert("RGB"))
                
            images[0].save(temp_path, save_all=True, append_images=images[1:])
            return temp_path
        except Exception as e:
            print(f"   -> [ERROR] Image conversion failed: {e}")
            return None
    else:
        # For PDF, JPG, PNG: Just make a safe-named copy
        temp_path = os.path.join(temp_dir, safe_filename + ext)
        shutil.copy2(file_path, temp_path)
        return temp_path

# --- 4. GEMINI 2.5 FLASH DUAL-ENGINE ---
def analyze_and_extract(file_path):
    """Uploads once, asks Gemini for JSON Metadata AND Full OCR Text."""
    upload_path = prepare_safe_upload(file_path)
    if not upload_path:
        return None, None
        
    uploaded_file = None
    try:
        uploaded_file = client.files.upload(file=upload_path)
        
        # 1. Extract Metadata
        prompt_meta = """
        You are an expert Florida paralegal. Read this entire document natively.
        Extract:
        1. Execution Date (YYYY-MM-DD). If none, use "Unknown_Date". Do NOT output slashes.
        2. Document Type (3-4 words, use underscores).
        Return ONLY valid JSON: {"date": "YYYY-MM-DD", "doc_type": "Doc_Type"}
        """
        res_meta = client.models.generate_content(model='gemini-2.5-flash', contents=[uploaded_file, prompt_meta])
        
        # 2. Extract Full OCR Text for RAG
        prompt_text = "Extract 100% of the raw text from this document accurately. Preserve formatting. Do not summarize."
        res_text = client.models.generate_content(model='gemini-2.5-flash', contents=[uploaded_file, prompt_text])
        
        ai_data = None
        match = re.search(r'\{.*?\}', res_meta.text, re.DOTALL)
        if match:
            ai_data = json.loads(match.group(0))
            
        return ai_data, res_text.text
            
    except Exception as e:
        print(f"   -> [ERROR] Gemini API failed: {e}")
        return None, None
        
    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except:
                pass
        if upload_path and os.path.exists(upload_path):
            os.remove(upload_path)

# --- 5. CSV LEDGER ---
def initialize_catalog(target_dir):
    catalog_file = os.path.join(target_dir, "document_catalog_gemini.csv")
    if not os.path.exists(catalog_file):
        with open(catalog_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Process_Timestamp", "Original_Filename", "New_Filename", "Execution_Date", "Document_Type"])
    return catalog_file

def log_to_catalog(catalog_file, old_name, new_name, exec_date, doc_type):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(catalog_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, old_name, new_name, exec_date, doc_type])

# --- 6. MAIN WORKFLOW ---
def process_directory():
    source_dir, target_dir = get_directories()
    catalog_file = initialize_catalog(target_dir)
    
    print(f"\nMoving files from: {source_dir}")
    print(f"Saving cleaned files to: {target_dir}\n")
    
    files_to_process = [f for f in os.listdir(source_dir) if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS]
    
    for filename in files_to_process:
        ext = os.path.splitext(filename)[1].lower()
        old_path = os.path.join(source_dir, filename)
        
        print(f"\nProcessing: {filename}")
        ai_data, extracted_text = analyze_and_extract(old_path)
        
        if ai_data and "date" in ai_data and "doc_type" in ai_data:
            # Sanitize to prevent "N/A" slash crashes
            chrono_date = sanitize_text(ai_data["date"])
            doc_type = sanitize_text(ai_data["doc_type"])
            
            # Determine Year Folder
            year_match = re.match(r'^(\d{4})', chrono_date)
            year_folder = year_match.group(1) if year_match else "Unknown_Year"
            
            # Create Year Directory if it doesn't exist
            year_dir_path = os.path.join(target_dir, year_folder)
            os.makedirs(year_dir_path, exist_ok=True)
            
            # Determine final file paths
            new_filename = f"{chrono_date}_{doc_type}{ext}"
            new_path = os.path.join(year_dir_path, new_filename)
            
            # Handle duplicates gracefully
            if os.path.exists(new_path):
                new_filename = f"{chrono_date}_{doc_type}_2{ext}"
                new_path = os.path.join(year_dir_path, new_filename)
                
            txt_path = os.path.join(year_dir_path, f"{os.path.splitext(new_filename)[0]}.txt")
            
            # 1. Move Original File
            shutil.move(old_path, new_path)
            
            # 2. Write Text File for RAG
            if extracted_text:
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
            
            log_to_catalog(catalog_file, filename, new_filename, chrono_date, doc_type)
            print(f"SUCCESS: Saved to /{year_folder}/ {new_filename} (+ .txt)")
            
        else:
            print(f"FAILED: Could not parse {filename}.")
            
        time.sleep(5) # Protects Google API Rate Limits

if __name__ == "__main__":
    process_directory()
    print("\nBatch complete. CSV Catalog updated.")