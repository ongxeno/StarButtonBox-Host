# system_tray_handler.py
# Manages the system tray icon, its menu, and actions.

import pystray
from PIL import Image # For loading the icon image
import threading
import logging
import sys # To help with PyInstaller pathing if needed
import os  # To help with PyInstaller pathing if needed

logger = logging.getLogger("StarButtonBoxServerTray")

# Global variable to hold the pystray.Icon instance
tray_icon_object = None
# Global variable to hold the thread running the tray icon
tray_thread = None

def _get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def _on_show_hide_window(icon, item, root_window):
    """Callback to show or hide the main application window."""
    if root_window:
        if root_window.state() == 'withdrawn':
            logger.info("Tray: Showing main window.")
            root_window.deiconify()
            root_window.lift() # Bring to front
            root_window.focus_force() # Force focus
        else:
            logger.info("Tray: Hiding main window (withdrawing).")
            root_window.withdraw()
    else:
        logger.warning("Tray: Root window not available for show/hide.")

def _on_start_server(icon, item, gui_app_instance):
    """Callback to start the server via the GUI app instance."""
    if gui_app_instance:
        logger.info("Tray: 'Start Server' clicked.")
        # Ensure this is called on the main Tkinter thread if it modifies GUI directly
        # or if _toggle_server_state itself handles threading appropriately.
        # For now, assuming _toggle_server_state can be called like this.
        gui_app_instance.root.after(0, lambda: gui_app_instance._toggle_server_state(start_server=True))
    else:
        logger.warning("Tray: GUI app instance not available for starting server.")

def _on_stop_server(icon, item, gui_app_instance):
    """Callback to stop the server via the GUI app instance."""
    if gui_app_instance:
        logger.info("Tray: 'Stop Server' clicked.")
        gui_app_instance.root.after(0, lambda: gui_app_instance._toggle_server_state(start_server=False))
    else:
        logger.warning("Tray: GUI app instance not available for stopping server.")

def _on_quit_application(icon, item, root_window, gui_app_instance):
    """Callback to quit the application."""
    logger.info("Tray: 'Quit' clicked. Stopping server and exiting.")
    if gui_app_instance:
        # Ensure server stop is handled (non-blockingly if possible, but _on_closing handles it)
        # We directly call the GUI's closing mechanism which should handle server stop
        # and then destroy the window.
        gui_app_instance.root.after(0, gui_app_instance._perform_full_quit)
    
    if icon: # icon is the pystray.Icon object
        icon.stop()
    logger.info("Tray: Icon stopped.")


def run_tray_icon(root_window, gui_app_instance, icon_path="tray_icon.png"):
    """
    Creates and runs the system tray icon in a separate daemon thread.

    Args:
        root_window: The main Tkinter window (tk.Tk instance).
        gui_app_instance: The instance of the ServerGUI class.
        icon_path (str): Path to the icon image file.
    """
    global tray_icon_object, tray_thread

    if tray_thread and tray_thread.is_alive():
        logger.info("Tray: Icon thread already running.")
        return

    try:
        actual_icon_path = _get_resource_path(icon_path)
        logger.info(f"Tray: Attempting to load icon from: {actual_icon_path}")
        image = Image.open(actual_icon_path)
    except FileNotFoundError:
        logger.error(f"Tray: Icon file '{actual_icon_path}' not found. Cannot create tray icon.")
        if gui_app_instance:
            gui_app_instance._log_to_gui(f"ERROR: Tray icon file '{icon_path}' not found.")
        return
    except Exception as e:
        logger.error(f"Tray: Error loading icon image: {e}")
        if gui_app_instance:
            gui_app_instance._log_to_gui(f"ERROR: Could not load tray icon: {e}")
        return

    # Define menu items
    # Lambdas are used to pass the correct arguments to callbacks
    menu = pystray.Menu(
        pystray.MenuItem(
            "Show/Hide Settings",
            lambda icon, item: _on_show_hide_window(icon, item, root_window),
            default=True # Double-clicking the icon will trigger this
        ),
        pystray.MenuItem(
            "Start Server",
            lambda icon, item: _on_start_server(icon, item, gui_app_instance)
        ),
        pystray.MenuItem(
            "Stop Server",
            lambda icon, item: _on_stop_server(icon, item, gui_app_instance)
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Quit StarButtonBox Server",
            lambda icon, item: _on_quit_application(icon, item, root_window, gui_app_instance)
        )
    )

    tray_icon_object = pystray.Icon("StarButtonBoxServer", image, "StarButtonBox Server", menu)
    
    # pystray's run() is blocking, so it needs its own thread.
    # Make it a daemon thread so it exits when the main application exits.
    def run_icon_thread():
        logger.info("Tray: Starting icon thread.")
        try:
            tray_icon_object.run()
        except Exception as e:
            logger.error(f"Tray: Exception in icon thread: {e}")
        finally:
            logger.info("Tray: Icon thread finished.")

    tray_thread = threading.Thread(target=run_icon_thread, daemon=True, name="SystemTrayThread")
    tray_thread.start()
    logger.info("Tray: System tray icon thread initiated.")

