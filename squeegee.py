import os
import time
import subprocess
from google import genai
from dotenv import load_dotenv

# --- 1. AUTHENTICATION ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("CRITICAL ERROR: Could not find GEMINI_API_KEY. Check your .env file.")
    exit()

# Using the new SDK client
client = genai.Client(api_key=api_key)

# --- 2. GUI ROUTING ---
def get_directory():
    """Summons native macOS Finder window using AppleScript."""
    print("[SYSTEM] Summoning native macOS folder selection...")
    script = 'set folderPath to choose folder with prompt "Select the folder with your CLEANED PDFs"\nPOSIX path of folderPath'
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

# --- 3. GEMINI 2.5 FLASH OCR ENGINE ---
def extract_text_with_gemini(pdf_path):
    """Uploads PDF, extracts all raw text natively, and securely deletes the file."""
    uploaded_file = None
    try:
        print(f"   -> Uploading {os.path.basename(pdf_path)} to secure cloud...")
        uploaded_file = client.files.upload(file=pdf_path)
        
        prompt = """
        You are an expert legal data extraction system. Read this entire document.
        Extract 100% of the text accurately. 
        Preserve formatting, paragraphs, lists, and tables as best as possible.
        Do not summarize, do not add commentary, and do not use markdown code blocks.
        Output ONLY the raw text found in the document.
        """
        
        print("   -> Running full-document OCR via Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt]
        )
        
        return response.text
            
    except Exception as e:
        print(f"   -> [ERROR] Gemini API failed: {e}")
        return None
        
    finally:
        # Strict Cloud Hygiene: Immediately delete the file from Google's servers
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as e:
                print(f"   -> [WARNING] Failed to delete cloud file: {e}")

# --- 4. MAIN WORKFLOW ---
def process_directory():
    target_dir = get_directory()
    if not target_dir:
        print("No folder selected. Exiting.")
        return

    print(f"\nTargeting folder: {target_dir}\n")
    
    # Grab all PDFs in the folder
    pdf_files = [f for f in os.listdir(target_dir) if f.lower().endswith(".pdf")]
    
    for filename in pdf_files:
        pdf_path = os.path.join(target_dir, filename)
        base_name = os.path.splitext(filename)[0]
        txt_path = os.path.join(target_dir, f"{base_name}.txt")
        
        # Prevents you from double-billing the API if a text file already exists
        if os.path.exists(txt_path):
            print(f"Skipping: {filename} (Text file already exists)")
            continue

        print(f"\nProcessing: {filename}")
        extracted_text = extract_text_with_gemini(pdf_path)
        
        if extracted_text:
            with open(txt_path, 'w', encoding='utf-8') as txt_file:
                txt_file.write(extracted_text)
            print(f"SUCCESS: Created sibling file -> {base_name}.txt")
        else:
            print(f"FAILED: Could not extract text for {filename}.")
            
        # A 3-second delay prevents API rate-limiting on the free tier
        time.sleep(7)

if __name__ == "__main__":
    process_directory()
    print("\nSqueegee extraction complete. Files are ready for local RAG vectorization.")