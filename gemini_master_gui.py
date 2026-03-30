import os
import json
import re
import csv
import time
import shutil
import subprocess
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# --- 1. AUTHENTICATION ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("CRITICAL ERROR: Could not find GEMINI_API_KEY. Check your .env file.")
    exit()

client = genai.Client(api_key=api_key)

# --- 2. DIRECTORY ROUTING (GUI POPUPS) ---
def get_directories():
    """Summons native macOS Finder windows to select Source and Target folders."""
    print("[SYSTEM] Summoning native macOS folder selection...")
    
    def ask_mac_folder(prompt_text):
        script = f'set folderPath to choose folder with prompt "{prompt_text}"\nPOSIX path of folderPath'
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    source_dir = ask_mac_folder("Select SOURCE Folder (PDFs to process)")
    if not source_dir:
        print("No source folder selected. Exiting.")
        exit()
        
    target_dir = ask_mac_folder("Select TARGET Folder (Where the clean files & folders go)")
    if not target_dir:
        print("No target folder selected. Exiting.")
        exit()
        
    return source_dir, target_dir

# --- 3. CSV LEDGER ---
def initialize_catalog(target_dir):
    catalog_file = os.path.join(target_dir, "document_catalog_gemini.csv")
    if not os.path.exists(catalog_file):
        with open(catalog_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Process_Timestamp", "Original_Filename", "New_Filename", "Execution_Date", "Document_Type", "Storage_Path"])
    return catalog_file

def log_to_catalog(catalog_file, old_name, new_name, exec_date, doc_type, save_path):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(catalog_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, old_name, new_name, exec_date, doc_type, save_path])

# --- 4. GEMINI 2.5 FLASH ENGINE (JSON + OCR TEXT) ---
def analyze_pdf_with_gemini(pdf_path):
    """Uploads PDF, extracts JSON metadata AND full OCR text, handles 503 errors."""
    uploaded_file = None
    max_retries = 3
    retry_delay = 7  
    
    prompt = """
    You are an expert Florida real estate paralegal. Read this entire legal document natively.
    
    Provide the output in exactly two parts:
    PART 1: A JSON block containing the Date and Document Type.
    PART 2: The complete, raw OCR text transcript of the entire document.

    Extract two pieces of information for the JSON:
    1. The actual Execution Date or Notarization Date when the document was signed. WARNING: Do NOT extract the Notary Commission Expiration Date. Convert the actual execution date strictly to the format: YYYY-MM-DD.
    2. A short, 3-to-4 word description of the Document Type (e.g., Warranty_Deed, Balloon_Mortgage, Quit_Claim_Deed). Use underscores instead of spaces.
    
    Format your response EXACTLY like this:
    ```json
    {"date": "YYYY-MM-DD", "doc_type": "Document_Type_Here"}
    ```
    ---TEXT---
    [Insert the entire raw text of the document here]
    """

    try:
        uploaded_file = client.files.upload(file=pdf_path)
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[uploaded_file, prompt]
                )
                
                raw_output = response.text
                
                # Extract JSON
                match_json = re.search(r'\{.*?\}', raw_output, re.DOTALL)
                
                # Extract Full Text
                parts = raw_output.split("---TEXT---")
                full_text = parts[1].strip() if len(parts) > 1 else "No text extracted."
                
                if match_json:
                    clean_json = match_json.group(0)
                    ai_data = json.loads(clean_json)
                    ai_data["full_text"] = full_text 
                    return ai_data
                else:
                    print(f"   -> Regex failed to find JSON in response.")
                    return None 
                    
            except Exception as e:
                error_str = str(e)
                if "503" in error_str or "UNAVAILABLE" in error_str:
                    if attempt < max_retries - 1:
                        print(f"   -> API busy (503). Waiting {retry_delay} seconds to retry... (Attempt {attempt + 1} of {max_retries})")
                        time.sleep(retry_delay)
                    else:
                        print(f"   -> FAILED: Gemini could not parse after {max_retries} attempts.")
                        return None
                else:
                    print(f"   -> Gemini API failed unexpectedly: {error_str}")
                    return None
                    
    except Exception as upload_error:
         print(f"   -> Failed to upload file to Gemini: {upload_error}")
         return None
         
    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as e:
                print(f"   -> Failed to delete cloud file: {e}")

# --- 5. MAIN WORKFLOW ---
def process_directory():
    source_dir, target_dir = get_directories()
    if not source_dir or not target_dir:
        return
        
    catalog_file = initialize_catalog(target_dir)
    
    print(f"\nMoving files from: {source_dir}")
    print(f"Saving cleaned files to: {target_dir}\n")
    
    for filename in os.listdir(source_dir):
        if not filename.lower().endswith(".pdf"):
            continue

        old_path = os.path.join(source_dir, filename)
        print(f"Processing: {filename}")