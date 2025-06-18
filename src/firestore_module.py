import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
from datetime import datetime
import json
from supabase import create_client
from storage3.exceptions import StorageApiError

class SupabaseMDXManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Supabase MDX File Manager")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Initialize Supabase client
        self.setup_supabase()
        
        # Setup UI
        self.setup_styles()
        self.create_widgets()
        self.setup_layout()
        
        # Load files on startup
        self.refresh_file_list()

        self.bind_additional_events()
    
    def setup_supabase(self):
        """Initialize Supabase client"""
        try:
            # Load credentials from config/secrets.json
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'secrets.json')
            with open(config_path, 'r') as f:
                secrets = json.load(f)
            url = secrets.get('supabase_url')
            key = secrets.get('firestore_key')
            from supabase import create_client
            self.supabase = create_client(url, key)
            self.bucket_name = "mdx-files"
            self.folder_states = {} 
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Connection Error", f"Failed to connect to Supabase: {str(e)}")
            self.root.destroy()
    
    def setup_styles(self):
        """Configure ttk styles for better appearance"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure button styles
        style.configure('Action.TButton', padding=(10, 5))
        style.configure('Danger.TButton', background='#dc3545', foreground='white')
        style.configure('Success.TButton', background='#28a745', foreground='white')
        style.configure('Primary.TButton', background='#007bff', foreground='white')
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        
        # Top toolbar
        self.toolbar_frame = ttk.Frame(self.main_frame)
        
        # Upload button
        self.upload_btn = ttk.Button(
            self.toolbar_frame, 
            text="📁 Upload File", 
            command=self.upload_file,
            style='Primary.TButton'
        )
        
        # Refresh button
        self.refresh_btn = ttk.Button(
            self.toolbar_frame, 
            text="🔄 Refresh", 
            command=self.refresh_file_list,
            style='Action.TButton'
        )
        
        # Create folder button
        self.create_folder_btn = ttk.Button(
            self.toolbar_frame, 
            text="📂 Create Folder", 
            command=self.create_folder,
            style='Action.TButton'
        )
        
        # Search frame
        self.search_frame = ttk.Frame(self.toolbar_frame)
        self.search_label = ttk.Label(self.search_frame, text="Search:")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=30)
        self.search_var.trace('w', self.filter_files)
        
        # File list with treeview
        self.files_frame = ttk.LabelFrame(self.main_frame, text="Files", padding="5")
        
        # Treeview for file list
        columns = ("name", "path", "size", "modified", "url")
        self.files_tree = ttk.Treeview(self.files_frame, columns=columns, show="tree headings", height=15)
        
        # Configure treeview columns
        self.files_tree.heading("#0", text="Type")
        self.files_tree.heading("name", text="Name")
        self.files_tree.heading("path", text="Path")
        self.files_tree.heading("size", text="Size")
        self.files_tree.heading("modified", text="Modified")
        self.files_tree.heading("url", text="Public URL")
        
        # Column widths
        self.files_tree.column("#0", width=50)
        self.files_tree.column("name", width=200)
        self.files_tree.column("path", width=250)
        self.files_tree.column("size", width=100)
        self.files_tree.column("modified", width=150)
        self.files_tree.column("url", width=400)
        
        # Scrollbars for treeview
        self.tree_scroll_y = ttk.Scrollbar(self.files_frame, orient="vertical", command=self.files_tree.yview)
        self.tree_scroll_x = ttk.Scrollbar(self.files_frame, orient="horizontal", command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)
        
        # Bind treeview events
        self.files_tree.bind("<Double-1>", self.on_file_double_click)
        self.files_tree.bind("<Button-3>", self.show_context_menu)  # Right click
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📄 View Content", command=self.view_file)
        self.context_menu.add_command(label="📥 Download", command=self.download_file)
        self.context_menu.add_command(label="✏️ Rename", command=self.rename_file)
        self.context_menu.add_command(label="🔗 Copy URL", command=self.copy_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete", command=self.delete_file)
        
        # File details and editor frame
        self.details_frame = ttk.LabelFrame(self.main_frame, text="File Details & Editor", padding="5")
        
        # File info
        self.info_frame = ttk.Frame(self.details_frame)
        self.selected_file_label = ttk.Label(self.info_frame, text="No file selected", font=("Arial", 10, "bold"))
        self.file_info_text = tk.Text(self.info_frame, height=4, width=50, state="disabled")
        
        # File editor
        self.editor_frame = ttk.Frame(self.details_frame)
        self.editor_label = ttk.Label(self.editor_frame, text="Content Editor:")
        self.file_editor = scrolledtext.ScrolledText(self.editor_frame, height=15, width=60)
        
        # Editor buttons
        self.editor_buttons_frame = ttk.Frame(self.editor_frame)
        self.save_btn = ttk.Button(
            self.editor_buttons_frame, 
            text="💾 Save Changes", 
            command=self.save_file_content,
            style='Success.TButton'
        )
        self.reload_btn = ttk.Button(
            self.editor_buttons_frame, 
            text="🔄 Reload", 
            command=self.reload_file_content,
            style='Action.TButton'
        )
        
        # Status bar
        self.status_bar = ttk.Label(self.main_frame, text="Ready", relief="sunken", anchor="w")
        
        # Progress bar (initially hidden)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.main_frame, 
            variable=self.progress_var, 
            mode='indeterminate'
        )
    
    def setup_layout(self):
        """Setup widget layout using grid"""
        # Main frame
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Toolbar
        self.toolbar_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.upload_btn.grid(row=0, column=0, padx=(0, 5))
        self.refresh_btn.grid(row=0, column=1, padx=(0, 5))
        self.create_folder_btn.grid(row=0, column=2, padx=(0, 20))
        
        # Search
        self.search_frame.grid(row=0, column=3, sticky="e")
        self.search_label.grid(row=0, column=0, padx=(0, 5))
        self.search_entry.grid(row=0, column=1)
        
        # Configure toolbar column weights
        self.toolbar_frame.grid_columnconfigure(3, weight=1)
        
        # Files frame (left side)
        self.files_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        self.files_tree.grid(row=0, column=0, sticky="nsew")
        self.tree_scroll_y.grid(row=0, column=1, sticky="ns")
        self.tree_scroll_x.grid(row=1, column=0, sticky="ew")
        
        # Configure files frame
        self.files_frame.grid_columnconfigure(0, weight=1)
        self.files_frame.grid_rowconfigure(0, weight=1)
        
        # Details frame (right side)
        self.details_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        
        # File info
        self.info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.selected_file_label.grid(row=0, column=0, sticky="w")
        self.file_info_text.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        # Editor
        self.editor_frame.grid(row=1, column=0, sticky="nsew")
        self.editor_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.file_editor.grid(row=1, column=0, sticky="nsew")
        self.editor_buttons_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.save_btn.grid(row=0, column=0, padx=(0, 5))
        self.reload_btn.grid(row=0, column=1)
        
        # Configure details frame
        self.details_frame.grid_columnconfigure(0, weight=1)
        self.details_frame.grid_rowconfigure(1, weight=1)
        self.info_frame.grid_columnconfigure(0, weight=1)
        self.editor_frame.grid_columnconfigure(0, weight=1)
        self.editor_frame.grid_rowconfigure(1, weight=1)
        
        # Status bar
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Configure main frame
        self.main_frame.grid_columnconfigure(0, weight=2)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Current file tracking
        self.current_file_path = None
        
    # CRUD Operations
    
    def upload_file(self):
        """Upload a new file to Supabase"""
        file_path = filedialog.askopenfilename(
            title="Select MDX File",
            filetypes=[("MDX files", "*.mdx"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        # Get remote path
        remote_path = tk.simpledialog.askstring(
            "Remote Path", 
            "Enter remote path (e.g., posts/article.mdx):",
            initialvalue=f"posts/{os.path.basename(file_path)}"
        )
        
        if not remote_path:
            return
        
        self.start_loading("Uploading file...")
        
        def upload_task():
            try:
                with open(file_path, "rb") as f:
                    result = self.supabase.storage.from_(self.bucket_name).upload(
                        file=f,
                        path=remote_path,
                        file_options={"content-type": "text/markdown"}
                    )
                
                self.root.after(0, lambda: self.upload_complete(result, remote_path))
                
            except StorageApiError as e:
                if "already exists" in str(e):
                    # File exists, ask to update
                    self.root.after(0, lambda: self.handle_file_exists(file_path, remote_path))
                else:
                    self.root.after(0, lambda e=e: self.upload_error(str(e)))
            except Exception as e:
                self.root.after(0, lambda e=e: self.upload_error(str(e)))
        
        threading.Thread(target=upload_task, daemon=True).start()
    
    def handle_file_exists(self, local_path, remote_path):
        """Handle case when file already exists"""
        self.stop_loading()
        result = messagebox.askyesno(
            "File Exists", 
            f"File '{remote_path}' already exists. Do you want to update it?"
        )
        
        if result:
            self.update_file(local_path, remote_path)
    
    def update_file(self, local_path, remote_path):
        """Update existing file"""
        self.start_loading("Updating file...")
        
        def update_task():
            try:
                with open(local_path, "rb") as f:
                    result = self.supabase.storage.from_(self.bucket_name).update(
                        file=f,
                        path=remote_path,
                        file_options={"content-type": "text/markdown"}
                    )
                
                self.root.after(0, lambda: self.upload_complete(result, remote_path))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.upload_error(str(e)))
        
        threading.Thread(target=update_task, daemon=True).start()
    
    def upload_complete(self, result, remote_path):
        """Handle successful upload"""
        self.stop_loading()
        self.update_status(f"Successfully uploaded: {remote_path}")
        messagebox.showinfo("Success", f"File uploaded successfully to {remote_path}")
        self.refresh_file_list()
    
    def upload_error(self, error_msg):
        """Handle upload error"""
        self.stop_loading()
        self.update_status("Upload failed")
        messagebox.showerror("Upload Error", f"Failed to upload file: {error_msg}")
    
    def download_file(self):
        """Download selected file"""
        selected = self.files_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a file to download")
            return
        
        item = self.files_tree.item(selected[0])
        file_path = item['values'][1]  # path column
        
        if not file_path:  # It's a folder
            messagebox.showwarning("Invalid Selection", "Cannot download a folder")
            return
        
        # Choose save location
        save_path = filedialog.asksaveasfilename(
            title="Save File As",
            initialvalue=os.path.basename(file_path),
            filetypes=[("MDX files", "*.mdx"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        
        if not save_path:
            return
        
        self.start_loading("Downloading file...")
        
        def download_task():
            try:
                response = self.supabase.storage.from_(self.bucket_name).download(file_path)
                
                with open(save_path, "wb") as f:
                    f.write(response)
                
                self.root.after(0, lambda: self.download_complete(save_path))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.download_error(str(e)))
        
        threading.Thread(target=download_task, daemon=True).start()
    
    def download_complete(self, save_path):
        """Handle successful download"""
        self.stop_loading()
        self.update_status(f"Downloaded to: {save_path}")
        messagebox.showinfo("Success", f"File downloaded to {save_path}")
    
    def download_error(self, error_msg):
        """Handle download error"""
        self.stop_loading()
        self.update_status("Download failed")
        messagebox.showerror("Download Error", f"Failed to download file: {error_msg}")
    
    def view_file(self):
        """View file content in editor"""
        selected = self.files_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a file to view")
            return
        
        item = self.files_tree.item(selected[0])
        file_path = item['values'][1]  # path column
        file_name = item['values'][0]  # name column
        
        if not file_path:  # It's a folder
            messagebox.showwarning("Invalid Selection", "Cannot view a folder")
            return
        
        self.current_file_path = file_path
        self.selected_file_label.config(text=f"Viewing: {file_name}")
        
        self.start_loading("Loading file content...")
        
        def load_content_task():
            try:
                response = self.supabase.storage.from_(self.bucket_name).download(file_path)
                content = response.decode('utf-8')
                
                self.root.after(0, lambda: self.display_file_content(content, item['values']))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.load_content_error(str(e)))
        
        threading.Thread(target=load_content_task, daemon=True).start()
    
    def display_file_content(self, content, file_info):
        """Display file content in editor"""
        self.stop_loading()
        
        # Update file info
        self.file_info_text.config(state="normal")
        self.file_info_text.delete(1.0, tk.END)
        info_text = f"Name: {file_info[0]}\nPath: {file_info[1]}\nSize: {file_info[2]}\nModified: {file_info[3]}"
        self.file_info_text.insert(1.0, info_text)
        self.file_info_text.config(state="disabled")
        
        # Update editor
        self.file_editor.delete(1.0, tk.END)
        self.file_editor.insert(1.0, content)
        
        self.update_status(f"Loaded: {file_info[0]}")
    
    def load_content_error(self, error_msg):
        """Handle content loading error"""
        self.stop_loading()
        self.update_status("Failed to load content")
        messagebox.showerror("Load Error", f"Failed to load file content: {error_msg}")
    
    def save_file_content(self):
        """Save edited content back to Supabase"""
        if not self.current_file_path:
            messagebox.showwarning("No File", "No file is currently loaded")
            return
        
        content = self.file_editor.get(1.0, tk.END).encode('utf-8')
        
        self.start_loading("Saving changes...")
        
        def save_task():
            try:
                import io
                file_like = io.BytesIO(content)
                
                result = self.supabase.storage.from_(self.bucket_name).update(
                    file=file_like,
                    path=self.current_file_path,
                    file_options={"content-type": "text/markdown"}
                )
                
                self.root.after(0, lambda: self.save_complete())
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.save_error(str(e)))
        
        threading.Thread(target=save_task, daemon=True).start()
    
    def save_complete(self):
        """Handle successful save"""
        self.stop_loading()
        self.update_status("Changes saved successfully")
        messagebox.showinfo("Success", "File saved successfully")
        self.refresh_file_list()
    
    def save_error(self, error_msg):
        """Handle save error"""
        self.stop_loading()
        self.update_status("Save failed")
        messagebox.showerror("Save Error", f"Failed to save file: {error_msg}")
    
    def reload_file_content(self):
        """Reload current file content"""
        if self.current_file_path:
            self.view_file()
    
    def delete_file(self):
        """Delete selected file"""
        selected = self.files_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a file to delete")
            return
        
        item = self.files_tree.item(selected[0])
        file_path = item['values'][1]  # path column
        file_name = item['values'][0]  # name column
        
        if not file_path:  # It's a folder
            messagebox.showwarning("Invalid Selection", "Cannot delete a folder this way")
            return
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirm Delete", 
            f"Are you sure you want to delete '{file_name}'?\nThis action cannot be undone."
        )
        
        if not result:
            return
        
        self.start_loading("Deleting file...")
        
        def delete_task():
            try:
                result = self.supabase.storage.from_(self.bucket_name).remove([file_path])
                self.root.after(0, lambda: self.delete_complete(file_name))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.delete_error(str(e)))
        
        threading.Thread(target=delete_task, daemon=True).start()
    
    def delete_complete(self, file_name):
        """Handle successful deletion"""
        self.stop_loading()
        self.update_status(f"Deleted: {file_name}")
        messagebox.showinfo("Success", f"File '{file_name}' deleted successfully")
        
        # Clear editor if deleted file was being viewed
        if self.current_file_path:
            self.current_file_path = None
            self.selected_file_label.config(text="No file selected")
            self.file_editor.delete(1.0, tk.END)
            self.file_info_text.config(state="normal")
            self.file_info_text.delete(1.0, tk.END)
            self.file_info_text.config(state="disabled")
        
        self.refresh_file_list()
    
    def delete_error(self, error_msg):
        """Handle deletion error"""
        self.stop_loading()
        self.update_status("Delete failed")
        messagebox.showerror("Delete Error", f"Failed to delete file: {error_msg}")
    
    def rename_file(self):
        """Rename selected file"""
        selected = self.files_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a file to rename")
            return
        
        item = self.files_tree.item(selected[0])
        old_path = item['values'][1]  # path column
        old_name = item['values'][0]  # name column
        
        if not old_path:  # It's a folder
            messagebox.showwarning("Invalid Selection", "Cannot rename folders")
            return
        
        # Get new name
        new_name = tk.simpledialog.askstring(
            "Rename File",
            f"Enter new name for '{old_name}':",
            initialvalue=old_name
        )
        
        if not new_name or new_name == old_name:
            return
        
        # Create new path
        path_parts = old_path.split('/')
        path_parts[-1] = new_name
        new_path = '/'.join(path_parts)
        
        self.start_loading("Renaming file...")
        
        def rename_task():
            try:
                # Download content
                content = self.supabase.storage.from_(self.bucket_name).download(old_path)
                
                # Upload with new name
                import io
                file_like = io.BytesIO(content)
                self.supabase.storage.from_(self.bucket_name).upload(
                    file=file_like,
                    path=new_path,
                    file_options={"content-type": "text/markdown"}
                )
                
                # Delete old file
                self.supabase.storage.from_(self.bucket_name).remove([old_path])
                
                self.root.after(0, lambda: self.rename_complete(old_name, new_name))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.rename_error(str(e)))
        
        threading.Thread(target=rename_task, daemon=True).start()
    
    def rename_complete(self, old_name, new_name):
        """Handle successful rename"""
        self.stop_loading()
        self.update_status(f"Renamed: {old_name} → {new_name}")
        messagebox.showinfo("Success", f"File renamed from '{old_name}' to '{new_name}'")
        self.refresh_file_list()
    
    def rename_error(self, error_msg):
        """Handle rename error"""
        self.stop_loading()
        self.update_status("Rename failed")
        messagebox.showerror("Rename Error", f"Failed to rename file: {error_msg}")
    
    def copy_url(self):
        """Copy public URL to clipboard"""
        selected = self.files_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a file to copy URL")
            return
        
        item = self.files_tree.item(selected[0])
        url = item['values'][4]  # url column
        
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.update_status("URL copied to clipboard")
            messagebox.showinfo("Success", "Public URL copied to clipboard")
        else:
            messagebox.showwarning("No URL", "No public URL available for this item")
    
    def create_folder(self):
        """Create a new folder by uploading a placeholder file"""
        folder_path = tk.simpledialog.askstring(
            "Create Folder",
            "Enter folder path (e.g., 'articles' or 'posts/drafts'):"
        )
        
        if not folder_path:
            return
        
        # Create placeholder file in folder
        placeholder_path = f"{folder_path}/.gitkeep"
        
        self.start_loading("Creating folder...")
        
        def create_folder_task():
            try:
                import io
                placeholder_content = io.BytesIO(b"# This folder was created by MDX Manager")
                
                result = self.supabase.storage.from_(self.bucket_name).upload(
                    file=placeholder_content,
                    path=placeholder_path,
                    file_options={"content-type": "text/plain"}
                )
                
                self.root.after(0, lambda: self.folder_create_complete(folder_path))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.folder_create_error(str(e)))
        
        threading.Thread(target=create_folder_task, daemon=True).start()
    
    def folder_create_complete(self, folder_path):
        """Handle successful folder creation"""
        self.stop_loading()
        self.update_status(f"Created folder: {folder_path}")
        messagebox.showinfo("Success", f"Folder '{folder_path}' created successfully")
        self.refresh_file_list()
    
    def folder_create_error(self, error_msg):
        """Handle folder creation error"""
        self.stop_loading()
        self.update_status("Folder creation failed")
        messagebox.showerror("Folder Error", f"Failed to create folder: {error_msg}")
    
    def refresh_file_list(self):
        """Refresh the file list from Supabase"""
        self.start_loading("Loading files...")
        
        def load_files_task():
            try:
                files = self.supabase.storage.from_(self.bucket_name).list()
                self.root.after(0, lambda: self.display_files(files))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.load_files_error(str(e)))
        
        threading.Thread(target=load_files_task, daemon=True).start()
    
    def display_files(self, files):
        """Enhanced display files method with better folder handling"""
        self.stop_loading()
        
        # Clear existing items
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        # Dictionary to store folder tree items
        folders_in_tree = {}
        
        # First pass: Create all folders
        all_folder_paths = set()
        
        # Extract all folder paths from file paths
        for file_info in files:
            full_path = file_info.get('name', '')
            if not full_path or full_path.endswith('.emptyFolderPlaceholder'):
                continue
                
            # Check if this is a folder object (no 'id' field)
            is_folder_object = file_info.get('id') is None
            if is_folder_object:
                all_folder_paths.add(full_path)
            elif '/' in full_path:
                # Extract folder path from file path
                path_parts = full_path.split('/')[:-1]  # Remove filename
                for i in range(len(path_parts)):
                    folder_path = '/'.join(path_parts[:i+1])
                    all_folder_paths.add(folder_path)
        
        # Create folder tree structure
        sorted_folders = sorted(all_folder_paths, key=lambda x: (x.count('/'), x))
        
        for folder_path in sorted_folders:
            if folder_path in folders_in_tree:
                continue
                
            parts = folder_path.split('/')
            folder_name = parts[-1]
            
            # Determine parent
            parent_item_id = ""
            if len(parts) > 1:
                parent_path = '/'.join(parts[:-1])
                parent_item_id = folders_in_tree.get(parent_path, "")
            
            # Get saved folder state (default to False for collapsed)
            is_open = self.folder_states.get(folder_path, False)
            
            # Choose icon based on state
            folder_icon = "📂" if is_open else "📁"
            
            folder_item_id = self.files_tree.insert(
                parent_item_id,
                "end",
                text=folder_icon,
                values=(folder_name, folder_path, "", "", ""),
                tags=("folder",),
                open=is_open
            )
            folders_in_tree[folder_path] = folder_item_id
        
        # Second pass: Add files to their respective folders
        for file_info in files:
            full_path = file_info.get('name', '')
            
            # Skip folder objects and placeholder files
            if (not full_path or 
                full_path.endswith('.emptyFolderPlaceholder') or 
                file_info.get('id') is None):
                continue
            
            # Determine file name and parent folder
            if '/' in full_path:
                parts = full_path.split('/')
                file_name = parts[-1]
                parent_path = '/'.join(parts[:-1])
                parent_item_id = folders_in_tree.get(parent_path, "")
            else:
                file_name = full_path
                parent_item_id = ""
            
            # Get file metadata
            metadata = file_info.get('metadata', {})
            file_size = metadata.get('size', 0)
            size = self.format_file_size(file_size)
            modified = self.format_date(file_info.get('updated_at', ''))
            
            # Get public URL
            try:
                url_response = self.supabase.storage.from_(self.bucket_name).get_public_url(full_path)
                public_url = url_response if isinstance(url_response, str) else ""
            except:
                public_url = ""
            
            # Insert file
            self.files_tree.insert(
                parent_item_id,
                "end",
                text="📄",
                values=(file_name, full_path, size, modified, public_url),
                tags=("file",)
            )
        
        # Configure tag styles
        self.files_tree.tag_configure("folder", background="#f0f8ff")
        self.files_tree.tag_configure("file", background="white")
        
        self.update_status(f"Loaded {len(files)} items")

    def setup_tree_events(self):
        """Setup additional tree events for folder handling"""
        # Bind tree open/close events
        self.files_tree.bind("<<TreeviewOpen>>", self.on_tree_open)
        self.files_tree.bind("<<TreeviewClose>>", self.on_tree_close)
        
        # Also handle single-click selection for visual feedback
        self.files_tree.bind("<Button-1>", self.on_tree_click)

    def on_tree_click(self, event):
        """Handle single click to update folder icons"""
        item_id = self.files_tree.identify_row(event.y)
        if not item_id:
            return
        
        item = self.files_tree.item(item_id)
        if "folder" in item.get('tags', []):
            # Check if click was on the triangle (expand/collapse area)
            region = self.files_tree.identify_region(event.x, event.y)
            if region == "tree":
                # This is a click on the triangle, let the default handler manage it
                # We'll update the icon in the TreeviewOpen/Close events
                pass

    # Modified create_widgets method - add this line after binding the existing events:
    def bind_additional_events(self):
        """Call this after create_widgets to bind additional events"""
        # Remove the old double-click binding and add the new one
        self.files_tree.unbind("<Double-1>")
        self.files_tree.bind("<Double-1>", self.on_file_double_click)
        
        # Setup tree events
        self.setup_tree_events()

    def toggle_folder(self, item_id):
        """Toggle folder expand/collapse state"""
        current_state = self.files_tree.item(item_id, 'open')
        new_state = not current_state
        self.files_tree.item(item_id, open=new_state)
        
        # Update icon and save state
        item = self.files_tree.item(item_id)
        folder_path = item['values'][1]
        self.folder_states[folder_path] = new_state
        
        if new_state:
            self.files_tree.item(item_id, text="📂")
        else:
            self.files_tree.item(item_id, text="📁")
        
    
    def upload_file_to_folder(self, folder_path):
        """Upload file to specific folder"""
        file_path = filedialog.askopenfilename(
            title="Select File to Upload",
            filetypes=[("MDX files", "*.mdx"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        filename = os.path.basename(file_path)
        remote_path = f"{folder_path}/{filename}"
        
        # Use existing upload logic but with predefined path
        self.start_loading("Uploading file...")
        
        def upload_task():
            try:
                with open(file_path, "rb") as f:
                    result = self.supabase.storage.from_(self.bucket_name).upload(
                        file=f,
                        path=remote_path,
                        file_options={"content-type": "text/markdown"}
                    )
                
                self.root.after(0, lambda: self.upload_complete(result, remote_path))
                
            except StorageApiError as e:
                if "already exists" in str(e):
                    self.root.after(0, lambda: self.handle_file_exists(file_path, remote_path))
                else:
                    self.root.after(0, lambda e=e: self.upload_error(str(e)))
            except Exception as e:
                self.root.after(0, lambda e=e: self.upload_error(str(e)))
        
        threading.Thread(target=upload_task, daemon=True).start()

    def create_subfolder(self, parent_folder):
        """Create subfolder within existing folder"""
        subfolder_name = tk.simpledialog.askstring(
            "Create Subfolder",
            f"Enter subfolder name within '{parent_folder}':"
        )
        
        if not subfolder_name:
            return
        
        folder_path = f"{parent_folder}/{subfolder_name}"
        placeholder_path = f"{folder_path}/.gitkeep"
        
        self.start_loading("Creating subfolder...")
        
        def create_task():
            try:
                import io
                placeholder_content = io.BytesIO(b"# Subfolder created by MDX Manager")
                
                result = self.supabase.storage.from_(self.bucket_name).upload(
                    file=placeholder_content,
                    path=placeholder_path,
                    file_options={"content-type": "text/plain"}
                )
                
                self.root.after(0, lambda: self.folder_create_complete(folder_path))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.folder_create_error(str(e)))
        
        threading.Thread(target=create_task, daemon=True).start()
    
    def load_files_error(self, error_msg):
        """Handle file loading error"""
        self.stop_loading()
        self.update_status("Failed to load files")
        messagebox.showerror("Load Error", f"Failed to load files: {error_msg}")
    
    def filter_files(self, *args):
        """Filter files based on search query"""
        query = self.search_var.get().lower()
        
        def filter_item(item):
            values = self.files_tree.item(item, 'values')
            name = values[0].lower() if values and len(values) > 0 else ""
            path = values[1].lower() if values and len(values) > 1 else ""
            
            # Check if item matches query
            matches = query == "" or query in name or query in path
            
            # Check children
            children = self.files_tree.get_children(item)
            children_match = False
            
            for child in children:
                if filter_item(child):
                    children_match = True
            
            # Show/hide item based on match
            if matches or children_match:
                self.files_tree.reattach(item, self.files_tree.parent(item), 'end')
                return True
            else:
                self.files_tree.detach(item)
                return False
        
        # Filter all root items
        for item in self.files_tree.get_children():
            filter_item(item)
    
    # Event handlers
    
    def on_file_double_click(self, event):
        """Handle double-click on file or folder"""
        selected = self.files_tree.selection()
        if not selected:
            return
        
        item = self.files_tree.item(selected[0])
        
        # Check if it's a folder
        if "folder" in item.get('tags', []):
            # Toggle folder open/closed state
            current_state = self.files_tree.item(selected[0], 'open')
            new_state = not current_state
            self.files_tree.item(selected[0], open=new_state)
            
            # Save the folder state
            folder_path = item['values'][1]  # Full path of the folder
            self.folder_states[folder_path] = new_state
            
            # Update folder icon based on state
            if new_state:
                self.files_tree.item(selected[0], text="📂")  # Open folder
            else:
                self.files_tree.item(selected[0], text="📁")  # Closed folder
        
        # If it's a file, open it for viewing
        elif "file" in item.get('tags', []) and item['values'][1]:
            self.view_file()

    def on_tree_open(self, event):
        """Handle folder opening via keyboard or click on triangle"""
        selected = self.files_tree.selection()
        if not selected:
            return
        
        item_id = selected[0]
        item = self.files_tree.item(item_id)
        
        if "folder" in item.get('tags', []):
            folder_path = item['values'][1]
            self.folder_states[folder_path] = True
            self.files_tree.item(item_id, text="📂")  # Open folder icon

    def on_tree_close(self, event):
        """Handle folder closing via keyboard or click on triangle"""
        selected = self.files_tree.selection()
        if not selected:
            return
        
        item_id = selected[0]
        item = self.files_tree.item(item_id)
        
        if "folder" in item.get('tags', []):
            folder_path = item['values'][1]
            self.folder_states[folder_path] = False
            self.files_tree.item(item_id, text="📁")  # Closed folder icon
    
    def show_context_menu(self, event):
        """Show context menu on right-click with folder-specific options"""
        item_id = self.files_tree.identify_row(event.y)
        if not item_id:
            return
            
        self.files_tree.selection_set(item_id)
        item = self.files_tree.item(item_id)
        
        # Clear existing menu
        self.context_menu.delete(0, tk.END)
        
        if "folder" in item.get('tags', []):
            # Folder context menu
            folder_path = item['values'][1]
            is_open = self.files_tree.item(item_id, 'open')
            
            if is_open:
                self.context_menu.add_command(label="📁 Collapse Folder", 
                                            command=lambda: self.toggle_folder(item_id))
            else:
                self.context_menu.add_command(label="📂 Expand Folder", 
                                            command=lambda: self.toggle_folder(item_id))
            
            self.context_menu.add_separator()
            self.context_menu.add_command(label="📄 Upload File Here", 
                                        command=lambda: self.upload_file_to_folder(folder_path))
            self.context_menu.add_command(label="📂 Create Subfolder", 
                                        command=lambda: self.create_subfolder(folder_path))
            self.context_menu.add_separator()
            self.context_menu.add_command(label="🏷️ Rename Folder", 
                                        command=lambda: self.rename_folder(item_id))
            self.context_menu.add_command(label="🗑️ Delete Folder", 
                                        command=lambda: self.delete_folder(item_id))
        else:
            # File context menu (existing)
            self.context_menu.add_command(label="📄 View Content", command=self.view_file)
            self.context_menu.add_command(label="📥 Download", command=self.download_file)
            self.context_menu.add_command(label="✏️ Rename", command=self.rename_file)
            self.context_menu.add_command(label="🔗 Copy URL", command=self.copy_url)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="🗑️ Delete", command=self.delete_file)
        
        self.context_menu.post(event.x_root, event.y_root)
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def format_date(self, date_string):
        """Format date string"""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return date_string[:16] if date_string else ""
    
    def start_loading(self, message="Loading..."):
        """Start loading animation"""
        self.update_status(message)
        self.progress_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        self.progress_bar.start(10)
        
        # Disable main buttons during operation
        self.upload_btn.config(state="disabled")
        self.refresh_btn.config(state="disabled")
        self.create_folder_btn.config(state="disabled")
    
    def stop_loading(self):
        """Stop loading animation"""
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        
        # Re-enable buttons
        self.upload_btn.config(state="normal")
        self.refresh_btn.config(state="normal")
        self.create_folder_btn.config(state="normal")
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_bar.config(text=f"{datetime.now().strftime('%H:%M:%S')} - {message}")