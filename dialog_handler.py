# dialog_handler.py
# Handles displaying the Tkinter prompt for the PC import feature.

import threading
import webbrowser
import sys
import config # Import config to check TKINTER_AVAILABLE

# Import Tkinter conditionally
if config.TKINTER_AVAILABLE:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
else:
    tk = None # Set to None if not available
    ttk = None
    messagebox = None

def _show_prompt_dialog_internal(url):
    """Internal function to create and run the Tkinter dialog."""
    if not config.TKINTER_AVAILABLE:
        print("\n--- Import Layout from PC (Fallback) ---", file=sys.stderr)
        print(f"Please open this URL in your browser: {url}", file=sys.stderr)
        print("--------------------------------------", file=sys.stderr)
        sys.stdout.flush()
        return

    root = None # Initialize root
    try:
        # Create and immediately hide the root window
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        # Create the Toplevel dialog as a child of the hidden root
        dialog = tk.Toplevel(root)
        dialog.title("Import Layout from Device")
        dialog.attributes('-topmost', True)

        # Center the dialog
        dialog.update_idletasks()
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width // 2) - (dialog_width // 2)
        y = (screen_height // 2) - (dialog_height // 2)
        dialog.geometry(f'+{x}+{y}')

        # Dialog content
        frame = ttk.Frame(dialog, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        label = ttk.Label(frame, text="Android device wants to import a layout file.\nOpen browser to select file?", justify=tk.CENTER)
        label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        url_label = ttk.Label(frame, text="URL:", anchor=tk.W)
        url_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        url_entry = ttk.Entry(frame, width=50)
        url_entry.insert(0, url)
        url_entry.configure(state='readonly')
        url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        # Button Commands
        def open_and_close():
            print(f"    -> User accepted. Opening browser to: {url}")
            sys.stdout.flush()
            try: webbrowser.open(url)
            except Exception as wb_e: print(f"    -> Error opening browser: {wb_e}", file=sys.stderr); sys.stdout.flush()
            dialog.destroy()

        def cancel_and_close():
            print("    -> User cancelled browser open request.")
            sys.stdout.flush()
            dialog.destroy()

        open_button = ttk.Button(button_frame, text="Open Browser", command=open_and_close)
        open_button.pack(side=tk.LEFT, padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=cancel_and_close)
        cancel_button.pack(side=tk.LEFT, padx=5)

        # Make dialog modal and wait
        dialog.protocol("WM_DELETE_WINDOW", cancel_and_close)
        dialog.transient(root)
        dialog.grab_set()
        print("    -> Waiting for user interaction in dialog...")
        sys.stdout.flush()
        root.wait_window(dialog) # Wait for dialog to be destroyed
        print("    -> Dialog closed.")
        sys.stdout.flush()

    except tk.TclError as tcl_e:
         print(f"Tkinter TclError: {tcl_e}", file=sys.stderr)
         print("--- Fallback Instructions ---", file=sys.stderr); print(f"Please open this URL: {url}", file=sys.stderr); print("-----------------------------", file=sys.stderr); sys.stdout.flush()
    except Exception as e:
        print(f"Error showing Tkinter dialog: {e}", file=sys.stderr)
        print("--- Fallback Instructions ---", file=sys.stderr); print(f"Please open this URL: {url}", file=sys.stderr); print("-----------------------------", file=sys.stderr); sys.stdout.flush()
    finally:
        # Ensure the hidden root window is destroyed
        if root and root.winfo_exists():
            root.destroy()


def trigger_pc_browser(url):
    """Starts the Tkinter dialog in a separate thread."""
    print(f"  -> Received request to trigger PC browser import for URL: {url}")
    sys.stdout.flush()
    # Run the dialog in a separate thread so it doesn't block the main UDP listener
    dialog_thread = threading.Thread(target=_show_prompt_dialog_internal, args=(url,), daemon=True)
    dialog_thread.start()

