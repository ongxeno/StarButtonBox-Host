import socket
import pydirectinput
import json
import time
import sys
import threading
import ipaddress
from zeroconf import ServiceInfo, Zeroconf, IPVersion # Added zeroconf imports
import signal # Added signal for graceful shutdown

# --- Configuration ---
COMMAND_PORT = 5005  # Port for receiving commands
BUFFER_SIZE = 1024
# --- mDNS Configuration ---
MDNS_SERVICE_TYPE = "_starbuttonbox._udp.local." # Standard service type format
MDNS_SERVICE_NAME = "StarButtonBox Server._starbuttonbox._udp.local." # Unique name for this instance

# --- Existing execute_key_event, execute_mouse_event, execute_mouse_scroll functions ---
# [ ... keep existing functions execute_key_event, execute_mouse_event, execute_mouse_scroll ... ]
# Ensure they use sys.stdout.flush() after prints if needed for immediate feedback.
def execute_key_event(data):
    """Handles 'key_event' actions (keyboard keys only) from the parsed JSON data."""
    key = data.get('key')
    modifiers = data.get('modifiers', []) # Default to empty list
    press_type_data = data.get('pressType', {}) # Default to empty dict
    press_type = press_type_data.get('type', 'tap') # Default to 'tap'
    duration_ms = press_type_data.get('durationMs') # Will be None if type is 'tap'

    if not key:
        print("    -> Error: 'key' field missing in key_event data.")
        sys.stdout.flush()
        return

    # --- Modifier Key Handling ---
    # Press down all modifier keys FIRST
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")
            sys.stdout.flush()

    # --- Main Action Execution (Keyboard Keys Only) ---
    try:
        # Handle as standard Keyboard Key Action
        if press_type == 'tap':
            print(f"    -> Simulating key tap: '{key}' with modifiers {modifiers}")
            sys.stdout.flush()
            pydirectinput.press(key) # Modifiers already held
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                print(f"    -> Warning: Invalid hold duration ({duration_ms}ms) for key '{key}'. Performing tap instead.")
                sys.stdout.flush()
                pydirectinput.press(key) # Modifiers already held
            else:
                print(f"    -> Simulating key hold: '{key}' for {duration_sec:.2f}s with modifiers {modifiers}")
                sys.stdout.flush()
                pydirectinput.keyDown(key) # Modifiers already held
                time.sleep(duration_sec)
                pydirectinput.keyUp(key)
        else:
            print(f"    -> Warning: Invalid pressType ('{press_type}') or missing durationMs for key '{key}'. Performing tap.")
            sys.stdout.flush()
            pydirectinput.press(key) # Modifiers already held

    except Exception as action_e:
        print(f"    -> Error executing action for key '{key}': {action_e}")
        sys.stdout.flush()
    finally: # Ensure modifiers are released even if action fails
        # --- Modifier Key Handling (Release) ---
        # Release modifiers AFTER main action is done
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
            except Exception as mod_e:
                print(f"    -> Warning: Failed to release modifier '{mod_key}': {mod_e}")
                sys.stdout.flush()


