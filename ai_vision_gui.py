import os
import fitz  # PyMuPDF
import base64
import json
import re
import csv
import io
import shutil
import tkinter as tk
from tkinter import filedialog
from PIL import Image
from datetime import datetime
from ollama import Client

def get_directories():
    """Summons native macOS Finder windows to select Input and Output folders."""
    root = tk.Tk()
    root.withdraw() # Hides the blank background window
    root.attributes('-topmost', True) # Forces the popup to the front of your screen
    
    print("Waiting for you to select the SOURCE folder...")
    source_dir = filedialog.askdirectory(title="Select SOURCE Folder (Messy Files)")
    if not source_dir:
        print("No source folder selected. Exiting.")
        exit()
        
    print("Waiting for you to select the TARGET folder...")
    target_dir = filedialog.askdirectory(title="Select TARGET Folder (Clean Output)")
    if not target_dir:
        print("No target folder selected. Exiting.")
        exit()
        
    return source_dir, target_dir

def initialize_catalog(target_dir):
    """Creates the CSV ledger in the output folder."""
    catalog_file = os.path.join(target_dir, "document_catalog.csv")
    if not os.path.exists(catalog_file):
        with open(catalog_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Process_Timestamp", "Original_Filename", "New_Filename", "Execution_Date", "Document_Type"])
    return catalog_file

def pdf_pages_to_single_base64(pdf_path):
    """Takes a 'photograph' of the first and last pages and stitches them."""
    try:
        doc = fitz.open(pdf_path)
        pages_to_process = [0]
        
        if len(doc) > 1:
            pages_to_process.append(len(doc) - 1)
            
        unique_pages = []
        for p in pages_to_process:
            if p not in unique_pages:
                unique_pages.append(p)
                
        images = []
        for p in unique_pages:
            page = doc.load_page(p)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            images.append(img)
            
        if len(images) > 1:
            total_height = sum(img.height for img in images)
            max_width = max(img.width for img in images)
            composite = Image.new("RGB", (max_width, total_height))
            
            y_offset = 0
            for img in images:
                composite.paste(img, (0, y_offset))
                y_offset += img.height
            final_img = composite
        else:
            final_img = images[0]
            
        buffer = io.BytesIO()
        final_img.save(buffer, format="PNG")
        return [base64.b64encode(buffer.getvalue()).decode('utf-8')]
        
    except Exception as e:
        print(f"Error rendering PDF {pdf_path}: {e}")
        return None

def analyze_with_vision(b64_images):
    """Interrogates local Llama 3.2 Vision."""
    client = Client(host='http://localhost:11434')
    
    prompt = """
    You are an expert Florida real estate paralegal. Look at this image of a legal document (the first and last pages are stitched together).
    
    Extract two pieces of information:
    1. The final Execution or Notarization Date. Look closely at handwritten notary dates or stamps near the bottom. Convert this date strictly to the format: YYYY-MM-DD.
    2. A short, 3-to-4 word description of the Document Type (e.g., Warranty_Deed, Balloon_Mortgage, Sat_Mortgage). Use underscores instead of spaces.
    
    Return ONLY a valid JSON object. Do not include markdown formatting or explanations.
    Format: {"date": "YYYY-MM-DD", "doc_type": "Document_Type_Here"}
    """
    
    try:
        response = client.chat(model='llama3.2-vision', messages=[
            {'role': 'user', 'content': prompt, 'images': b64_images}
        ])
        raw_output = response['message']['content']
        
        match = re.search(r'\{.*?\}', raw_output, re.DOTALL)
        if match:
            clean_json = match.group(0)
            return json.loads(clean_json)
        else:
            print(f"Regex failed to find JSON in: {raw_output}")
            return None
            
    except Exception as e:
        print(f"Vision AI failed: {e}")
        return None

def log_to_catalog(catalog_file, old_name, new_name, exec_date, doc_type):
    """Appends the result to the CSV ledger."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(catalog_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, old_name, new_name, exec_date, doc_type])

def process_directory():
    # 1. Trigger the UI Popups
    source_dir, target_dir = get_directories()
    catalog_file = initialize_catalog(target_dir)
    
    print(f"\nMoving files from: {source_dir}")
    print(f"Saving cleaned files to: {target_dir}\n")
    
    for filename in os.listdir(source_dir):
        # The Non-PDF Shield: Safely ignores images, word docs, hidden files, etc.
        if not filename.lower().endswith(".pdf"):
            print(f"Skipping non-PDF file: {filename}")
            continue
            
        old_path = os.path.join(source_dir, filename)
        print(f"Analyzing: {filename}...")
        
        b64_images = pdf_pages_to_single_base64(old_path)
        if not b64_images:
            continue
            
        ai_data = analyze_with_vision(b64_images)
        
        if ai_data and "date" in ai_data and "doc_type" in ai_data:
            chrono_date = ai_data["date"]
            doc_type = ai_data["doc_type"]
            
            new_filename = f"{chrono_date}_{doc_type}.pdf"
            new_path = os.path.join(target_dir, new_filename)
            
            # Use shutil.move to safely transfer between different folders/drives
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
            print(f"FAILED: AI could not parse {filename}.\n")

if __name__ == "__main__":
    process_directory()
    print("Batch complete. CSV Catalog updated.")