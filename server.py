import socket
import pydirectinput
import json
import time
import sys
import threading # Added threading
import ipaddress # Added ipaddress for network calculations

# --- Existing Configuration ---
PORT = 5005  # Port to listen on for commands
BUFFER_SIZE = 1024
# --- New Discovery Configuration ---
DISCOVERY_PORT = 5006 # Port for broadcasting/listening for discovery
DISCOVERY_MESSAGE = b"STARBUTTONBOX_SERVER_DISCOVERY" # Unique message (Not strictly needed for broadcast response)
BROADCAST_INTERVAL_SEC = 5 # How often to broadcast

# --- Existing execute_key_event, execute_mouse_event, execute_mouse_scroll functions ---

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


# --- New Discovery Broadcast Function ---
def broadcast_discovery(stop_event):
    """Periodically broadcasts a discovery message containing the command port."""
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_socket.settimeout(0.2) # Set a timeout so the loop can check stop_event

    # Prepare the JSON payload containing the command port
    message_payload = json.dumps({"type": "discovery_response", "port": PORT}).encode('utf-8')

    print(f"Discovery broadcast thread started. Broadcasting on port {DISCOVERY_PORT} every {BROADCAST_INTERVAL_SEC} seconds.")
    sys.stdout.flush()

    # --- Attempt to find broadcast address (more robust) ---
    broadcast_address = '<broadcast>' # Default to generic broadcast
    try:
        # Get hostname
        hostname = socket.gethostname()
        # Get all IP addresses for the hostname
        # Using socket.getaddrinfo for better compatibility (IPv4/IPv6)
        ip_addresses = socket.getaddrinfo(hostname, None)
        # Filter for IPv4 addresses
        ipv4_addresses = [addr[4][0] for addr in ip_addresses if addr[0] == socket.AF_INET]

        # Find a non-loopback IPv4 address and calculate its broadcast address
        for ip_str in ipv4_addresses:
            if not ip_str.startswith('127.'):
                try:
                    # Try common subnet masks
                    masks_to_try = ['/24', '/16', '/8'] # Common masks
                    found_mask = False
                    for mask_str in masks_to_try:
                        try:
                            iface = ipaddress.IPv4Interface(f"{ip_str}{mask_str}")
                            broadcast_address = str(iface.network.broadcast_address)
                            print(f"  -> Determined broadcast address: {broadcast_address} (from IP: {ip_str}, mask: {mask_str})")
                            sys.stdout.flush()
                            found_mask = True
                            break # Found a valid one for this IP
                        except ValueError:
                            continue # Try next mask if current one is invalid for the IP
                    if found_mask:
                        break # Found broadcast address for one of the IPs, stop checking others
                except Exception as ip_err:
                    print(f"  -> Warning: Error determining broadcast address for {ip_str}: {ip_err}")
                    sys.stdout.flush()
                    continue # Try next IP if error

        if broadcast_address == '<broadcast>':
            print("  -> Warning: Could not determine specific broadcast address, using generic '<broadcast>'. Discovery might be less reliable.")
            sys.stdout.flush()

    except socket.gaierror as e:
        print(f"  -> Warning: Could not get local IP address information: {e}. Using generic broadcast address.")
        sys.stdout.flush()
    except Exception as e:
         print(f"  -> Warning: An unexpected error occurred during broadcast address lookup: {e}. Using generic broadcast address.")
         sys.stdout.flush()


    # --- Broadcast Loop ---
    while not stop_event.is_set():
        try:
            # Send the broadcast message with the command PORT
            broadcast_socket.sendto(message_payload, (broadcast_address, DISCOVERY_PORT))
            # print(f"Sent discovery broadcast to {broadcast_address}:{DISCOVERY_PORT}") # Optional: reduce log spam
        except socket.error as sock_err:
             # Handle specific socket errors, e.g., network unreachable
             print(f"Socket error sending discovery broadcast: {sock_err}")
             # Avoid flooding logs if the network is down, maybe wait longer
             stop_event.wait(BROADCAST_INTERVAL_SEC * 2) # Wait longer on error
        except Exception as e:
            print(f"Error sending discovery broadcast: {e}")
            sys.stdout.flush()
        # Wait for the next interval or until stop_event is set
        stop_event.wait(BROADCAST_INTERVAL_SEC) # Use wait() for interruptible sleep

    broadcast_socket.close()
    print("Discovery broadcast thread stopped.")
    sys.stdout.flush()


def main():
    # Create a UDP socket for commands
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # --- Start Discovery Thread ---
    stop_event = threading.Event()
    discovery_thread = threading.Thread(target=broadcast_discovery, args=(stop_event,), daemon=True)
    discovery_thread.start()
    # --------------------------

    try:
        # Bind the command socket
        server_socket.bind(('0.0.0.0', PORT))
        print(f"UDP command server listening on port {PORT}...")
        sys.stdout.flush() # Ensure print statements appear immediately

        while True:
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
            except Exception as loop_e:
                print(f"    -> Error processing command packet from {addr}: {loop_e}")
                sys.stdout.flush()

            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down...")
        sys.stdout.flush()
    except Exception as e:
        print(f"\nCritical error: Failed to start or run server: {e}")
        sys.stdout.flush()
    finally:
        # --- Stop Discovery Thread ---
        print("Stopping discovery broadcast thread...")
        sys.stdout.flush()
        stop_event.set()
        discovery_thread.join(timeout=2.0) # Wait for thread to finish gracefully
        # --------------------------
        server_socket.close()
        print("Command server socket closed.")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
