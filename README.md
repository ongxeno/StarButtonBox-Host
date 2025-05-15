# StarButtonBox PC Server

This Python application is the server-side component of the StarButtonBox system. It runs on a Windows PC, listens for commands from the StarButtonBox Android application, and simulates keyboard/mouse inputs to control games, primarily designed for Star Citizen.

The server features a graphical user interface (GUI) for configuration and status monitoring.

## Features

* **UDP Command Listener:** Receives commands from the Android client over the local network.
* **Input Simulation:**
    * Executes keyboard macros (key presses, holds, modifiers) via `pydirectinput`.
    * Simulates mouse events (clicks, holds) and scrolls via `pyautogui`.
    * Supports an "Auto Drag and Drop" feature to automate mouse drag operations between two captured screen positions.
* **mDNS Service Discovery:** Advertises itself on the local network using mDNS (Zeroconf) as `_starbuttonbox._udp.local.`, allowing the Android app to discover it automatically.
* **Network Reliability:** Implements health checks (PING/PONG) and command acknowledgments (ACK) with the Android client to monitor connection status and ensure command delivery.
* **Graphical User Interface (GUI):** Built with Tkinter, providing:
    * Real-time server status (IP, port, mDNS status, overall status).
    * Configuration for server port.
    * Toggle for enabling/disabling mDNS service.
    * Option to automatically start the server application with Windows.
    * Option to start the application minimized to the system tray.
    * Option to minimize the application to the system tray when the window is closed.
    * A live log viewer.
* **System Tray Icon:**
    * Provides quick access to show/hide the settings window.
    * Allows starting/stopping the server.
    * Option to quit the application.
* **Persistent Configuration:** Settings are saved in a `server_settings.json` file located in `%APPDATA%\StarButtonBoxServer`.
* **File Logging:** Server activity and errors are logged to `server.log` in the same directory as `server_settings.json`.
* **Layout Import Helper:** Can trigger the PC's web browser to open a URL provided by the Android app for importing layout files.

## Project Structure (Python Scripts)