def execute_mouse_event(data):
    """Handles 'mouse_event' actions from the parsed JSON data."""
    button_str = data.get('button')
    press_type_data = data.get('pressType', {})
    press_type = press_type_data.get('type', 'tap')
    duration_ms = press_type_data.get('durationMs')
    modifiers = data.get('modifiers', []) # Get modifiers list

    # Map button string from JSON ("LEFT", "RIGHT", "MIDDLE") to pydirectinput names
    button_map = {
        "LEFT": "left",
        "RIGHT": "right",
        "MIDDLE": "middle"
    }
    button = button_map.get(button_str)

    if not button:
        print(f"    -> Error: Invalid or missing 'button' field ('{button_str}') in mouse_event data.")
        sys.stdout.flush()
        return

    # --- Modifier Key Handling ---
    # Hold keyboard modifiers if present
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
            print(f"    -> Holding modifier: {mod_key}")
            sys.stdout.flush()
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")
            sys.stdout.flush()

    # --- Main Mouse Action ---
    try:
        if press_type == 'tap':
            print(f"    -> Simulating mouse click: '{button}' button with modifiers {modifiers}")
            sys.stdout.flush()
            pydirectinput.click(button=button)
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                 print(f"    -> Warning: Invalid hold duration ({duration_ms}ms) for mouse button '{button}'. Performing click instead.")
                 sys.stdout.flush()
                 pydirectinput.click(button=button)
            else:
                print(f"    -> Simulating mouse hold: '{button}' button for {duration_sec:.2f}s with modifiers {modifiers}")
                sys.stdout.flush()
                pydirectinput.mouseDown(button=button)
                time.sleep(duration_sec)
                pydirectinput.mouseUp(button=button)
        else:
             print(f"    -> Warning: Invalid pressType ('{press_type}') or missing durationMs for mouse button '{button}'. Performing click.")
             sys.stdout.flush()
             pydirectinput.click(button=button)

    except Exception as mouse_e:
        print(f"    -> Error executing mouse action for button '{button}': {mouse_e}")
        sys.stdout.flush()
    finally:
        # --- Modifier Key Handling (Release) ---
        # Release keyboard modifiers if they were held
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
                print(f"    -> Releasing modifier: {mod_key}")
                sys.stdout.flush()
            except Exception as mod_e:
                print(f"    -> Warning: Failed to release modifier '{mod_key}': {mod_e}")
                sys.stdout.flush()


def execute_mouse_scroll(data):
    """Handles 'mouse_scroll' actions from the parsed JSON data."""
    direction = data.get('direction')
    clicks = data.get('clicks', 1) # Default to 1 click if not specified
    modifiers = data.get('modifiers', []) # Get modifiers list

    if direction == "UP":
        scroll_amount = clicks
    elif direction == "DOWN":
        scroll_amount = -clicks # Negative value for scrolling down
    else:
        print(f"    -> Error: Invalid or missing 'direction' field ('{direction}') in mouse_scroll data.")
        sys.stdout.flush()
        return

    # --- Modifier Key Handling ---
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
            print(f"    -> Holding modifier: {mod_key}")
            sys.stdout.flush()
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")
            sys.stdout.flush()

    # --- Main Scroll Action ---
    try:
        print(f"    -> Simulating mouse scroll: direction '{direction}', clicks {clicks} (amount {scroll_amount}) with modifiers {modifiers}")
        sys.stdout.flush()
        pydirectinput.scroll(scroll_amount)
    except Exception as scroll_e:
         print(f"    -> Error executing mouse scroll: {scroll_e}")
         sys.stdout.flush()
    finally:
        # --- Modifier Key Handling (Release) ---
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
                print(f"    -> Releasing modifier: {mod_key}")
                sys.stdout.flush()
            except Exception as mod_e:
                print(f"    -> Warning: Failed to release modifier '{mod_key}': {mod_e}")
                sys.stdout.flush()

# --- Function to get a non-loopback IP address ---
def get_local_ip():
    """Attempts to find a non-loopback local IP address."""
    try:
        # Try connecting to a public DNS server (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('8.8.8.8', 1)) # Google DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback if connection fails
        try:
            return socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            return "127.0.0.1" # Last resort

# --- Global Zeroconf instance ---
zeroconf = None
service_info = None

def register_mdns_service():
    """Registers the StarButtonBox service using Zeroconf."""
    global zeroconf, service_info
    try:
        zeroconf = Zeroconf(ip_version=IPVersion.V4Only) # Use IPv4 for simplicity

        local_ip = get_local_ip()
        if local_ip == "127.0.0.1":
             print("Warning: Could not determine a non-loopback IP address. mDNS registration might fail or use loopback.")
             sys.stdout.flush()
             # Optionally, force a specific interface or handle this case differently

        # Get hostname for the service name
        host_name = socket.gethostname().split('.')[0] # Use just the hostname part
        service_name = f"{host_name} StarButtonBox Server._starbuttonbox._udp.local." # More descriptive name

        # Create ServiceInfo
        service_info = ServiceInfo(
            type_=MDNS_SERVICE_TYPE,
            name=service_name,
            addresses=[socket.inet_aton(local_ip)], # Provide IP address bytes
            port=COMMAND_PORT,
            properties={}, # No extra properties needed for now
            server=f"{host_name}.local.", # Standard server name format
        )

        print(f"Registering mDNS service:")
        print(f"  Name: {service_name}")
        print(f"  Type: {MDNS_SERVICE_TYPE}")
        print(f"  Address: {local_ip}")
        print(f"  Port: {COMMAND_PORT}")
        sys.stdout.flush()

        zeroconf.register_service(service_info)
        print("mDNS service registered successfully.")
        sys.stdout.flush()

    except Exception as e:
        print(f"Error registering mDNS service: {e}")
        sys.stdout.flush()
        if zeroconf:
            zeroconf.close()
        zeroconf = None # Ensure it's None if registration failed

