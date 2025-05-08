# dialog_handler.py
# Handles triggering the browser opening for the PC import feature.
# Uses console output as the primary notification method.

import threading
import webbrowser
import sys

def _open_browser_task(url):
    """Prints instructions and attempts to open the browser."""
    print("\n--- Import Layout from PC ---", file=sys.stderr)
    print(f"Received request from Android device.", file=sys.stderr)
    print(f"Attempting to open URL in your browser:", file=sys.stderr)
    print(f"  {url}", file=sys.stderr)
    print(f"If the browser doesn't open, please copy and paste the URL above.", file=sys.stderr)
    print("-----------------------------", file=sys.stderr)
    sys.stdout.flush() # Ensure message is printed immediately

    try:
        success = webbrowser.open(url)
        if not success:
             print(f"Warning: webbrowser.open() reported failure. Manual copy/paste might be needed.", file=sys.stderr)
             sys.stdout.flush()
    except Exception as wb_e:
        print(f"Error attempting to open browser automatically: {wb_e}", file=sys.stderr)
        print("Please copy and paste the URL manually.", file=sys.stderr)
        sys.stdout.flush()

def trigger_pc_browser(url):
    """Prints instructions and opens the browser in a separate thread."""
    print(f"  -> Triggering PC browser import process for URL: {url}")
    sys.stdout.flush()
    # Run the browser opening in a separate thread to avoid blocking UDP listener
    # Although webbrowser.open is often non-blocking, doing it in a thread is safer.
    browser_thread = threading.Thread(target=_open_browser_task, args=(url,), name="BrowserOpenThread", daemon=True)
    browser_thread.start()

