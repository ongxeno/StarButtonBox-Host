# server_gui.py
# Main application for the StarButtonBox Server GUI using Tkinter.

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue # For thread-safe GUI updates from server thread
import logging # To integrate with the logging setup in server.py
import socket # For _update_ip_display
import sys # For determining if running as packaged app
import os # For path operations
import argparse # For parsing command-line arguments

# Import other project modules
import config_manager
import server as server_control
import mdns_handler # Though not directly used, good to keep if server_control depends on it implicitly
import config # For default port, etc.
import system_tray_handler # New import for system tray

# Get the logger instance configured in server.py
logger = logging.getLogger("StarButtonBoxServer")

class ServerGUI:
    def __init__(self, root_tk, start_minimized_arg=False):
        self.root = root_tk
        self.root.title("StarButtonBox Server Control")
        self.root.geometry("700x550")
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing_window_button) # Changed method name for clarity

        # --- Variables to store settings and state ---
        self.settings = config_manager.load_settings()
        self.server_port_var = tk.StringVar(value=str(self.settings.get("server_port", config.COMMAND_PORT)))
        self.mdns_enabled_var = tk.BooleanVar(value=self.settings.get("mdns_enabled", True))
        self.autostart_enabled_var = tk.BooleanVar(value=self.settings.get("autostart_enabled", False))
        self.minimize_to_tray_on_exit_var = tk.BooleanVar(value=self.settings.get("minimize_to_tray_on_exit", False))
        self.start_minimized_to_tray_var = tk.BooleanVar(value=self.settings.get("start_minimized_to_tray", False))

        self.server_status_var = tk.StringVar(value="Server Stopped")
        self.server_ip_var = tk.StringVar(value="IP: N/A")
        self.port_status_display_var = tk.StringVar(value=f"Port: {self.server_port_var.get()}")
        self.mdns_status_display_var = tk.StringVar(value=f"mDNS: {'Active' if self.mdns_enabled_var.get() else 'Inactive'}")

        self.log_queue = queue.Queue()
        self.server_stop_thread = None

        self._initialize_widget_references()
        self._create_widgets()
        self._update_ip_display()
        self._setup_logging_to_gui()
        self.root.after(100, self._process_log_queue)

        icon_filename = "tray_icon.png"
        system_tray_handler.run_tray_icon(self.root, self, icon_filename)

        # --- Handle Start Minimized ---
        # Priority: 1. Command-line arg, 2. Saved setting
        should_start_minimized = False
        if start_minimized_arg: # Check command-line argument first
            logger.info("GUI: '--start-minimized' argument detected. Starting minimized.")
            self._log_to_gui("INFO: Starting minimized due to command-line argument.")
            should_start_minimized = True
        elif self.start_minimized_to_tray_var.get(): # Check saved setting
            logger.info("GUI: 'Start Minimized to Tray' setting is enabled. Starting minimized.")
            self._log_to_gui("INFO: Starting minimized due to saved setting.")
            should_start_minimized = True
        
        if should_start_minimized:
            # Withdraw after a very short delay to ensure window elements are created
            # and tray icon has a chance to initialize.
            self.root.after(100, self.root.withdraw) 
        else:
            # Ensure window is visible if not starting minimized
            self.root.deiconify()


        # --- Autostart Server Logic ---
        if self.autostart_enabled_var.get():
            executable_path = self.settings.get("executable_path_for_autostart")
            if executable_path and os.path.exists(executable_path):
                logger.info("Autostart enabled. Attempting to start server on GUI launch.")
                self._log_to_gui("INFO: Autostart enabled. Attempting to start server...")
                self._toggle_server_state(start_server=True)
            elif executable_path: # Path stored but doesn't exist
                logger.warning(f"Autostart enabled, but executable path '{executable_path}' not found. Server not started.")
                self._log_to_gui(f"WARN: Autostart: Executable path '{executable_path}' invalid or missing.")
                self._update_gui_for_server_state(is_running=False)
            else: # Autostart enabled but no path stored
                logger.warning("Autostart enabled, but no executable path stored. Server not started.")
                self._log_to_gui("WARN: Autostart: Executable path not configured.")
                self._update_gui_for_server_state(is_running=False)
        else: # Autostart not enabled in settings
            self._update_gui_for_server_state(is_running=False)


    def _initialize_widget_references(self):
        """Initializes all widget instance variables to None."""
        self.status_frame = None
        self.ip_label = None
        self.port_status_label = None
        self.mdns_status_label = None
        self.overall_status_label = None
        self.config_frame = None
        self.port_entry = None
        self.apply_port_button = None
        self.mdns_checkbutton = None
        self.autostart_checkbutton = None
        self.minimize_to_tray_checkbutton = None
        self.start_minimized_checkbutton = None # New widget reference
        self.start_stop_button = None
        self.log_frame = None
        self.log_text_area = None

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Status Section (as before)
        self.status_frame = ttk.LabelFrame(main_frame, text="Server Status", padding="10")
        self.status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.status_frame.columnconfigure(1, weight=1)
        self.ip_label = ttk.Label(self.status_frame, textvariable=self.server_ip_var)
        self.ip_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.port_status_label = ttk.Label(self.status_frame, textvariable=self.port_status_display_var)
        self.port_status_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.mdns_status_label = ttk.Label(self.status_frame, textvariable=self.mdns_status_display_var)
        self.mdns_status_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.overall_status_label = ttk.Label(self.status_frame, textvariable=self.server_status_var, font=("Segoe UI", 10, "bold"))
        self.overall_status_label.grid(row=0, column=1, rowspan=3, sticky=tk.E, padx=5, pady=2)

        # Configuration Section
        self.config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        self.config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.config_frame.columnconfigure(1, weight=1)

        ttk.Label(self.config_frame, text="Server Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.port_entry = ttk.Entry(self.config_frame, textvariable=self.server_port_var, width=10)
        self.port_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.apply_port_button = ttk.Button(self.config_frame, text="Apply & Restart Server", command=self._apply_port_settings)
        self.apply_port_button.grid(row=0, column=2, padx=5, pady=5)

        self.mdns_checkbutton = ttk.Checkbutton(self.config_frame, text="Enable mDNS Discovery", variable=self.mdns_enabled_var, command=self._apply_mdns_settings)
        self.mdns_checkbutton.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        self.autostart_checkbutton = ttk.Checkbutton(self.config_frame, text="Start Server with Windows", variable=self.autostart_enabled_var, command=self._toggle_autostart)
        self.autostart_checkbutton.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        self.minimize_to_tray_checkbutton = ttk.Checkbutton(
            self.config_frame,
            text="Minimize to system tray on close (X)",
            variable=self.minimize_to_tray_on_exit_var,
            command=self._apply_minimize_to_tray_setting
        )
        self.minimize_to_tray_checkbutton.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        # New Checkbox for Start Minimized
        self.start_minimized_checkbutton = ttk.Checkbutton(
            self.config_frame,
            text="Start application minimized to system tray",
            variable=self.start_minimized_to_tray_var,
            command=self._apply_start_minimized_setting
        )
        self.start_minimized_checkbutton.grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5) # New row

        # Server Control Button
        self.start_stop_button = ttk.Button(main_frame, text="Start Server", command=self._toggle_server_state_button_click, width=20)
        self.start_stop_button.grid(row=1, column=1, sticky=(tk.E, tk.S), padx=5, pady=10)

        # Log Output Section
        self.log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="5")
        self.log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.log_frame.columnconfigure(0, weight=1)
        self.log_frame.rowconfigure(0, weight=1)
        self.log_text_area = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, state='disabled', height=10, font=("Consolas", 9))
        self.log_text_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(2, weight=1)

    def _setup_logging_to_gui(self):
        gui_log_handler = TkinterLogHandler(self.log_queue)
        gui_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(gui_log_handler)
        logger.info("GUI logging handler initialized.") # Log that handler is set up

    def _update_ip_display(self):
        # ... (implementation as before)
        try:
            hostname = socket.gethostname()
            ip_list = socket.gethostbyname_ex(hostname)[2]
            display_ip = "N/A"
            for ip_addr in ip_list:
                if not ip_addr.startswith("127."):
                    display_ip = ip_addr
                    break
            if display_ip == "N/A" and ip_list: display_ip = ip_list[0]
            self.server_ip_var.set(f"Server IP: {display_ip}")
        except Exception as e:
            self.server_ip_var.set("Server IP: Error finding IP")
            logger.warning(f"Could not determine local IP for display: {e}")


    def _log_to_gui(self, message):
        self.log_queue.put(message)

    def _process_log_queue(self):
        # ... (implementation as before)
        try:
            while True:
                message = self.log_queue.get_nowait()
                if self.log_text_area:
                    self.log_text_area.configure(state='normal')
                    self.log_text_area.insert(tk.END, message + '\n')
                    self.log_text_area.configure(state='disabled')
                    self.log_text_area.see(tk.END)
                else: print(f"GUI_LOG_FALLBACK: {message}", file=sys.stderr)
        except queue.Empty: pass
        finally: self.root.after(100, self._process_log_queue)


    def _update_gui_status(self, status_message):
        # ... (implementation as before)
        def update_task():
            self.server_status_var.set(status_message)
            is_running = "Running" in status_message or "Starting" in status_message or "Active" in status_message
            current_port = self.server_port_var.get()
            mdns_on = self.mdns_enabled_var.get()
            self.port_status_display_var.set(f"Port: {current_port}")
            if is_running: self.mdns_status_display_var.set(f"mDNS: {'Active' if mdns_on else 'Inactive (Server Running)'}")
            else: self.mdns_status_display_var.set(f"mDNS: {'Enabled' if mdns_on else 'Disabled'} (Server Stopped)")
        self.root.after(0, update_task)
        logger.info(f"GUI Status Update: {status_message}")

    def _apply_port_settings(self):
        # ... (implementation as before)
        try:
            new_port = int(self.server_port_var.get())
            if not (1024 <= new_port <= 65535):
                messagebox.showerror("Invalid Port", "Port number must be between 1024 and 65535.")
                self.server_port_var.set(str(self.settings.get("server_port")))
                return
            logger.info(f"GUI: Applying new port: {new_port}")
            self._log_to_gui(f"INFO: Attempting to set port to {new_port} and restart server...")
            self._restart_server_with_new_config(new_port=new_port)
        except ValueError:
            messagebox.showerror("Invalid Port", "Port number must be a valid integer.")
            self.server_port_var.set(str(self.settings.get("server_port")))


    def _apply_mdns_settings(self):
        # ... (implementation as before)
        mdns_is_enabled = self.mdns_enabled_var.get()
        logger.info(f"GUI: Applying mDNS setting: {'Enabled' if mdns_is_enabled else 'Disabled'}")
        self._log_to_gui(f"INFO: Setting mDNS to {'Enabled' if mdns_is_enabled else 'Disabled'} and restarting server...")
        self._restart_server_with_new_config(new_mdns_status=mdns_is_enabled)


    def _restart_server_with_new_config(self, new_port=None, new_mdns_status=None):
        # ... (implementation as before)
        def _actual_restart():
            current_port_val = int(self.server_port_var.get()) if new_port is None else new_port
            current_mdns_val = self.mdns_enabled_var.get() if new_mdns_status is None else new_mdns_status
            self.settings["server_port"] = current_port_val
            self.settings["mdns_enabled"] = current_mdns_val
            config_manager.save_settings(port=current_port_val, mdns_enabled=current_mdns_val)
            self.port_status_display_var.set(f"Port: {current_port_val}")
            self.mdns_status_display_var.set(f"mDNS: {'Enabled' if current_mdns_val else 'Disabled'} (Applying...)")
            self._toggle_server_state(start_server=True)

        if server_control.server_thread and server_control.server_thread.is_alive():
            self._log_to_gui("INFO: Stopping server before applying new configuration...")
            self.server_status_var.set("Server Stopping...")
            if self.start_stop_button: self.start_stop_button.config(state='disabled')
            if self.server_stop_thread and self.server_stop_thread.is_alive():
                logger.warning("GUI: Server stop already in progress during restart.")
                messagebox.showwarning("Server Busy", "Server is already stopping. Please wait.")
                return
            self.server_stop_thread = threading.Thread(target=self._execute_stop_and_then_restart, args=(_actual_restart,), daemon=True)
            self.server_stop_thread.start()
        else: _actual_restart()

    def _execute_stop_and_then_restart(self, restart_callback):
        # ... (implementation as before)
        server_control.stop_server()
        self.root.after(0, restart_callback)

    def _toggle_autostart(self):
        # ... (implementation as before)
        enable = self.autostart_enabled_var.get()
        executable_path = ""
        if enable:
            if getattr(sys, 'frozen', False): executable_path = os.path.abspath(sys.executable)
            else:
                executable_path = os.path.abspath(sys.argv[0])
                messagebox.showwarning("Autostart Info", "Autostart is being set for the Python script...") # Shortened
        logger.info(f"GUI: Toggling autostart to {enable}. Executable path: {executable_path if enable else 'N/A'}")
        self._log_to_gui(f"INFO: Setting autostart to {enable}.")
        if config_manager.set_autostart_in_registry(enable, executable_path if enable else ""):
            config_manager.save_settings(autostart_enabled=enable, executable_path=executable_path if enable else self.settings.get("executable_path_for_autostart"))
            self.settings["autostart_enabled"] = enable
            if enable: self.settings["executable_path_for_autostart"] = executable_path
            messagebox.showinfo("Autostart Setting", f"Autostart with Windows has been {'enabled' if enable else 'disabled'}.")
        else:
            messagebox.showerror("Autostart Error", "Failed to update autostart setting. Check logs.")
            self.autostart_enabled_var.set(not enable)

    def _apply_minimize_to_tray_setting(self): # New method
        """Saves the 'Minimize to tray on exit' setting."""
        minimize = self.minimize_to_tray_on_exit_var.get()
        logger.info(f"GUI: Setting 'Minimize to tray on exit' to {minimize}")
        self._log_to_gui(f"INFO: 'Minimize to tray on exit' set to {minimize}.")
        config_manager.save_settings(minimize_to_tray_on_exit=minimize)
        self.settings["minimize_to_tray_on_exit"] = minimize

    def _apply_start_minimized_setting(self): # New method
        """Saves the 'Start minimized to tray' setting and updates registry if autostart is on."""
        start_minimized = self.start_minimized_to_tray_var.get()
        logger.info(f"GUI: Setting 'Start minimized to tray' to {start_minimized}")
        self._log_to_gui(f"INFO: 'Start minimized to tray' set to {start_minimized}.")
        
        # Save the setting to JSON config first
        config_manager.save_settings(start_minimized_to_tray=start_minimized)
        self.settings["start_minimized_to_tray"] = start_minimized

        # If autostart is currently enabled, we need to update the registry entry
        # to include or remove the --start-minimized flag.
        if self.autostart_enabled_var.get():
            executable_path = self.settings.get("executable_path_for_autostart", "")
            if executable_path:
                logger.info("GUI: Autostart is enabled, updating registry entry for start minimized change.")
                self._log_to_gui("INFO: Updating autostart registry entry...")
                if not config_manager.set_autostart_in_registry(True, executable_path):
                    messagebox.showerror("Autostart Error", "Failed to update autostart registry entry for 'start minimized' change. Check logs.")
                else:
                    messagebox.showinfo("Autostart Updated", "Autostart registry entry updated for 'start minimized' preference.")
            else:
                logger.warning("GUI: Cannot update autostart registry for 'start minimized' as executable path is not set.")

    def _toggle_server_state_button_click(self):
        # ... (implementation as before)
        if self.server_stop_thread and self.server_stop_thread.is_alive():
            logger.warning("GUI: Start/Stop button clicked while a stop operation is in progress.")
            messagebox.showwarning("Server Busy", "Server is currently stopping. Please wait.")
            return
        if server_control.server_thread and server_control.server_thread.is_alive():
            self._toggle_server_state(start_server=False)
        else: self._toggle_server_state(start_server=True)


    def _toggle_server_state(self, start_server: bool):
        # ... (implementation as before, non-blocking stop)
        if start_server:
            if not (server_control.server_thread and server_control.server_thread.is_alive()):
                port = int(self.server_port_var.get())
                mdns = self.mdns_enabled_var.get()
                logger.info(f"GUI: Requesting server start. Port: {port}, mDNS: {mdns}")
                success = server_control.start_server(port, mdns, self._log_to_gui, self._update_gui_status)
                self._update_gui_for_server_state(is_running=success)
                if not success: messagebox.showerror("Server Start Error", f"Failed to start server on port {port}. Check logs.")
            else:
                logger.info("GUI: Server start requested, but already running.")
                self._log_to_gui("INFO: Server is already running.")
        else: 
            if server_control.server_thread and server_control.server_thread.is_alive():
                if self.server_stop_thread and self.server_stop_thread.is_alive():
                    logger.warning("GUI: Server stop requested, but already stopping.")
                    return
                logger.info("GUI: Requesting server stop.")
                self.server_status_var.set("Server Stopping...")
                if self.start_stop_button: self.start_stop_button.config(state='disabled')
                self.server_stop_thread = threading.Thread(target=self._execute_stop_server_and_update_gui, daemon=True)
                self.server_stop_thread.start()
            else:
                logger.info("GUI: Server stop requested, but not running.")
                self._update_gui_for_server_state(is_running=False)


    def _execute_stop_server_and_update_gui(self):
        # ... (implementation as before)
        server_control.stop_server()
        self.root.after(0, lambda: self._update_gui_for_server_state(is_running=False))


    def _update_gui_for_server_state(self, is_running: bool):
        # ... (implementation as before)
        button_text = "Stop Server" if is_running else "Start Server"
        controls_state = 'disabled' if is_running else 'normal'
        if self.start_stop_button: self.start_stop_button.config(text=button_text, state='normal')
        if self.port_entry: self.port_entry.config(state=controls_state)
        if self.mdns_checkbutton: self.mdns_checkbutton.config(state=controls_state)
        if self.apply_port_button: self.apply_port_button.config(state=controls_state)
        if not is_running:
            self.server_status_var.set("Server Stopped")
            mdns_config_enabled = self.mdns_enabled_var.get()
            self.mdns_status_display_var.set(f"mDNS: {'Enabled' if mdns_config_enabled else 'Disabled'} (Server Stopped)")
            self.port_status_display_var.set(f"Port: {self.server_port_var.get()} (Stopped)")
        else: self.port_status_display_var.set(f"Port: {self.server_port_var.get()}")
        self._update_ip_display()

    def _on_closing_window_button(self): # Renamed from _on_closing
        """Handles the main window's 'X' button click event."""
        logger.info("GUI: Window close 'X' button clicked.")
        if self.minimize_to_tray_on_exit_var.get(): # Check the new setting
            logger.info("GUI: Minimizing to system tray.")
            self._log_to_gui("INFO: Minimizing to system tray. Right-click tray icon for options.")
            self.root.withdraw() # Hide the main window
        else:
            # Proceed with the original quit confirmation logic
            self._perform_full_quit_confirmation()


    def _perform_full_quit_confirmation(self):
        """Handles the logic for quitting the application, usually after user confirmation."""
        quit_message = "The server might still be running. Do you want to stop the server and quit?"
        if not (server_control.server_thread and server_control.server_thread.is_alive()):
            quit_message = "Do you want to quit?"

        if self.server_stop_thread and self.server_stop_thread.is_alive():
            messagebox.showwarning("Server Busy", "Server is currently stopping. Please wait before closing.")
            return

        if messagebox.askokcancel("Quit", quit_message):
            logger.info("GUI: User confirmed quit. Initiating full shutdown.")
            self._perform_full_quit()
        else:
            logger.info("GUI: User cancelled quit.")

    def _perform_full_quit(self):
        """Stops server (if running), stops tray icon, and destroys the window."""
        logger.info("GUI: Performing full application quit.")
        self._log_to_gui("INFO: Shutting down server and application...")
        
        # Ensure server stop is initiated (non-blocking for GUI)
        if server_control.server_thread and server_control.server_thread.is_alive():
            if not (self.server_stop_thread and self.server_stop_thread.is_alive()):
                 self._toggle_server_state(start_server=False)
            # If stop thread is already running, let it finish.
            # We'll wait for it before destroying root.
            self.root.after(100, self._check_server_stopped_for_exit_and_stop_tray)
        else: # Server not running, just stop tray and destroy
            self._stop_tray_and_destroy_root()

    def _check_server_stopped_for_exit_and_stop_tray(self):
        """Checks if server stop thread is done, then stops tray and destroys root."""
        if self.server_stop_thread and self.server_stop_thread.is_alive():
            self.root.after(100, self._check_server_stopped_for_exit_and_stop_tray)
        else:
            self._stop_tray_and_destroy_root()
            
    def _stop_tray_and_destroy_root(self):
        """Stops the system tray icon and destroys the root Tkinter window."""
        system_tray_handler.stop_tray_icon() # Stop the tray icon
        self.root.destroy() # Destroy the main window


    def run(self):
        self.root.mainloop()

class TkinterLogHandler(logging.Handler):
    # ... (as before)
    def __init__(self, queue_instance): super().__init__(); self.log_queue = queue_instance
    def emit(self, record): msg = self.format(record); self.log_queue.put(msg)

if __name__ == '__main__':
    # --- Argument Parsing for --start-minimized ---
    parser = argparse.ArgumentParser(description="StarButtonBox Server GUI")
    parser.add_argument(
        "--start-minimized",
        action="store_true",
        help="Start the application minimized to the system tray."
    )
    args = parser.parse_args()

    root = tk.Tk()
    app = ServerGUI(root, start_minimized_arg=args.start_minimized)
    
    # If not starting minimized via argument, and window is withdrawn by setting, deiconify it initially.
    # The __init__ logic will handle withdrawing it again if the setting is True.
    # This ensures the window appears at least momentarily if not started via --start-minimized arg.
    # However, the current __init__ logic handles this by only withdrawing if needed.
    # So, this explicit deiconify might not be strictly necessary if __init__ is robust.
    # For safety, if not started by arg, ensure it's not withdrawn initially by Tkinter's default.
    # if not args.start_minimized:
    #     root.deiconify() # Ensure window is visible if not starting minimized by arg

    app.run()