def unregister_mdns_service():
    """Unregisters the mDNS service and closes Zeroconf."""
    global zeroconf, service_info
    if zeroconf and service_info:
        print("\nUnregistering mDNS service...")
        sys.stdout.flush()
        try:
            zeroconf.unregister_service(service_info)
            zeroconf.close()
            print("mDNS service unregistered and Zeroconf closed.")
            sys.stdout.flush()
        except Exception as e:
            print(f"Error unregistering mDNS service: {e}")
            sys.stdout.flush()
    elif zeroconf:
        print("\nClosing Zeroconf (service likely not registered)...")
        sys.stdout.flush()
        zeroconf.close()
    zeroconf = None
    service_info = None

def handle_shutdown(signum, frame):
    """Signal handler for graceful shutdown."""
    print(f"\nReceived signal {signum}. Shutting down...")
    sys.stdout.flush()
    # Unregister mDNS first
    unregister_mdns_service()
    # Exit the program
    sys.exit(0)

def main():
    # --- Register Signal Handlers ---
    signal.signal(signal.SIGINT, handle_shutdown)  # Handle Ctrl+C
    signal.signal(signal.SIGTERM, handle_shutdown) # Handle termination signal

    # --- Register mDNS Service ---
    register_mdns_service()
    if not zeroconf:
        print("Failed to initialize mDNS. Exiting.")
        sys.stdout.flush()
        return # Exit if mDNS failed

    # --- Command Server Socket ---
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Bind the command socket
        server_socket.bind(('0.0.0.0', COMMAND_PORT))
        print(f"UDP command server listening on port {COMMAND_PORT}...")
        sys.stdout.flush()

        # --- Command Listening Loop ---
        while True: # Loop indefinitely until shutdown signal
            try:
                # Wait for a UDP command packet
                data_bytes, addr = server_socket.recvfrom(BUFFER_SIZE)
                json_string = data_bytes.decode('utf-8').strip()
                print(f"\nReceived command data: '{json_string}' from {addr}")
                sys.stdout.flush()

                # Parse the JSON string
                try:
                    action_data = json.loads(json_string)
                except json.JSONDecodeError as json_e:
                    print(f"    -> Error: Invalid JSON received: {json_e}")
                    sys.stdout.flush()
                    continue

                # Determine action type and execute
                action_type = action_data.get('type')

                if action_type == 'key_event':
                    execute_key_event(action_data)
                elif action_type == 'mouse_event':
                    execute_mouse_event(action_data)
                elif action_type == 'mouse_scroll':
                    execute_mouse_scroll(action_data)
                else:
                    print(f"    -> Warning: Unknown action type '{action_type}' received.")
                    sys.stdout.flush()

            except UnicodeDecodeError:
                print(f"    -> Error: Received data from {addr} could not be decoded as UTF-8.")
                sys.stdout.flush()
            except socket.timeout: # Should not happen unless timeout is set on command socket
                 continue
            except Exception as loop_e:
                print(f"    -> Error processing command packet from {addr}: {loop_e}")
                sys.stdout.flush()

            sys.stdout.flush()

    except Exception as e:
        print(f"\nCritical error running command server: {e}")
        sys.stdout.flush()
    finally:
        # --- Cleanup ---
        # Signal handler calls unregister_mdns_service()
        # Ensure command socket is closed if loop exits unexpectedly
        if server_socket:
            server_socket.close()
            print("Command server socket closed.")
            sys.stdout.flush()
        # Ensure mDNS is unregistered even if signal handler didn't run (e.g., error before loop)
        unregister_mdns_service()


if __name__ == "__main__":
    main()
