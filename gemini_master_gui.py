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

# Initialize the NEW Google GenAI Client
client = genai.Client(api_key=api_key)

# --- 2. GUI ROUTING ---
def get_directories():
    """Summons native macOS Finder windows using AppleScript."""
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

# --- 3. CSV LEDGER ---
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

# --- 4. GEMINI 1.5 FLASH ENGINE (NEW SDK) ---
def analyze_pdf_with_gemini(pdf_path):
    """Uploads PDF via new SDK, extracts JSON, and securely deletes the file."""
    uploaded_file = None
    try:
        # New SDK Upload Syntax
        uploaded_file = client.files.upload(file=pdf_path)
        
        prompt = """
        You are an expert Florida real estate paralegal. Read this entire legal document natively.
        
        Extract two pieces of information:
        1. The actual Execution Date or Notarization Date when the document was signed. WARNING: Do NOT extract the Notary Commission Expiration Date. Look for phrases like "Made this", "Signed", or "Acknowledged before me". Convert the actual execution date strictly to the format: YYYY-MM-DD.
        2. A short, 3-to-4 word description of the Document Type (e.g., Warranty_Deed, Balloon_Mortgage, Quit_Claim_Deed, Order_Rescheduling_Sale). Use underscores instead of spaces.
        
        Return ONLY a valid JSON object. Do not include markdown formatting or explanations.
        Format: {"date": "YYYY-MM-DD", "doc_type": "Document_Type_Here"}
        """
        
        # New SDK Generation Syntax
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt]
        )
        
        raw_output = response.text
        
        # Regex to catch the JSON perfectly
        match = re.search(r'\{.*?\}', raw_output, re.DOTALL)
        if match:
            clean_json = match.group(0)
            return json.loads(clean_json)
        else:
            print(f"Regex failed to find JSON in: {raw_output}")
            return None
            
    except Exception as e:
        print(f"Gemini API failed: {e}")
        return None
        
    finally:
        # Strict Cloud Hygiene: Delete the file from Google's servers immediately
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as e:
                print(f"Failed to delete cloud file: {e}")

# --- 5. MAIN WORKFLOW ---
def process_directory():
    source_dir, target_dir = get_directories()
    catalog_file = initialize_catalog(target_dir)
    
    print(f"\nMoving files from: {source_dir}")
    print(f"Saving cleaned files to: {target_dir}\n")
    
    for filename in os.listdir(source_dir):
        if not filename.lower().endswith(".pdf"):
            continue

        old_path = os.path.join(source_dir, filename)
        print(f"Analyzing with Gemini: {filename}...")
        
        ai_data = analyze_pdf_with_gemini(old_path)
        
        if ai_data and "date" in ai_data and "doc_type" in ai_data:
            chrono_date = ai_data["date"]
            doc_type = ai_data["doc_type"]
            
            new_filename = f"{chrono_date}_{doc_type}.pdf"
            new_path = os.path.join(target_dir, new_filename)
            
            if not os.path.exists(new_path):
                shutil.move(old_path, new_path)
                log_to_catalog(catalog_file, filename, new_filename, chrono_date, doc_type)
                print(f"SUCCESS: -> {new_filename}\n")
            else:
                alt_filename = f"{chrono_date}_{doc_type}_2.pdf"
                shutil.move(old_path, os.path.join(target_dir, alt_filename))
                log_to_catalog(catalog_file, filename, alt_filename, chrono_date, doc_type)
                print(f"SUCCESS (Duplicate Date): -> {alt_filename}\n")
        else:
            print(f"FAILED: Gemini could not parse {filename}.\n")
            
        time.sleep(3) # Rate limit protection

if __name__ == "__main__":
    process_directory()
    print("\nBatch complete. CSV Catalog updated.")