import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
import os
import requests
import urllib.parse
import glob

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class FF7Downloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fitgirl FuckingFast.co Batch Downloader v3")
        self.geometry("900x920")

        self.link_vars = []  # Stores (URL, BooleanVar, Name) tuples
        self.retry_event = threading.Event() # Event to signal a retry
        
        self.create_ui()

    def create_ui(self):
        # --- TOP SECTION: INPUT ---
        top_frame = tk.LabelFrame(self, text="Step 1: Input Links", font=("Arial", 10, "bold"))
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        self.input_text = scrolledtext.ScrolledText(top_frame, height=8, width=80)
        self.input_text.pack(fill=tk.X, padx=5, pady=5)
        
        self.input_text.insert(tk.END, "Paste your list of https://fuckingfast.co/...#filename.rar links here...")

        # Button Row
        top_btn_frame = tk.Frame(top_frame)
        top_btn_frame.pack(pady=5)

        tk.Button(top_btn_frame, text="📂 Load from Text File", bg="#FF9800", fg="white", font=("Arial", 10, "bold"), 
                  command=self.load_from_file).pack(side=tk.LEFT, padx=10)
        
        tk.Button(top_btn_frame, text="⬇ Load & Parse Links", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), 
                  command=self.parse_links_from_input).pack(side=tk.LEFT, padx=10)

        # --- MIDDLE SECTION: FILTERS ---
        filter_frame = tk.LabelFrame(self, text="Step 2: Select Files", font=("Arial", 10, "bold"))
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        # Selection Buttons
        btn_frame = tk.Frame(filter_frame)
        btn_frame.pack(pady=5, fill=tk.X)
        
        tk.Button(btn_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Deselect All", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        
        # Smart Filters
        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        tk.Label(btn_frame, text="Quick Filters: ", fg="gray").pack(side=tk.LEFT)
        
        tk.Button(btn_frame, text="Core Game", bg="#e1f5fe", command=lambda: self.select_pattern("fitgirl-repacks.site")).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Credits", command=lambda: self.select_pattern("optional-credits")).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="French", command=lambda: self.select_pattern("optional-french")).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="German", command=lambda: self.select_pattern("optional-german")).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Japanese", command=lambda: self.select_pattern("optional-japanese")).pack(side=tk.LEFT, padx=2)

        # --- SCROLLABLE CHECKBOX AREA ---
        list_frame = tk.Frame(filter_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(list_frame, height=250) 
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- BOTTOM SECTION: ACTION ---
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(pady=10, fill=tk.X, padx=10)

        self.btn_start = tk.Button(bottom_frame, text="START BATCH DOWNLOAD", bg="#4CAF50", fg="white", 
                                   font=("Arial", 12, "bold"), height=2, command=self.start_thread)
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.btn_retry = tk.Button(bottom_frame, text="↻ RESTART CURRENT FILE", bg="#f44336", fg="white", 
                                   font=("Arial", 10, "bold"), height=2, state='disabled', command=self.trigger_retry)
        self.btn_retry.pack(side=tk.RIGHT, padx=(5, 0))

        # Progress UI
        progress_frame = tk.LabelFrame(self, text="Download Progress", font=("Arial", 10, "bold"))
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.current_file_label = tk.Label(progress_frame, text="No active download", anchor="w")
        self.current_file_label.pack(fill=tk.X, padx=5, pady=(5,0))

        self.file_progress = ttk.Progressbar(progress_frame, mode="determinate", maximum=100, value=0)
        self.file_progress.pack(fill=tk.X, padx=5, pady=(2,4))

        self.file_size_label = tk.Label(progress_frame, text="", anchor="w")
        self.file_size_label.pack(fill=tk.X, padx=5, pady=(0,6))

        overall_row = tk.Frame(progress_frame)
        overall_row.pack(fill=tk.X, padx=5, pady=(2,8))
        self.overall_progress = ttk.Progressbar(overall_row, mode="determinate")
        self.overall_progress.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.overall_label = tk.Label(overall_row, text="0 / 0", width=12)
        self.overall_label.pack(side=tk.RIGHT, padx=(8,0))

        # Log
        tk.Label(self, text="Process Log:").pack(anchor="w", padx=10)
        self.log_area = scrolledtext.ScrolledText(self, height=8, state='disabled', bg="#f0f0f0")
        self.log_area.pack(fill=tk.X, padx=10, pady=(0, 10))

    # --- New Function: Load File ---
    def load_from_file(self):
        file_path = filedialog.askopenfilename(title="Select Links File", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert(tk.END, content)
                self.log(f"Loaded links from: {os.path.basename(file_path)}")
                self.parse_links_from_input()
            except Exception as e:
                messagebox.showerror("Error", f"Could not read file: {e}")

    # --- New Function: Trigger Retry ---
    def trigger_retry(self):
        if messagebox.askyesno("Confirm Retry", "Are you sure you want to restart the current file download? This will delete partial files."):
            self.retry_event.set()
            self.log(">>> RETRY REQUESTED... Please wait for reset.")

    # --- Parsing Logic ---
    def parse_links_from_input(self):
        raw_text = self.input_text.get("1.0", tk.END)
        lines = [l.strip("- ") for l in raw_text.split('\n') if l.strip()]
        
        if not lines:
            messagebox.showinfo("Empty", "Please paste links or load a file first.")
            return

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.link_vars.clear()

        count = 0
        for i, url in enumerate(lines):
            if not url.startswith("http"):
                continue

            if "#" in url:
                filename = url.split("#")[-1]
            else:
                filename = f"Link {i+1}: {url[:30]}..."

            var = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(self.scrollable_frame, text=filename, variable=var, anchor="w")
            cb.pack(fill=tk.X, padx=5, pady=2)
            
            self.link_vars.append((url, var, filename))
            count += 1
        
        self.log(f"Loaded {count} links. Select files to download.")

    # --- Selection Helpers ---
    def select_all(self):
        for _, var, _ in self.link_vars:
            var.set(True)

    def deselect_all(self):
        for _, var, _ in self.link_vars:
            var.set(False)

    def select_pattern(self, pattern):
        count = 0
        for _, var, filename in self.link_vars:
            if pattern.lower() in filename.lower():
                var.set(True)
                count += 1
            else:
                var.set(False)
        self.log(f"Auto-selected {count} files matching '{pattern}'.")

    # --- Logging ---
    def log(self, msg):
        def _append():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, f"{msg}\n")
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.after(0, _append)

    # --- Download Logic ---
    def start_thread(self):
        selected_urls = [item for item in self.link_vars if item[1].get()]
        
        if not selected_urls:
            messagebox.showwarning("No Selection", "Please select at least one file to download.")
            return
            
        t = threading.Thread(target=self.run_batch, args=(selected_urls,), daemon=True)
        t.start()

    def run_batch(self, selected_items):
        self.after(0, lambda: self.btn_start.config(state='disabled', text="DOWNLOADING..."))
        self.after(0, lambda: self.btn_retry.config(state='normal'))

        driver = self.setup_driver()
        if not driver:
            self.log("Failed to initialize Browser.")
            self.after(0, lambda: self.btn_start.config(state='normal', text="START BATCH DOWNLOAD"))
            self.after(0, lambda: self.btn_retry.config(state='disabled'))
            return

        download_path = os.path.join(os.getcwd(), "batch_downloads")
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        total = len(selected_items)
        index = 0
        completed = 0

        self.after(0, lambda: self.overall_progress.config(maximum=total, value=0))
        self.after(0, lambda: self.overall_label.config(text=f"0 / {total}"))

        try:
            while index < total:
                url, _, filename = selected_items[index]
                self.retry_event.clear() # Reset retry flag

                # ---------------------------------------------------------
                # NEW CHECK: Skip if file already exists
                # ---------------------------------------------------------
                target_file_path = os.path.join(download_path, filename)
                
                # Check for existence (only works if filename derived from #hash matches real file)
                if os.path.exists(target_file_path) and not filename.startswith("Link "):
                    self.log(f"[{index+1}/{total}] SKIPPING: {filename} (Already exists)")
                    completed += 1
                    
                    # Update progress bars
                    self.after(0, lambda c=completed: self.overall_progress.config(value=c))
                    self.after(0, lambda c=completed, t=total: self.overall_label.config(text=f"{c} / {t}"))
                    
                    index += 1
                    continue
                # ---------------------------------------------------------

                # Update current file label
                self.after(0, lambda fn=filename, idx=index, tot=total: self.current_file_label.config(text=f"Preparing: {fn} ({idx+1}/{tot})"))
                self.after(0, lambda: self.file_progress.config(value=0))
                self.after(0, lambda: self.file_size_label.config(text=""))
                self.log(f"[{index+1}/{total}] processing: {filename}")

                status = "FAILED"
                try:
                    driver.get(url)
                    
                    possible_href = None
                    try:
                        # Find potential link before click for size estimation
                        anchors = driver.find_elements(By.TAG_NAME, "a")
                        for a in anchors:
                            href = a.get_attribute("href") or ""
                            if any(ext in href.lower() for ext in [".zip", ".rar", ".7z", ".exe", ".bin"]):
                                possible_href = href
                                break
                    except: pass

                    # Click Download
                    btn = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download') or contains(., 'DOWNLOAD')]"))
                    )
                    
                    # Try to click
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                    except:
                        btn.click()

                    # Resolve absolute URL if possible
                    if possible_href:
                        possible_href = urllib.parse.urljoin(driver.current_url, possible_href)

                    # MONITOR DOWNLOAD
                    status = self.monitor_download_live(download_path, possible_href, filename, timeout=600)

                except Exception as e:
                    self.log(f" -> ERROR: {e}")
                    status = "ERROR"

                # CHECK STATUS
                if status == "RETRY":
                    self.log(f" -> RESTARTING {filename}...")
                    # Cleanup partial files
                    partials = glob.glob(os.path.join(download_path, "*.crdownload"))
                    for p in partials:
                        try: os.remove(p)
                        except: pass
                    # Do NOT increment index, loop continues on same item
                    continue
                
                elif status == "SUCCESS":
                    self.log(f" -> COMPLETED: {filename}")
                    completed += 1
                else:
                    self.log(f" -> TIMEOUT/FAILED: {filename}")
                    completed += 1 # We count failed as done processing to move on

                # Update overall progress
                self.after(0, lambda c=completed: self.overall_progress.config(value=c))
                self.after(0, lambda c=completed, t=total: self.overall_label.config(text=f"{c} / {t}"))
                self.after(0, lambda: self.current_file_label.config(text="Idle"))
                time.sleep(0.5)
                
                # Move to next item
                index += 1

        except Exception as e:
            self.log(f"Critical Error: {e}")
        finally:
            self.log("------------------------------")
            self.log("Batch finished.")
            try: driver.quit()
            except: pass
            self.after(0, lambda: self.btn_start.config(state='normal', text="START BATCH DOWNLOAD"))
            self.after(0, lambda: self.btn_retry.config(state='disabled'))
            self.after(0, lambda: self.current_file_label.config(text="No active download"))
            self.after(0, lambda: self.file_progress.config(value=0))

    def setup_driver(self):
        try:
            download_folder = os.path.join(os.getcwd(), "batch_downloads")
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)

            options = Options()
            options.add_argument("--headless=new") 
            options.add_argument("--window-size=1000,800")
            options.add_argument("--disable-gpu")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

            prefs = {
                "download.default_directory": download_folder,
                "download.prompt_for_download": False,
                "directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
            
            driver = webdriver.Chrome(options=options)
            
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': download_folder
            })
            
            return driver
        except Exception as e:
            self.log(f"Driver Setup Error: {e}")
            return None

    def monitor_download_live(self, folder, possible_href, filename, timeout=600):
        start_time = time.time()
        seen_cr = None
        dynamic_max = 1 * 1024 * 1024 
        expected_size = None

        if possible_href:
            try:
                head = requests.head(possible_href, allow_redirects=True, timeout=8)
                if head.status_code == 200 and 'Content-Length' in head.headers:
                    expected_size = int(head.headers['Content-Length'])
            except: pass

        # Wait loop for file appearance
        while (time.time() - start_time) < timeout:
            # CHECK RETRY
            if self.retry_event.is_set():
                return "RETRY"

            time.sleep(0.4)
            
            # --- Detection Logic ---
            try: files = os.listdir(folder)
            except: files = []
            
            crdownload_files = [os.path.join(folder, f) for f in files if f.endswith(".crdownload")]
            non_temp_files = [os.path.join(folder, f) for f in files if not f.endswith(".crdownload") and not f.startswith('.')]

            if crdownload_files:
                crdownload_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                seen_cr = crdownload_files[0]
                break
            else:
                matches = [p for p in non_temp_files if filename in os.path.basename(p) or os.path.basename(p).startswith(os.path.splitext(filename)[0])]
                if matches:
                    final_path = max(matches, key=lambda p: os.path.getmtime(p))
                    final_size = os.path.getsize(final_path)
                    if expected_size:
                        pct = min(100, int(final_size / expected_size * 100))
                        self.after(0, lambda p=pct: self.file_progress.config(value=p))
                        self.after(0, lambda: self.file_size_label.config(text=f"{final_size/1024/1024:.2f} MB / {expected_size/1024/1024:.2f} MB"))
                    else:
                        self.after(0, lambda: self.file_progress.config(value=100))
                        self.after(0, lambda: self.file_size_label.config(text=f"{final_size/1024/1024:.2f} MB"))
                    return "SUCCESS"

        if not seen_cr:
            return "TIMEOUT"

        # Monitoring loop
        while (time.time() - start_time) < timeout:
            # CHECK RETRY
            if self.retry_event.is_set():
                return "RETRY"

            time.sleep(0.5)
            try:
                if not os.path.exists(seen_cr):
                    # Finished or failed? Check for result file
                    final_candidates = [os.path.join(folder, f) for f in os.listdir(folder) if not f.startswith(".") and not f.endswith(".crdownload")]
                    if final_candidates:
                         # Assume success
                         self.after(0, lambda: self.file_progress.config(value=100))
                         return "SUCCESS"
                    else:
                         self.after(0, lambda: self.file_progress.config(value=100))
                         return "SUCCESS"

                cur_size = os.path.getsize(seen_cr)
                size_text = f"{cur_size/1024/1024:.2f} MB"
                
                if expected_size:
                    pct = min(100.0, (cur_size / expected_size) * 100.0)
                    self.after(0, lambda p=pct: self.file_progress.config(value=p))
                    self.after(0, lambda: self.file_size_label.config(text=f"{size_text} / {expected_size/1024/1024:.2f} MB ({p:.1f}%)"))
                else:
                    if cur_size > dynamic_max:
                        while cur_size > dynamic_max: dynamic_max *= 2
                        val = min(99.9, (cur_size / dynamic_max) * 100.0)
                        self.after(0, lambda p=val: self.file_progress.config(value=p))
                    else:
                        val = (cur_size / dynamic_max) * 100.0
                        self.after(0, lambda p=val: self.file_progress.config(value=p))
                    self.after(0, lambda: self.file_size_label.config(text=f"{size_text} (estimating...)"))

            except Exception:
                continue

        return "TIMEOUT"

if __name__ == "__main__":
    app = FF7Downloader()
    app.mainloop()