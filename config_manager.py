# config_manager.py
# Handles loading and saving server configurations from/to a JSON file,
# and manages Windows auto-start registry settings.

import json
import os
import sys
import config # For default values
import winreg # For Windows registry operations
import logging

logger = logging.getLogger("StarButtonBoxServerConfig") # Use a specific logger for this module

# --- Configuration File ---
if getattr(sys, 'frozen', False):
    SETTINGS_DIR = os.path.join(os.getenv('APPDATA'), 'StarButtonBoxServer')
    if not os.path.exists(SETTINGS_DIR):
        try:
            os.makedirs(SETTINGS_DIR)
        except OSError as e:
            logger.error(f"Could not create settings directory {SETTINGS_DIR}: {e}")
            SETTINGS_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
else:
    SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE_NAME = "server_settings.json"
SETTINGS_FILE_PATH = os.path.join(SETTINGS_DIR, SETTINGS_FILE_NAME)

# --- Default Settings ---
DEFAULT_SETTINGS = {
    "server_port": config.COMMAND_PORT,
    "mdns_enabled": True,
    "autostart_enabled": False,
    "executable_path_for_autostart": "",
    "minimize_to_tray_on_exit": False,
    "start_minimized_to_tray": False # New setting for starting minimized
}

# --- Registry Settings for Auto-Start ---
AUTOSTART_REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_APP_NAME = "StarButtonBoxServer"


def load_settings():
    """
    Loads settings from the JSON file.
    If the file doesn't exist, is empty, or is corrupt, returns default settings.
    """
    if os.path.exists(SETTINGS_FILE_PATH):
        try:
            with open(SETTINGS_FILE_PATH, 'r') as f:
                content = f.read()
                if not content.strip():
                    logger.info(f"Settings file '{SETTINGS_FILE_PATH}' is empty. Using defaults.")
                    return DEFAULT_SETTINGS.copy()
                f.seek(0)
                settings_from_file = json.load(f)
                loaded_settings = DEFAULT_SETTINGS.copy()
                loaded_settings.update(settings_from_file)
                return loaded_settings
        except json.JSONDecodeError:
            logger.error(f"Could not decode JSON from '{SETTINGS_FILE_PATH}'. Using default settings.")
            return DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Could not read settings file '{SETTINGS_FILE_PATH}': {e}. Using default settings.")
            return DEFAULT_SETTINGS.copy()
    else:
        logger.info(f"Settings file '{SETTINGS_FILE_PATH}' not found. Using default settings and creating it.")
        _save_settings_to_file(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()

def save_settings(port=None, mdns_enabled=None, autostart_enabled=None, executable_path=None, 
                  minimize_to_tray_on_exit=None, start_minimized_to_tray=None): # Added new param
    """
    Saves the provided settings to the JSON file.
    If a setting is not provided (None), its current value is retained.
    """
    current_settings = load_settings()

    if port is not None:
        current_settings["server_port"] = int(port)
    if mdns_enabled is not None:
        current_settings["mdns_enabled"] = bool(mdns_enabled)
    if autostart_enabled is not None:
        current_settings["autostart_enabled"] = bool(autostart_enabled)
    if executable_path is not None:
        current_settings["executable_path_for_autostart"] = str(executable_path)
    if minimize_to_tray_on_exit is not None:
        current_settings["minimize_to_tray_on_exit"] = bool(minimize_to_tray_on_exit)
    if start_minimized_to_tray is not None: # Handle new setting
        current_settings["start_minimized_to_tray"] = bool(start_minimized_to_tray)

    return _save_settings_to_file(current_settings)

def _save_settings_to_file(settings_dict):
    """Internal helper to write the settings dictionary to the file."""
    try:
        with open(SETTINGS_FILE_PATH, 'w') as f:
            json.dump(settings_dict, f, indent=4)
        logger.info(f"Settings saved to '{SETTINGS_FILE_PATH}'")
        return True
    except Exception as e:
        logger.error(f"Could not save settings to '{SETTINGS_FILE_PATH}': {e}")
        return False

def get_setting(key, default_value=None):
    """Helper to get a specific setting."""
    settings = load_settings()
    return settings.get(key, default_value if default_value is not None else DEFAULT_SETTINGS.get(key))


def set_autostart_in_registry(enable: bool, executable_path: str):
    """
    Configures the application to start with Windows by adding/removing a registry key
    under HKEY_CURRENT_USER.
    """
    if enable and not executable_path:
        logger.error("Cannot enable autostart: executable_path is missing.")
        return False
    if enable and not os.path.exists(executable_path):
        logger.error(f"Cannot enable autostart: executable_path '{executable_path}' does not exist.")
        return False

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY_PATH, 0, winreg.KEY_WRITE)
        if enable:
            normalized_path = os.path.normpath(executable_path)
            # Add --start-minimized argument if the setting is enabled
            settings = load_settings() # Load current settings to check start_minimized_to_tray
            path_to_register = f'"{normalized_path}"'
            if settings.get("start_minimized_to_tray", False): # Check the setting
                path_to_register += " --start-minimized"
                
            winreg.SetValueEx(key, AUTOSTART_APP_NAME, 0, winreg.REG_SZ, path_to_register)
            logger.info(f"Autostart enabled: Added '{path_to_register}' to registry for '{AUTOSTART_APP_NAME}'.")
            save_settings(executable_path=normalized_path) # Save base path, not with arg
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_APP_NAME)
                logger.info(f"Autostart disabled: Removed '{AUTOSTART_APP_NAME}' from registry.")
            except FileNotFoundError:
                logger.info(f"Autostart was not set for '{AUTOSTART_APP_NAME}' (DeleteValue).")
        winreg.CloseKey(key)
        return True
    except PermissionError:
        logger.error(f"Permission denied when trying to access registry for autostart.")
        return False
    except FileNotFoundError:
        logger.error(f"Registry path '{AUTOSTART_REG_KEY_PATH}' not found for autostart.")
        return False
    except Exception as e:
        logger.error(f"Failed to {'enable' if enable else 'disable'} autostart: {e}")
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Testing config_manager.py...")
    print("Settings will be stored at:", SETTINGS_FILE_PATH)

    settings = load_settings()
    print(f"\nInitial/Loaded settings: {settings}")

    print("\nTesting 'start_minimized_to_tray' setting...")
    save_settings(start_minimized_to_tray=True)
    settings = load_settings()
    print(f"Start minimized: {settings.get('start_minimized_to_tray')}")
    assert settings.get('start_minimized_to_tray') is True

    save_settings(start_minimized_to_tray=False)
    settings = load_settings()
    print(f"Start minimized: {settings.get('start_minimized_to_tray')}")
    assert settings.get('start_minimized_to_tray') is False

    # Test autostart with start_minimized integration
    print("\nTesting enabling autostart with 'start_minimized_to_tray' = True")
    save_settings(start_minimized_to_tray=True) # Ensure setting is true for this test
    
    if getattr(sys, 'frozen', False):
        test_exe_path = os.path.abspath(sys.executable)
    else:
        test_exe_path = os.path.abspath(__file__)
        if not os.path.exists(test_exe_path) and test_exe_path.endswith(".py"):
             try: open(test_exe_path, "a").close()
             except: pass
    
    if set_autostart_in_registry(True, test_exe_path):
        print("  Registry entry for autostart (likely) updated. Check manually for '--start-minimized' argument.")
    
    # Reset for next test
    save_settings(start_minimized_to_tray=False)
    set_autostart_in_registry(False, test_exe_path) # Clean up registry
    print("\nTest finished. Remember to check registry manually for autostart entries.")
