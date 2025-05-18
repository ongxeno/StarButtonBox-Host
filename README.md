# StarButtonBox PC Server

[Archieved Repository] I've decide to merge the server repository into Android application repository. You can see more at https://github.com/ongxeno/StarButtonBox-Android/tree/main/server

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
* `firewall_handler.py` (Optional/Legacy): A utility module for interacting with Windows Firewall via `netsh`.

## Setup & Dependencies

1.  **Python:** Python 3.8 or newer is recommended.
2.  **Install Dependencies:**
    Open a command prompt or PowerShell and install the required libraries using pip:
    ```bash
    pip install pydirectinput pyautogui keyboard zeroconf pystray Pillow
    ```
    Alternatively, create a `requirements.txt` file with the following content and run `pip install -r requirements.txt`:
    ```
    pydirectinput
    pyautogui
    keyboard
    zeroconf
    pystray
    Pillow
    ```

## Configuration

The server's settings are managed through its GUI and stored in `server_settings.json`. This file is typically created in your user's `APPDATA` directory (e.g., `C:\Users\<YourUser>\AppData\Roaming\StarButtonBoxServer\server_settings.json`) when the application is first run or when settings are saved.

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
   To start minimized (if the setting is enabled or for testing the argument):
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
    * Ensure you have an application icon file named `icon.ico` in your project's root directory (the same directory where `StarButtonBoxServer.spec` will be).
    * Ensure you have a tray icon file named `tray_icon.png` in your project's root directory.

3.  **Create the `.spec` File:**
    Create a file named `StarButtonBoxServer.spec` in your project's root directory with the following content. This file tells PyInstaller how to build your application.

    ```python
    # StarButtonBoxServer.spec
    # -*- mode: python ; coding: utf-8 -*-

    # This .spec file assumes it is located in the root of your project directory,
    # alongside server_gui.py, icon.ico, and tray_icon.png.

    a = Analysis(
        ['server_gui.py'], # Main GUI script
        pathex=['.'],      # Search for scripts in the current directory (where .spec is)
        binaries=[],
        datas=[
            ('tray_icon.png', '.'), # Bundles tray_icon.png into the app's root
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
            # Add other modules here if ModuleNotFoundError occurs when running the .exe
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
        upx=True,        # Compresses the executable; set to False if issues arise or UPX not installed
        console=False,   # Essential for GUI applications (no command window)
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='icon.ico'  # Assumes icon.ico is in the same directory as this .spec file
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='StarButtonBoxServer', # Name of the output folder in 'dist'
    )
    ```

4.  **Build the Executable:**
    Open a command prompt or PowerShell, navigate to your project's root directory (where `StarButtonBoxServer.spec` is located), and run:
    ```bash
    pyinstaller --noconfirm StarButtonBoxServer.spec
    ```
    The `--noconfirm` option prevents PyInstaller from asking for confirmation if it needs to overwrite existing build files.

5.  **Output:**
    The packaged application will be in the `dist\StarButtonBoxServer` folder. The main executable is `StarButtonBoxServer.exe`.

## Using the Server Application

1.  Run `StarButtonBoxServer.exe` (or `python server_gui.py` if running from source).
2.  The GUI window will appear (unless "Start minimized" is enabled).
3.  **Configure Settings via GUI:**
    * Set the desired **Server Port**. Click "Apply & Restart" if you change it.
    * Toggle **mDNS Discovery**. Click "Apply & Restart" if you change it.
    * Enable **Start Server with Windows** if desired.
    * Configure **Minimize to tray on close (X)** and **Start application minimized to system tray** preferences.
4.  **Start the Server:** Click the "Start Server" button. Status indicators should update.
5.  **System Tray:** The application will have an icon in the system tray. Right-click it for options to show/hide the settings window, start/stop the server, or quit the application.
6.  **Android App:** Ensure your StarButtonBox Android app is on the same local network and configured to connect to the PC's IP address and the server port. If mDNS is working, the Android app should be able to discover the server automatically.

## Troubleshooting

* **Log File:** The primary source for troubleshooting is `server.log`. It's typically located in `%APPDATA%\StarButtonBoxServer` when running the packaged `.exe`, or in the script's directory when running `python server_gui.py`.
* **Windows Firewall:** When `StarButtonBoxServer.exe` is run for the first time and attempts network operations, Windows Firewall will likely prompt for permission.
    * **Ensure you "Allow access"**, especially for **"Private networks"**.
    * If you miss the prompt or deny it, you'll need to manually add an inbound rule in "Windows Defender Firewall with Advanced Security" for the `StarButtonBoxServer.exe` program.
* **Connectivity Issues with `.exe`:** If the server works when run as a Python script but not as an `.exe`, common causes include:
    * Windows Firewall blocking the `.exe`.
    * PyInstaller missing a hidden dependency. To diagnose, temporarily edit the `.spec` file to set `console=True` in the `EXE` section, rebuild, and run the `.exe`. A console window will appear and show Python tracebacks (like `ModuleNotFoundError`). Add missing modules to the `hiddenimports` list in the `.spec` file and rebuild.
    * Incorrect paths to bundled data files (e.g., `tray_icon.png`). Ensure the `datas` section in your `.spec` file is correct and your code uses a method like `system_tray_handler._get_resource_path()` for bundled files.
* **Port in Use:** If the server fails to start and logs indicate the port is already in use, ensure no other application (including another instance of StarButtonBoxServer) is using that port.

