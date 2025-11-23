import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import requests
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class FF7Downloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fitgirl FuckingFast.co Batch Downloader")
        self.geometry("900x880")

        self.link_vars = []  # Stores (URL, BooleanVar, Name) tuples
        
        self.create_ui()

    def create_ui(self):
        # --- TOP SECTION: INPUT ---
        top_frame = tk.LabelFrame(self, text="Step 1: Paste Links Here", font=("Arial", 10, "bold"))
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        self.input_text = scrolledtext.ScrolledText(top_frame, height=8, width=80)
        self.input_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Default instruction text
        self.input_text.insert(tk.END, "Paste your list of https://fuckingfast.co/... links here...")

        load_btn = tk.Button(top_frame, text="Load & Parse Links", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), command=self.parse_links_from_input)
        load_btn.pack(pady=5)

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
        
        canvas = tk.Canvas(list_frame, height=300) # Fixed height for the list
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

        self.btn_start = tk.Button(bottom_frame, text="START BATCH DOWNLOAD", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), height=2, command=self.start_thread)
        self.btn_start.pack(fill=tk.X)

        # Progress UI
        progress_frame = tk.LabelFrame(self, text="Download Progress", font=("Arial", 10, "bold"))
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        # Per-file progress: label + determinate bar + size label
        self.current_file_label = tk.Label(progress_frame, text="No active download", anchor="w")
        self.current_file_label.pack(fill=tk.X, padx=5, pady=(5,0))

        self.file_progress = ttk.Progressbar(progress_frame, mode="determinate", maximum=100, value=0)
        self.file_progress.pack(fill=tk.X, padx=5, pady=(2,4))

        self.file_size_label = tk.Label(progress_frame, text="", anchor="w")
        self.file_size_label.pack(fill=tk.X, padx=5, pady=(0,6))

        # Overall progress: determinate bar showing completed/total
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

    # --- Parsing Logic ---
    def parse_links_from_input(self):
        # 1. Get text
        raw_text = self.input_text.get("1.0", tk.END)
        lines = [l.strip("- ") for l in raw_text.split('\n') if l.strip()]
        
        if not lines:
            messagebox.showinfo("Empty", "Please paste links first.")
            return

        # 2. Clear old widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.link_vars.clear()

        # 3. Create new checkboxes
        count = 0
        for i, url in enumerate(lines):
            if not url.startswith("http"):
                continue # Skip non-links

            # Extract filename from URL hash if present
            # format: https://...#filename.rar
            if "#" in url:
                filename = url.split("#")[-1]
            else:
                # Fallback if no hash
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
        # Always update UI from main thread
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
        # Disable start button safely
        self.after(0, lambda: self.btn_start.config(state='disabled', text="DOWNLOADING IN PROGRESS..."))

        # Setup Driver
        driver = self.setup_driver()
        if not driver:
            self.log("Failed to initialize Browser.")
            self.after(0, lambda: self.btn_start.config(state='normal', text="START BATCH DOWNLOAD"))
            return

        download_path = os.path.join(os.getcwd(), "batch_downloads")
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        total = len(selected_items)
        completed = 0

        # Initialize overall progress UI
        self.after(0, lambda: self.overall_progress.config(maximum=total, value=0))
        self.after(0, lambda: self.overall_label.config(text=f"0 / {total}"))

        try:
            for index, (url, _, filename) in enumerate(selected_items):
                # Update current file label
                self.after(0, lambda fn=filename, idx=index, tot=total: self.current_file_label.config(text=f"Preparing: {fn} ({idx+1}/{tot})"))
                self.after(0, lambda: self.file_progress.config(value=0))
                self.after(0, lambda: self.file_size_label.config(text=""))

                self.log(f"[{index+1}/{total}] processing: {filename}")
                
                try:
                    driver.get(url)
                    
                    # Try to find the direct download link BEFORE clicking, if any
                    # Look for anchor tags with file-like hrefs
                    possible_href = None
                    try:
                        anchors = driver.find_elements(By.TAG_NAME, "a")
                        for a in anchors:
                            try:
                                href = a.get_attribute("href") or ""
                                if any(ext in href.lower() for ext in [".zip", ".rar", ".7z", ".exe", ".tar", ".msi"]):
                                    possible_href = href
                                    break
                            except Exception:
                                continue
                    except Exception:
                        possible_href = None

                    # Find and click DOWNLOAD button (existing logic)
                    btn = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download') or contains(., 'DOWNLOAD')]"))
                    )
                    # Sometimes button element has href in parent/child or onclick; try to extract
                    try:
                        # If button has a 'href' attribute (rare), use it
                        btn_href = btn.get_attribute("href")
                        if btn_href:
                            possible_href = btn_href
                    except Exception:
                        pass

                    # If still no possible_href, attempt to inspect onclick text for URL
                    if not possible_href:
                        try:
                            onclick = btn.get_attribute("onclick") or ""
                            # rough extraction of URLs from onclick
                            if "http" in onclick:
                                start = onclick.find("http")
                                # take until next quote or space
                                tail = onclick[start:]
                                endpos = min([p for p in [tail.find("'"), tail.find('"'), tail.find(")"), tail.find(" ")] if p!=-1] + [len(tail)])
                                possible_href = tail[:endpos]
                        except Exception:
                            pass

                    # Click the button to start download
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                    except Exception:
                        try:
                            btn.click()
                        except Exception:
                            self.log("Could not click download button programmatically.")

                    # After clicking, try to fully resolve possible_href to absolute URL
                    if possible_href:
                        possible_href = urllib.parse.urljoin(driver.current_url, possible_href)

                    # Monitor the download folder for a new .crdownload file and show progress
                    success = self.monitor_download_live(download_path, possible_href, filename, timeout=600)

                    if success:
                        self.log(f" -> COMPLETED: {filename}")
                    else:
                        self.log(f" -> TIMEOUT/FAILED: {filename}")

                except Exception as e:
                    self.log(f" -> ERROR: Could not download {filename} ({e})")

                finally:
                    completed += 1
                    # Update overall progress bar safely
                    self.after(0, lambda c=completed: self.overall_progress.config(value=c))
                    self.after(0, lambda c=completed, t=total: self.overall_label.config(text=f"{c} / {t}"))
                    # Clear current file label briefly
                    self.after(0, lambda: self.current_file_label.config(text="Idle"))
                    time.sleep(0.3)  # small pause

        except Exception as e:
            self.log(f"Critical Error: {e}")
        finally:
            self.log("------------------------------")
            self.log("Batch finished. You can close the app.")
            try:
                driver.quit()
            except Exception:
                pass
            self.after(0, lambda: self.btn_start.config(state='normal', text="START BATCH DOWNLOAD"))
            self.after(0, lambda: self.current_file_label.config(text="No active download"))
            self.after(0, lambda: self.file_progress.config(value=0))
            self.after(0, lambda: self.file_size_label.config(text=""))

    def setup_driver(self):
        try:
            download_folder = os.path.join(os.getcwd(), "batch_downloads")
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)

            options = Options()
            options.add_argument("--headless=new") # UNCOMMENT to hide browser
            options.add_argument("--window-size=1000,800")
            options.add_argument("--disable-gpu")
            # Mock user agent to look like real user
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

            prefs = {
                "download.default_directory": download_folder,
                "download.prompt_for_download": False,
                "directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
            
            driver = webdriver.Chrome(options=options)
            
            # Force headless download permissions (even if visible, good practice)
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': download_folder
            })
            
            return driver
        except Exception as e:
            self.log(f"Driver Setup Error: {e}")
            return None

    def monitor_download_live(self, folder, possible_href, filename, timeout=600):
        """
        Monitor for a new .crdownload file and update per-file progress in real-time.
        Attempts to use Content-Length from possible_href (HEAD request) for accurate percent.
        If unknown, uses dynamic scaling of progress bar so it visually moves as bytes increase.
        """
        start_time = time.time()
        seen_cr = None
        prev_size = 0
        dynamic_max = 1 * 1024 * 1024  # start with 1MB maximum for visual scaling
        expected_size = None

        # If we have a possible_href, attempt HEAD to get Content-Length
        if possible_href:
            try:
                head = requests.head(possible_href, allow_redirects=True, timeout=8)
                if head.status_code == 200 and 'Content-Length' in head.headers:
                    expected_size = int(head.headers['Content-Length'])
            except Exception:
                expected_size = None

        # wait for a new file to appear (either a .crdownload or direct file)
        while (time.time() - start_time) < timeout:
            time.sleep(0.4)
            try:
                files = os.listdir(folder)
            except FileNotFoundError:
                files = []

            # look for a .crdownload file that is new/recent
            crdownload_files = [os.path.join(folder, f) for f in files if f.endswith(".crdownload")]
            non_temp_files = [os.path.join(folder, f) for f in files if not f.endswith(".crdownload") and not f.startswith('.')]

            # Choose the newest .crdownload if present
            if crdownload_files:
                # pick most recently modified .crdownload
                crdownload_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                seen_cr = crdownload_files[0]
                # estimate expected_size again if we haven't and we have a filename mapping to possible_href
                # (we attempted HEAD before clicking already)
                break
            else:
                # No .crdownload present yet - maybe the file downloaded extremely fast and final file is present
                # check if a file matching filename exists (exact or prefix)
                matches = [p for p in non_temp_files if filename in os.path.basename(p) or os.path.basename(p).startswith(os.path.splitext(filename)[0])]
                if matches:
                    # assume done
                    final_path = max(matches, key=lambda p: os.path.getmtime(p))
                    final_size = os.path.getsize(final_path)
                    # Set UI to 100% (if expected known) or show size
                    if expected_size:
                        pct = min(100, int(final_size / expected_size * 100))
                        self.after(0, lambda p=pct: self.file_progress.config(value=p))
                        self.after(0, lambda: self.file_size_label.config(text=f"{final_size/1024/1024:.2f} MB / {expected_size/1024/1024:.2f} MB"))
                    else:
                        # dynamic: set progress to full
                        self.after(0, lambda: self.file_progress.config(value=100))
                        self.after(0, lambda: self.file_size_label.config(text=f"{final_size/1024/1024:.2f} MB"))
                    return True

        # If we reach here, wait for .crdownload to appear and then monitor
        if not seen_cr:
            # wait a bit longer for .crdownload to start
            wait_start = time.time()
            while (time.time() - wait_start) < 15:
                time.sleep(0.4)
                try:
                    files = os.listdir(folder)
                except FileNotFoundError:
                    files = []
                crdownload_files = [os.path.join(folder, f) for f in files if f.endswith(".crdownload")]
                if crdownload_files:
                    crdownload_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                    seen_cr = crdownload_files[0]
                    break

        if not seen_cr:
            # no crdownload found within a short window; fallback to polling folder for new file for some time
            poll_start = time.time()
            initial_listing = set(os.listdir(folder))
            while (time.time() - poll_start) < 10:
                time.sleep(0.5)
                try:
                    files = set(os.listdir(folder))
                except FileNotFoundError:
                    files = set()
                new_files = files - initial_listing
                if new_files:
                    # pick newest new file
                    new_paths = [os.path.join(folder, f) for f in new_files]
                    final_path = max(new_paths, key=lambda p: os.path.getmtime(p))
                    final_size = os.path.getsize(final_path)
                    self.after(0, lambda: self.file_progress.config(value=100))
                    self.after(0, lambda: self.file_size_label.config(text=f"{final_size/1024/1024:.2f} MB"))
                    return True

        # If we still didn't find any file to monitor, abort
        if not seen_cr:
            return False

        # Now monitor the .crdownload file until it disappears (download finished)
        last_mtime = 0
        while (time.time() - start_time) < timeout:
            time.sleep(0.5)
            try:
                if not os.path.exists(seen_cr):
                    # .crdownload vanished -> download probably finished; find final file
                    final_candidates = [os.path.join(folder, f) for f in os.listdir(folder) if not f.startswith(".") and not f.endswith(".crdownload")]
                    if final_candidates:
                        final_path = max(final_candidates, key=lambda p: os.path.getmtime(p))
                        final_size = os.path.getsize(final_path)
                        if expected_size:
                            pct = min(100, int(final_size / expected_size * 100))
                            self.after(0, lambda p=pct: self.file_progress.config(value=p))
                            self.after(0, lambda: self.file_size_label.config(text=f"{final_size/1024/1024:.2f} MB / {expected_size/1024/1024:.2f} MB"))
                        else:
                            self.after(0, lambda: self.file_progress.config(value=100))
                            self.after(0, lambda: self.file_size_label.config(text=f"{final_size/1024/1024:.2f} MB"))
                        return True
                    else:
                        # no final file found but .crdownload disappeared; treat as success
                        self.after(0, lambda: self.file_progress.config(value=100))
                        return True

                # read current size
                cur_size = os.path.getsize(seen_cr)
                # update size label
                size_text = f"{cur_size/1024/1024:.2f} MB"
                if expected_size:
                    pct = min(100.0, (cur_size / expected_size) * 100.0)
                    self.after(0, lambda p=pct: self.file_progress.config(value=p))
                    self.after(0, lambda: self.file_size_label.config(text=f"{size_text} / {expected_size/1024/1024:.2f} MB ({p:.1f}%)"))
                else:
                    # dynamic scaling: if size exceeds dynamic_max, increase dynamic_max
                    if cur_size > dynamic_max:
                        # scale up to accommodate real size
                        while cur_size > dynamic_max:
                            dynamic_max *= 2
                        # represent progress as percent of dynamic_max
                        val = min(99.9, (cur_size / dynamic_max) * 100.0)
                        self.after(0, lambda p=val: self.file_progress.config(value=p))
                        self.after(0, lambda: self.file_size_label.config(text=f"{size_text} (estimating...)"))
                    else:
                        val = (cur_size / dynamic_max) * 100.0
                        self.after(0, lambda p=val: self.file_progress.config(value=p))
                        self.after(0, lambda: self.file_size_label.config(text=f"{size_text} (estimating...)"))

                prev_size = cur_size

            except Exception:
                # On any error reading the file, continue waiting
                continue

        # timeout reached
        return False

if __name__ == "__main__":
    app = FF7Downloader()
    app.mainloop()
