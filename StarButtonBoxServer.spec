# -*- mode: python ; coding: utf-8 -*-

# Import PyInstaller utility to get path to bundled data files at runtime
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['server_gui.py'], # Your main GUI script
    pathex=['C:\\Users\\ppong\\VSCodeProject\\StarButtonBoxPC'], # !!! Ensure this ABSOLUTE path is correct !!!
    binaries=[],
    datas=[
        # Add data files here. Format: ('source_path_on_your_system', 'destination_folder_in_bundle')
        # The destination '.' means the root of the bundled app directory.
        ('tray_icon.png', '.'),
        # If you have other assets, like a default config (though yours is created in APPDATA):
        # ('default_server_settings.json', '.')
    ],
    hiddenimports=[
        'pystray', 
        'pystray._win32', # Explicitly include Windows backend for pystray
        'PIL', 
        'PIL.Image', 
        'PIL.ImageTk', 
        'PIL._imagingtk', 
        'PIL._tkinter_finder', # Pillow and Tkinter integration specifics
        'pyautogui',
        'keyboard', 
        'keyboard._winkeyboard', # Windows backend for keyboard library
        'zeroconf', 
        'ifaddr', # Often a dependency for zeroconf to discover network interfaces
        'winreg', # For registry access (autostart)
        'argparse', # Used in server_gui.py for --start-minimized
        'queue', # Standard library, but sometimes helps to be explicit
        'logging.handlers', # If you were to use specific handlers like RotatingFileHandler
        'pkg_resources', # Often a hidden dependency for many packages
        'pkg_resources.py2_warn',
        'threading', # Standard, but good to list if heavily used
        'socket',    # Standard
        'json',      # Standard
        'time',      # Standard
        'sys',       # Standard
        'os',        # Standard
        'signal',    # Standard
        'concurrent',# For ThreadPoolExecutor
        'concurrent.futures',
        # Add any other modules reported as ModuleNotFoundError when running the .exe
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False, # Setting to False is standard
    optimize=0,      # 0 for no optimization, 1 or 2 for bytecode optimization (usually not needed unless specific size/speed goals)
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [], # Usually empty if a.scripts is populated
    exclude_binaries=True, # Keep this if you don't have specific external binaries to bundle differently
    name='StarButtonBoxServer',
    debug=False, # Set to True for a debug build (more verbose, larger) if troubleshooting PyInstaller itself
    bootloader_ignore_signals=False,
    strip=False, # Set to True to strip debug symbols (smaller exe, but harder to debug if it crashes at C level)
    upx=True,    # Uses UPX to compress the final executable. Requires UPX to be installed and in PATH.
                 # Set to False if you don't have UPX or encounter issues.
    console=True, 
    disable_windowed_traceback=False, 
    argv_emulation=False, 
    target_arch=None,     
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas, # This includes what you defined in a.datas
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StarButtonBoxServer', # Name of the output folder in 'dist'
)