def stop_tray_icon():
    """Stops the system tray icon if it's running."""
    global tray_icon_object, tray_thread
    logger.info("Tray: Attempting to stop tray icon...")
    if tray_icon_object:
        tray_icon_object.stop()
        tray_icon_object = None
        logger.info("Tray: pystray icon object stopped.")
    
    if tray_thread and tray_thread.is_alive():
        logger.info("Tray: Waiting for tray thread to join...")
        tray_thread.join(timeout=1.0) # Wait for the thread to finish
        if tray_thread.is_alive():
            logger.warning("Tray: Tray thread did not join in time.")
        else:
            logger.info("Tray: Tray thread joined.")
    tray_thread = None

if __name__ == '__main__':
    # This is a simple test for the tray icon functionality itself.
    # It won't interact with a full GUI app here.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Testing system_tray_handler.py directly...")

    # Create a dummy root window and app instance for testing callbacks
    class DummyGUI:
        def __init__(self, root):
            self.root = root
        def _toggle_server_state(self, start_server):
            print(f"DummyGUI: _toggle_server_state called with start_server={start_server}")
            logger.info(f"DummyGUI: Server state toggle: {start_server}")
        def _perform_full_quit(self):
            print("DummyGUI: _perform_full_quit called. Stopping tray and destroying root.")
            logger.info("DummyGUI: Performing full quit.")
            stop_tray_icon() # Ensure icon is stopped
            if self.root:
                self.root.destroy()
        def _log_to_gui(self, message): # Dummy log callback
            print(f"DUMMY_GUI_LOG: {message}")


    dummy_root = tk.Tk()
    dummy_root.title("Tray Test Dummy Window")
    dummy_root.geometry("300x100")
    ttk.Label(dummy_root, text="This is a dummy window for tray testing.\nClose this window or use tray 'Quit' to exit test.").pack(pady=20)
    
    dummy_gui_app = DummyGUI(dummy_root)

    # Ensure you have a 'tray_icon.png' in the same directory as this script for this test to work.
    # If not, pystray might use a default icon or fail.
    icon_file = "tray_icon.png" 
    if not os.path.exists(_get_resource_path(icon_file)):
        logger.warning(f"'{icon_file}' not found for direct test. pystray might use a default icon or error.")


    def on_dummy_close():
        logger.info("Dummy window close button clicked.")
        dummy_gui_app._perform_full_quit()

    dummy_root.protocol("WM_DELETE_WINDOW", on_dummy_close)

    run_tray_icon(dummy_root, dummy_gui_app, icon_file)
    
    print("Dummy Tkinter main loop starting. Right-click tray icon or close dummy window.")
    dummy_root.mainloop()
    
    # Ensure tray icon thread is cleaned up if mainloop exits some other way
    if tray_thread and tray_thread.is_alive():
         logger.info("Main test loop exited, ensuring tray icon is stopped.")
         stop_tray_icon()
    logger.info("Direct test finished.")