* `server_gui.py`: The main entry point for the application. Creates and manages the Tkinter GUI, and initiates server operations.
* `server.py`: Contains the core server logic, including UDP socket management, packet processing, mDNS interaction (via `mdns_handler`), and threading for the server loop. It's refactored to be controlled by `server_gui.py`.
* `config_manager.py`: Handles loading and saving application settings from/to `server_settings.json`. Also manages Windows Registry entries for the "Start with Windows" feature.
* `system_tray_handler.py`: Manages the system tray icon, its context menu, and associated actions using the `pystray` library.
* `input_simulator.py`: Contains functions to simulate keyboard and mouse inputs using `pydirectinput` and `pyautogui`.
* `auto_drag_handler.py`: Implements the logic for the "Auto Drag and Drop" feature, including capturing mouse positions and performing the drag loop.
* `mdns_handler.py`: Manages mDNS/Zeroconf service registration and unregistration.
* `dialog_handler.py`: Handles triggering the PC's web browser, primarily for the "Import Layout from PC" feature.
* `config.py`: Stores static configuration constants like default port numbers and packet type definitions.
* `firewall_handler.py` (Optional/Legacy): A utility module for interacting with Windows Firewall via `netsh`. (Note: The primary firewall interaction method was shifted to triggering the system's prompt.)

## Setup & Dependencies

1.  **Python:** Python 3.8 or newer is recommended.
2.  **Install Dependencies:**
    Open a command prompt or PowerShell and install the required libraries using pip:
    ```bash
    pip install pydirectinput pyautogui keyboard zeroconf pystray Pillow
    ```
    You can also create a `requirements.txt` file with the following content and run `pip install -r requirements.txt`:
    ```
    pydirectinput
    pyautogui
    keyboard
    zeroconf
    pystray
    Pillow
    ```

## Configuration

The server's settings are managed through its GUI and stored in `server_settings.json`. This file is typically located in your user's `APPDATA` directory (e.g., `C:\Users\<YourUser>\AppData\Roaming\StarButtonBoxServer\server_settings.json`).

Editable settings via the GUI include:
* **Server Port:** The UDP port the server listens on.
* **Enable mDNS Discovery:** Toggles mDNS service advertisement.
* **Start Server with Windows:** Adds/removes the application from Windows startup.
* **Start application minimized to system tray:** If checked, the GUI will start hidden, with only the tray icon visible (useful when "Start Server with Windows" is also enabled).
* **Minimize to system tray on close (X):** If checked, clicking the GUI window's close button will hide the window to the system tray instead of quitting the application.

## Running the Server

### 1. Directly from Python Scripts:
   Navigate to the project directory in your command prompt or PowerShell and run:
   ```bash
   python server_gui.py
   ```
   You can also start it minimized if you've previously enabled the setting or by passing an argument (though the argument is mainly for the packaged version when launched by the registry):
   ```bash
   python server_gui.py --start-minimized
   ```

### 2. As a Packaged Executable (`.exe`):
   Once built (see next section), simply run the `StarButtonBoxServer.exe`.

## Building the Executable (`.exe`) for Windows

PyInstaller is used to package the Python application into a standalone Windows executable.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Prepare Assets:**
    * Ensure you have an application icon file named `icon.ico` in your project's root directory (where `StarButtonBoxServer.spec` will be).
    * Ensure you have a tray icon file named `tray_icon.png` in your project's root directory.

3.  **Use the `.spec` File:**
    A `.spec` file provides the most control for PyInstaller. Create a file named `StarButtonBoxServer.spec` in your project's root directory with the following content:

    ```python
    # StarButtonBoxServer.spec
    # -*- mode: python ; coding: utf-8 -*-

    # PyInstaller will run this spec file from the directory where the spec file is located.
    # Paths for 'datas' and 'icon' can be relative to this spec file's location.

    a = Analysis(
        ['server_gui.py'], # Your main GUI script, relative to where this .spec file is
        pathex=['.'], # Search for scripts in the current directory (where .spec is)
        binaries=[],
        datas=[
            # Add data files here. Format: ('source_path_relative_to_spec', 'destination_folder_in_bundle')
            # The destination '.' means the root of the bundled app directory.
            ('tray_icon.png', '.'), 
        ],
        hiddenimports=[
            'pystray', 'pystray._win32',
            'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL._imagingtk', 'PIL._tkinter_finder',
            'pyautogui',
            'keyboard', 'keyboard._winkeyboard',
            'zeroconf', 'ifaddr',
            'winreg', 'argparse', 'queue',
            'logging.handlers', 'pkg_resources', 'pkg_resources.py2_warn',
            'threading', 'socket', 'json', 'time', 'sys', 'os', 'signal',
            'concurrent', 'concurrent.futures',
        ],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
        optimize=0,
    )

    pyz = PYZ(a.pure)

    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='StarButtonBoxServer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True, # Set to False if you don't have UPX or encounter issues
        console=False, # Essential for GUI applications
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='icon.ico' # Relative path for app icon (assumes icon.ico is in the same dir as .spec)
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='StarButtonBoxServer',
    )
    ```
    **Important Changes & Assumptions:**
    * **No `project_root` variable needed:** The paths are now directly relative.
    * **`pathex=['.']`**: PyInstaller will look for `server_gui.py` in the same directory as the `.spec` file.
    * **`datas=[('tray_icon.png', '.')]`**: Assumes `tray_icon.png` is in the same directory as the `.spec` file.
    * **`icon='icon.ico'`**: Assumes `icon.ico` is in the same directory as the `.spec` file.
    * **Crucial:** You **must** run the `pyinstaller` command from the directory where your `.spec` file and these assets (`server_gui.py`, `icon.ico`, `tray_icon.png`, and other `.py` modules) are located. Typically, this is your project's root directory.

4.  **Build the Executable:**
    Open a command prompt or PowerShell, **navigate to your project's root directory** (where `StarButtonBoxServer.spec` is), and run:
    ```bash
    pyinstaller --noconfirm StarButtonBoxServer.spec
    ```

5.  **Output:**
    The packaged application will be in the `dist\StarButtonBoxServer` folder.

## Using the Server Application

(Instructions remain the same as before)

## Troubleshooting

(Troubleshooting advice remains the same as before)
