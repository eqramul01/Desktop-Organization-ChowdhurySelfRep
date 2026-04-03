import os
import time
import json
import re
import csv
import shutil
import tempfile
import threading
import concurrent.futures
import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
from google import genai
from PIL import Image
from pillow_heif import register_heif_opener

# Enable Apple HEIC support & Set GUI Theme
register_heif_opener()
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

SUPPORTED_EXTS = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.heic']
CONFIG_FILE = os.path.expanduser("~/.legal_sorter_api_key.txt")

# Worker Pool: Set to 2-3 for Free Tier, 10-15 for Paid Tier
MAX_CONCURRENT_WORKERS = 3

class LegalSorterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Legal Document Sorter (Multi-Threaded)")
        self.geometry("750x700")
        
        self.source_dir = ""
        self.target_dir = ""
        self.csv_lock = threading.Lock()
        
        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 1. Folder Selection Frame
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.frame_top.grid_columnconfigure(1, weight=1)

        self.btn_source = ctk.CTkButton(self.frame_top, text="Select Master Source Folder", command=self.select_source)
        self.btn_source.grid(row=0, column=0, padx=10, pady=10)
        self.lbl_source = ctk.CTkLabel(self.frame_top, text="No folder selected", text_color="gray")
        self.lbl_source.grid(row=0, column=1, sticky="w")

        self.btn_target = ctk.CTkButton(self.frame_top, text="Select Target (Clean) Folder", command=self.select_target)
        self.btn_target.grid(row=1, column=0, padx=10, pady=10)
        self.lbl_target = ctk.CTkLabel(self.frame_top, text="No folder selected", text_color="gray")
        self.lbl_target.grid(row=1, column=1, sticky="w")

        # 2. API Key Frame
        self.frame_api = ctk.CTkFrame(self)
        self.frame_api.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.frame_api.grid_columnconfigure(1, weight=1)

        self.lbl_api = ctk.CTkLabel(self.frame_api, text="Gemini API Key:", font=ctk.CTkFont(weight="bold"))
        self.lbl_api.grid(row=0, column=0, padx=10, pady=10)

        self.entry_api = ctk.CTkEntry(self.frame_api, show="*", placeholder_text="Paste your AIzaSy... key here")
        self.entry_api.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.btn_save_api = ctk.CTkButton(self.frame_api, text="Save Key", width=100, command=self.save_api_key)
        self.btn_save_api.grid(row=0, column=2, padx=10, pady=10)

        self.load_api_key()

        # 3. Action Button & Telemetry Readout
        self.btn_run = ctk.CTkButton(self, text=f"▶ Run Swarm Engine ({MAX_CONCURRENT_WORKERS} Bots)", font=ctk.CTkFont(size=15, weight="bold"), height=40, command=self.start_processing_thread)
        self.btn_run.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")

        # Live Telemetry Tracker
        self.lbl_progress = ctk.CTkLabel(self, text="Awaiting Task...", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2FA572")
        self.lbl_progress.grid(row=3, column=0, pady=(0, 10))

        # 4. Live Console Readout
        self.console = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Courier", size=12))
        self.console.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_message("System Ready. Please select folders to begin.\n")

    # --- GUI LOGIC ---
    def save_api_key(self):
        key = self.entry_api.get().strip()
        if key:
            with open(CONFIG_FILE, "w") as f:
                f.write(key)
            self.log_message("[SYSTEM] API Key securely saved to your Mac profile.")
        else:
            self.log_message("[WARNING] API Key field is empty.")

    def load_api_key(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                key = f.read().strip()
                if key:
                    self.entry_api.insert(0, key)

    def select_source(self):
        self.source_dir = filedialog.askdirectory(title="Select Master Source Folder")
        if self.source_dir:
            self.lbl_source.configure(text=os.path.basename(self.source_dir), text_color="white")

    def select_target(self):
        self.target_dir = filedialog.askdirectory(title="Select Target Folder")
        if self.target_dir:
            self.lbl_target.configure(text=os.path.basename(self.target_dir), text_color="white")

    def log_message(self, message):
        self.console.insert("end", message + "\n")
        self.console.see("end")

    # Safe UI updater for the background thread
    def update_telemetry(self, current, total, eta_str):
        self.lbl_progress.configure(text=f"Processing: {current}/{total} Files | ETA: {eta_str}")

    def start_processing_thread(self):
        if not self.source_dir or not self.target_dir:
            self.log_message("[ERROR] Please select both folders first.")
            return
            
        self.btn_run.configure(state="disabled", text="Swarm Active... Please Wait")
        self.lbl_progress.configure(text="Calculating trajectory...")
        thread = threading.Thread(target=self.run_pipeline_manager)
        thread.start()

    def sanitize_text(self, text):
        if not text or text == "N/A": return "Unknown"
        return re.sub(r'[\\/*?:"<>|]', '-', str(text)).strip()

    # --- THE WORKER BOT (Processes a single file) ---
    def process_single_file(self, old_path, catalog_file, client):
        filename = os.path.basename(old_path)
        ext = os.path.splitext(filename)[1].lower()
        self.log_message(f"Bot engaged: {filename}...")
        
        temp_dir = tempfile.gettempdir()
        safe_filename = f"safe_upload_{int(time.time() * 1000)}_{threading.get_ident()}"
        upload_path = None
        
        if ext in ['.tiff', '.tif', '.heic']:
            upload_path = os.path.join(temp_dir, safe_filename + ".pdf")
            try:
                img = Image.open(old_path)
                imgs = [img.convert("RGB")]
                if getattr(img, "is_animated", False) or hasattr(img, "n_frames"):
                    for i in range(1, img.n_frames):
                        img.seek(i)
                        imgs.append(img.convert("RGB"))
                imgs[0].save(upload_path, save_all=True, append_images=imgs[1:])
            except Exception as e:
                self.log_message(f"   [ERROR] Image conversion failed on {filename}: {e}")
                return
        else:
            upload_path = os.path.join(temp_dir, safe_filename + ext)
            shutil.copy2(old_path, upload_path)

        uploaded_file = None
        try:
            uploaded_file = client.files.upload(file=upload_path)
            
            # --- THE POLLING LOOP (Corrected) ---
            while uploaded_file.state.name == 'PROCESSING':
                self.log_message(f"   [WAIT] Google is digesting {filename}...")
                time.sleep(3)
                uploaded_file = client.files.get(name=uploaded_file.name)
                
            if uploaded_file.state.name == 'FAILED':
                raise Exception("Google rejected the file format.")
            # ------------------------------------------

            prompt_meta = 'Extract: 1. Execution Date (YYYY-MM-DD). If none, use "Unknown_Date". 2. Document Type (3-4 words, use underscores). Return ONLY valid JSON: {"date": "YYYY-MM-DD", "doc_type": "Doc_Type"}'
            res_meta = client.models.generate_content(model='gemini-2.5-flash', contents=[uploaded_file, prompt_meta])
            
            prompt_text = "Extract 100% of the raw text accurately. Preserve formatting."
            res_text = client.models.generate_content(model='gemini-2.5-flash', contents=[uploaded_file, prompt_text])
            
            match = re.search(r'\{.*?\}', res_meta.text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group(0))
                c_date = self.sanitize_text(ai_data.get("date", "Unknown"))
                d_type = self.sanitize_text(ai_data.get("doc_type", "Unknown"))
                
                year_match = re.match(r'^(\d{4})', c_date)
                year_folder = year_match.group(1) if year_match else "Unknown_Year"
                year_dir_path = os.path.join(self.target_dir, year_folder)
                os.makedirs(year_dir_path, exist_ok=True)
                
                new_filename = f"{c_date}_{d_type}{ext}"
                new_path = os.path.join(year_dir_path, new_filename)
                if os.path.exists(new_path):
                    new_filename = f"{c_date}_{d_type}_2_{int(time.time() % 1000)}{ext}"
                    new_path = os.path.join(year_dir_path, new_filename)
                    
                txt_path = os.path.join(year_dir_path, f"{os.path.splitext(new_filename)[0]}.txt")
                
                shutil.move(old_path, new_path)
                if res_text.text:
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(res_text.text)
                        
                with self.csv_lock:
                    with open(catalog_file, 'a', newline='') as f:
                        csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), filename, new_filename, c_date, d_type, old_path])
                    
                self.log_message(f"✓ Saved: /{year_folder}/{new_filename}")
            else:
                self.log_message(f"✗ FAILED JSON Parse: {filename}")
                
        except Exception as e:
            self.log_message(f"   [ERROR] API Failure on {filename}: {e}")
        finally:
            if uploaded_file:
                try: client.files.delete(name=uploaded_file.name)
                except: pass
            if upload_path and os.path.exists(upload_path):
                os.remove(upload_path)
                
        time.sleep(2)

    # --- THE SWARM MANAGER ---
    def run_pipeline_manager(self):
        api_key = self.entry_api.get().strip()
        if not api_key:
            self.log_message("[CRITICAL] Please enter your GEMINI_API_KEY in the box above.")
            self.after(0, lambda: self.btn_run.configure(state="normal", text=f"▶ Run Swarm Engine ({MAX_CONCURRENT_WORKERS} Bots)"))
            self.after(0, lambda: self.lbl_progress.configure(text="Awaiting Task..."))
            return
            
        client = genai.Client(api_key=api_key)
        
        catalog_file = os.path.join(self.target_dir, "document_catalog_gemini.csv")
        if not os.path.exists(catalog_file):
            with open(catalog_file, 'w', newline='') as f:
                csv.writer(f).writerow(["Process_Timestamp", "Original_Filename", "New_Filename", "Execution_Date", "Document_Type", "Original_Path"])

        self.log_message("Scanning master folder tree. Building target list...")
        
        files_to_process = []
        for root, dirs, files in os.walk(self.source_dir):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTS and not f.startswith('._'):
                    files_to_process.append(os.path.join(root, f))

        total_files = len(files_to_process)
        if total_files == 0:
            self.log_message("No supported files found in the source directory.")
            self.after(0, lambda: self.btn_run.configure(state="normal", text=f"▶ Run Swarm Engine ({MAX_CONCURRENT_WORKERS} Bots)"))
            self.after(0, lambda: self.lbl_progress.configure(text="Complete"))
            return

        self.log_message(f"Deploying {MAX_CONCURRENT_WORKERS} bots to process {total_files} files...\n---")

        start_time = time.time()
        processed_count = 0

        # Deploy the Swarm and track live progress
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
            futures = [executor.submit(self.process_single_file, filepath, catalog_file, client) for filepath in files_to_process]
            
            # As each individual bot finishes a file, update the math
            for future in concurrent.futures.as_completed(futures):
                processed_count += 1
                files_left = total_files - processed_count
                elapsed = time.time() - start_time
                
                # Calculate ETA based on current swarm velocity
                avg_time_per_file = elapsed / processed_count
                eta_seconds = avg_time_per_file * files_left
                mins, secs = divmod(int(eta_seconds), 60)
                eta_str = f"{mins}m {secs}s"
                
                # Safely push the math to the Mac GUI
                self.after(0, self.update_telemetry, processed_count, total_files, eta_str)
            
        self.log_message("\n=== SWARM CRAWL COMPLETE ===")
        self.after(0, lambda: self.btn_run.configure(state="normal", text=f"▶ Run Swarm Engine ({MAX_CONCURRENT_WORKERS} Bots)"))
        self.after(0, lambda: self.lbl_progress.configure(text="All Files Processed Successfully!"))

if __name__ == "__main__":
    app = LegalSorterApp()
    app.mainloop()