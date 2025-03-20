#!/usr/bin/env python3
import os
import sys
import sqlite3
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
import zlib
import re

class CursorChatViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Cursor Chat Viewer")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Set the default database path
        self.default_path = os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/state.vscdb")
        
        self.db_path = tk.StringVar(value=self.default_path)
        self.setup_ui()
        self.chat_data = []
        
    def setup_ui(self):
        # Main frame 
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Database path frame
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(path_frame, text="Database Path:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(path_frame, textvariable=self.db_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Browse", command=self.browse_db).pack(side=tk.LEFT, padx=5)
        ttk.Button(path_frame, text="Connect", command=self.load_chats).pack(side=tk.LEFT, padx=5)
        
        # Split view with a panedwindow
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left frame - List of chats
        left_frame = ttk.Frame(paned, padding="5")
        paned.add(left_frame, weight=1)
        
        # Chat list controls
        list_control_frame = ttk.Frame(left_frame)
        list_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(list_control_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.insert(0, "Search...")
        search_entry.bind("<FocusIn>", lambda e: search_entry.delete(0, tk.END) if search_entry.get() == "Search..." else None)
        search_entry.bind("<FocusOut>", lambda e: search_entry.insert(0, "Search...") if search_entry.get() == "" else None)
        search_entry.bind("<Return>", lambda e: self.search_chats())
        
        ttk.Button(list_control_frame, text="🔍", width=3, command=self.search_chats).pack(side=tk.LEFT, padx=5)
        
        # Chat list with scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_list = ttk.Treeview(list_frame, columns=("id", "date", "title"), show="headings")
        self.chat_list.heading("id", text="ID")
        self.chat_list.heading("date", text="Date")
        self.chat_list.heading("title", text="Title")
        self.chat_list.column("id", width=50)
        self.chat_list.column("date", width=120)
        self.chat_list.column("title", width=200)
        self.chat_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.chat_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_list.configure(yscrollcommand=scrollbar.set)
        
        self.chat_list.bind("<<TreeviewSelect>>", self.on_chat_select)
        
        # Right frame - Chat content
        right_frame = ttk.Frame(paned, padding="5")
        paned.add(right_frame, weight=2)
        
        # Content controls
        content_control_frame = ttk.Frame(right_frame)
        content_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(content_control_frame, text="Export JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(content_control_frame, text="Export Text", command=self.export_text).pack(side=tk.LEFT, padx=5)
        ttk.Button(content_control_frame, text="Format as Chat", command=self.format_as_chat).pack(side=tk.LEFT, padx=5)
        
        # Text area with scrollbar
        self.content_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=("Courier New", 11))
        self.content_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Connect to a database to start.")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Automatically load chats if default path exists
        if os.path.exists(self.default_path):
            self.root.after(100, self.load_chats)
    
    def browse_db(self):
        db_path = filedialog.askopenfilename(
            title="Select Cursor Database",
            filetypes=[("SQLite Database", "*.vscdb"), ("All Files", "*.*")],
            initialdir=os.path.dirname(self.db_path.get())
        )
        if db_path:
            self.db_path.set(db_path)
    
    def search_chats(self):
        search_term = self.search_var.get().lower()
        if not search_term or search_term == "search...":
            return
        
        # Clear current selection
        self.chat_list.selection_remove(self.chat_list.selection())
        
        for i, (chat_id, date_str, key, value, title) in enumerate(self.chat_data):
            # Try to get content as text
            try:
                if value[:2] == b'x\x9c':
                    text_content = zlib.decompress(value).decode('utf-8', errors='ignore')
                else:
                    text_content = value.decode('utf-8', errors='ignore')
                
                if (search_term in text_content.lower() or 
                    search_term in chat_id.lower() or 
                    search_term in title.lower()):
                    self.chat_list.see(str(i))
                    self.chat_list.selection_set(str(i))
                    # Show the content
                    self.on_chat_select(None)
                    return  # Stop at first match
            except Exception:
                continue
        
        messagebox.showinfo("Search", "No matches found.")
    
    def extract_date_from_json(self, json_str):
        try:
            data = json.loads(json_str)
            # Look for timestamp or date fields
            if isinstance(data, dict):
                for key in ['createdAt', 'timestamp', 'date', 'time']:
                    if key in data and data[key]:
                        try:
                            # Try to parse as timestamp (seconds or milliseconds)
                            timestamp = int(data[key])
                            if timestamp > 1000000000000:  # milliseconds
                                timestamp /= 1000
                            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
                        except:
                            # Try to parse as string
                            if isinstance(data[key], str) and len(data[key]) > 5:
                                return data[key]
            
            # Try to find any messages with timestamps
            if isinstance(data, dict) and 'messages' in data and isinstance(data['messages'], list) and data['messages']:
                first_msg = data['messages'][0]
                if isinstance(first_msg, dict) and 'timestamp' in first_msg:
                    timestamp = int(first_msg['timestamp'])
                    if timestamp > 1000000000000:  # milliseconds
                        timestamp /= 1000
                    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
        except:
            pass
        return "Unknown"
    
    def extract_title_from_json(self, json_str):
        try:
            data = json.loads(json_str)
            # Look for title fields
            if isinstance(data, dict):
                for key in ['title', 'name', 'subject']:
                    if key in data and data[key] and isinstance(data[key], str):
                        return data[key][:40]  # Truncate long titles
                
                # Try to extract from first message
                if 'messages' in data and isinstance(data['messages'], list) and data['messages']:
                    first_msg = data['messages'][0]
                    if isinstance(first_msg, dict) and 'content' in first_msg and isinstance(first_msg['content'], str):
                        # Extract first line or first N characters
                        content = first_msg['content']
                        first_line = content.split('\n')[0]
                        return first_line[:40] + ('...' if len(first_line) > 40 else '')
        except:
            pass
        return ""
    
    def load_chats(self):
        try:
            # Clear existing data
            self.chat_list.delete(*self.chat_list.get_children())
            self.content_text.delete(1.0, tk.END)
            self.chat_data = []
            
            # Connect to the database
            conn = sqlite3.connect(self.db_path.get())
            cursor = conn.cursor()
            
            # Query all chat records
            cursor.execute("SELECT key, value FROM cursorDiskKV")
            rows = cursor.fetchall()
            
            # Filter and process chat records
            chat_rows = []
            for key, value in rows:
                # Only include items that look like chat records
                if key.startswith('chat:'):
                    try:
                        chat_id = key.replace('chat:', '')
                        
                        # Try to decompress and extract metadata
                        try:
                            if value[:2] == b'x\x9c':  # zlib magic number
                                decompressed = zlib.decompress(value)
                                json_str = decompressed.decode('utf-8', errors='ignore')
                                date_str = self.extract_date_from_json(json_str)
                                title = self.extract_title_from_json(json_str)
                            else:
                                json_str = value.decode('utf-8', errors='ignore')
                                date_str = self.extract_date_from_json(json_str)
                                title = self.extract_title_from_json(json_str)
                        except:
                            date_str = "Unknown"
                            title = ""
                        
                        chat_rows.append((chat_id, date_str, key, value, title))
                    except Exception:
                        # Skip records that can't be processed
                        pass
            
            # Sort by date (most recent first) if date is available
            chat_rows.sort(key=lambda x: x[1] if x[1] != "Unknown" else "", reverse=True)
            self.chat_data = chat_rows
            
            # Add to treeview
            for i, (chat_id, date_str, key, _, title) in enumerate(chat_rows):
                self.chat_list.insert("", tk.END, values=(chat_id, date_str, title), iid=str(i))
            
            self.status_var.set(f"Loaded {len(chat_rows)} chat records")
            
            conn.close()
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to load chat records: {str(e)}")
    
    def on_chat_select(self, event):
        selected_items = self.chat_list.selection()
        if not selected_items:
            return
        
        try:
            index = int(selected_items[0])
            _, _, key, value, _ = self.chat_data[index]
            
            self.content_text.delete(1.0, tk.END)
            
            # Try to decode the BLOB data
            try:
                # First try to decompress with zlib if it looks compressed
                try:
                    if value[:2] == b'x\x9c':  # zlib magic number
                        value = zlib.decompress(value)
                except Exception:
                    pass
                
                # Try to decode as UTF-8 text
                text = value.decode('utf-8')
                
                # Check if it's JSON and format it
                try:
                    json_data = json.loads(text)
                    text = json.dumps(json_data, indent=2)
                except json.JSONDecodeError:
                    pass
                
                self.content_text.insert(tk.END, text)
            except UnicodeDecodeError:
                # If UTF-8 decoding fails, show hex representation
                hex_view = ' '.join(f'{b:02x}' for b in value[:1000])
                self.content_text.insert(tk.END, f"Binary data (showing first 1000 bytes):\n{hex_view}")
                if len(value) > 1000:
                    self.content_text.insert(tk.END, f"\n... {len(value) - 1000} more bytes ...")
            
            self.status_var.set(f"Viewing chat: {key}")
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to display chat content: {str(e)}")
    
    def format_as_chat(self):
        selected_items = self.chat_list.selection()
        if not selected_items:
            messagebox.showinfo("Format", "Please select a chat to format")
            return
        
        try:
            index = int(selected_items[0])
            _, _, key, value, _ = self.chat_data[index]
            
            self.content_text.delete(1.0, tk.END)
            
            # Try to decode the BLOB data
            try:
                # First try to decompress with zlib if it looks compressed
                try:
                    if value[:2] == b'x\x9c':  # zlib magic number
                        value = zlib.decompress(value)
                except Exception:
                    pass
                
                # Try to decode as UTF-8 text
                text = value.decode('utf-8')
                
                # Try to parse as JSON and format as chat
                try:
                    json_data = json.loads(text)
                    
                    # Format the chat content
                    formatted_text = []
                    
                    # Add title if available
                    if isinstance(json_data, dict):
                        if 'title' in json_data and json_data['title']:
                            formatted_text.append(f"Title: {json_data['title']}\n")
                        
                        # Process messages
                        if 'messages' in json_data and isinstance(json_data['messages'], list):
                            for msg in json_data['messages']:
                                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                                    role = msg['role'].upper()
                                    content = msg['content']
                                    
                                    # Add a timestamp if available
                                    timestamp_str = ""
                                    if 'timestamp' in msg:
                                        try:
                                            timestamp = int(msg['timestamp'])
                                            if timestamp > 1000000000000:  # milliseconds
                                                timestamp /= 1000
                                            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                                            timestamp_str = f" ({time_str})"
                                        except:
                                            pass
                                    
                                    formatted_text.append(f"[{role}{timestamp_str}]\n{content}\n\n")
                    
                    if formatted_text:
                        self.content_text.insert(tk.END, "\n".join(formatted_text))
                    else:
                        # Fall back to JSON if we couldn't format as chat
                        self.content_text.insert(tk.END, json.dumps(json_data, indent=2))
                except json.JSONDecodeError:
                    # Not valid JSON, show as is
                    self.content_text.insert(tk.END, text)
            except UnicodeDecodeError:
                # If UTF-8 decoding fails, show hex representation
                hex_view = ' '.join(f'{b:02x}' for b in value[:1000])
                self.content_text.insert(tk.END, f"Binary data (showing first 1000 bytes):\n{hex_view}")
                if len(value) > 1000:
                    self.content_text.insert(tk.END, f"\n... {len(value) - 1000} more bytes ...")
            
            self.status_var.set(f"Formatted chat: {key}")
        except Exception as e:
            self.status_var.set(f"Error formatting: {str(e)}")
            messagebox.showerror("Format Error", f"Failed to format chat content: {str(e)}")
    
    def export_json(self):
        selected_items = self.chat_list.selection()
        if not selected_items:
            messagebox.showinfo("Export", "Please select a chat to export")
            return
        
        try:
            index = int(selected_items[0])
            chat_id, _, key, value, _ = self.chat_data[index]
            
            # Get save path
            file_path = filedialog.asksaveasfilename(
                title="Export JSON",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"cursor_chat_{chat_id}.json"
            )
            
            if not file_path:
                return
            
            # Process data
            try:
                if value[:2] == b'x\x9c':
                    value = zlib.decompress(value)
                
                # Try to decode and format as JSON
                text = value.decode('utf-8')
                try:
                    json_data = json.loads(text)
                    formatted_json = json.dumps(json_data, indent=2)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(formatted_json)
                    
                    self.status_var.set(f"Exported to {file_path}")
                except json.JSONDecodeError:
                    # Just save as text if not valid JSON
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    self.status_var.set(f"Exported text to {file_path} (not valid JSON)")
            except UnicodeDecodeError:
                messagebox.showerror("Export Error", "Cannot export binary data as JSON")
        except Exception as e:
            self.status_var.set(f"Error exporting: {str(e)}")
            messagebox.showerror("Export Error", str(e))
    
    def export_text(self):
        selected_items = self.chat_list.selection()
        if not selected_items:
            messagebox.showinfo("Export", "Please select a chat to export")
            return
        
        try:
            index = int(selected_items[0])
            chat_id, _, key, value, _ = self.chat_data[index]
            
            # Get save path
            file_path = filedialog.asksaveasfilename(
                title="Export Text",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"cursor_chat_{chat_id}.txt"
            )
            
            if not file_path:
                return
            
            # Process data
            try:
                if value[:2] == b'x\x9c':
                    value = zlib.decompress(value)
                
                # Try to decode as text
                text = value.decode('utf-8')
                
                # If it's JSON, try to extract meaningful content
                try:
                    json_data = json.loads(text)
                    
                    # Process chat data into readable format if possible
                    if isinstance(json_data, dict) and 'messages' in json_data and isinstance(json_data['messages'], list):
                        messages = json_data['messages']
                        readable_text = []
                        
                        if 'title' in json_data and json_data['title']:
                            readable_text.append(f"Title: {json_data['title']}\n")
                        
                        for msg in messages:
                            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                                role = msg['role'].upper()
                                content = msg['content']
                                
                                # Add timestamp if available
                                timestamp_str = ""
                                if 'timestamp' in msg:
                                    try:
                                        timestamp = int(msg['timestamp'])
                                        if timestamp > 1000000000000:  # milliseconds
                                            timestamp /= 1000
                                        time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                                        timestamp_str = f" ({time_str})"
                                    except:
                                        pass
                                
                                readable_text.append(f"[{role}{timestamp_str}]\n{content}\n\n")
                        
                        text = '\n'.join(readable_text)
                except json.JSONDecodeError:
                    # Not JSON, keep as is
                    pass
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                self.status_var.set(f"Exported to {file_path}")
            except UnicodeDecodeError:
                # If binary, save as binary
                with open(file_path, 'wb') as f:
                    f.write(value)
                self.status_var.set(f"Exported binary data to {file_path}")
        except Exception as e:
            self.status_var.set(f"Error exporting: {str(e)}")
            messagebox.showerror("Export Error", str(e))

def main():
    root = tk.Tk()
    app = CursorChatViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main() 