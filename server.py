import socket
import pydirectinput
import json
import time
import sys # Import sys for flushing output

# Configuration
PORT = 5005  # Port to listen on
BUFFER_SIZE = 1024  # Maximum size of incoming UDP packets

def execute_key_event(data):
    """Handles 'key_event' actions (keyboard keys only) from the parsed JSON data."""
    key = data.get('key')
    modifiers = data.get('modifiers', []) # Default to empty list
    press_type_data = data.get('pressType', {}) # Default to empty dict
    press_type = press_type_data.get('type', 'tap') # Default to 'tap'
    duration_ms = press_type_data.get('durationMs') # Will be None if type is 'tap'

    if not key:
        print("    -> Error: 'key' field missing in key_event data.")
        return

    # --- Modifier Key Handling ---
    # Press down all modifier keys FIRST
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")

    # --- Main Action Execution (Keyboard Keys Only) ---
    try:
        # Handle as standard Keyboard Key Action
        if press_type == 'tap':
            print(f"    -> Simulating key tap: '{key}' with modifiers {modifiers}")
            pydirectinput.press(key) # Modifiers already held
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                print(f"    -> Warning: Invalid hold duration ({duration_ms}ms) for key '{key}'. Performing tap instead.")
                pydirectinput.press(key) # Modifiers already held
            else:
                print(f"    -> Simulating key hold: '{key}' for {duration_sec:.2f}s with modifiers {modifiers}")
                pydirectinput.keyDown(key) # Modifiers already held
                time.sleep(duration_sec)
                pydirectinput.keyUp(key)
        else:
            print(f"    -> Warning: Invalid pressType ('{press_type}') or missing durationMs for key '{key}'. Performing tap.")
            pydirectinput.press(key) # Modifiers already held

    except Exception as action_e:
        print(f"    -> Error executing action for key '{key}': {action_e}")
    finally: # Ensure modifiers are released even if action fails
        # --- Modifier Key Handling (Release) ---
        # Release modifiers AFTER main action is done
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
            except Exception as mod_e:
                print(f"    -> Warning: Failed to release modifier '{mod_key}': {mod_e}")


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
        return

    # --- Modifier Key Handling ---
    # Hold keyboard modifiers if present
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
            print(f"    -> Holding modifier: {mod_key}")
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")

    # --- Main Mouse Action ---
    try:
        if press_type == 'tap':
            print(f"    -> Simulating mouse click: '{button}' button with modifiers {modifiers}")
            pydirectinput.click(button=button)
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                 print(f"    -> Warning: Invalid hold duration ({duration_ms}ms) for mouse button '{button}'. Performing click instead.")
                 pydirectinput.click(button=button)
            else:
                print(f"    -> Simulating mouse hold: '{button}' button for {duration_sec:.2f}s with modifiers {modifiers}")
                pydirectinput.mouseDown(button=button)
                time.sleep(duration_sec)
                pydirectinput.mouseUp(button=button)
        else:
             print(f"    -> Warning: Invalid pressType ('{press_type}') or missing durationMs for mouse button '{button}'. Performing click.")
             pydirectinput.click(button=button)

    except Exception as mouse_e:
        print(f"    -> Error executing mouse action for button '{button}': {mouse_e}")
    finally:
        # --- Modifier Key Handling (Release) ---
        # Release keyboard modifiers if they were held
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
                print(f"    -> Releasing modifier: {mod_key}")
            except Exception as mod_e:
                print(f"    -> Warning: Failed to release modifier '{mod_key}': {mod_e}")


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
        return

    # --- Modifier Key Handling ---
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
            print(f"    -> Holding modifier: {mod_key}")
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")

    # --- Main Scroll Action ---
    try:
        print(f"    -> Simulating mouse scroll: direction '{direction}', clicks {clicks} (amount {scroll_amount}) with modifiers {modifiers}")
        pydirectinput.scroll(scroll_amount)
    except Exception as scroll_e:
         print(f"    -> Error executing mouse scroll: {scroll_e}")
    finally:
        # --- Modifier Key Handling (Release) ---
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
                print(f"    -> Releasing modifier: {mod_key}")
            except Exception as mod_e:
                print(f"    -> Warning: Failed to release modifier '{mod_key}': {mod_e}")


def main():
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Bind the socket to all available network interfaces and the specified port
        server_socket.bind(('0.0.0.0', PORT))
        print(f"UDP server listening on port {PORT}...")
        sys.stdout.flush() # Ensure print statements appear immediately

        while True:
            try:
                # Wait for a UDP packet
                data_bytes, addr = server_socket.recvfrom(BUFFER_SIZE)
                json_string = data_bytes.decode('utf-8').strip()
                print(f"\nReceived raw data: '{json_string}' from {addr}")
                sys.stdout.flush()

                # Parse the JSON string
                try:
                    action_data = json.loads(json_string)
                except json.JSONDecodeError as json_e:
                    print(f"    -> Error: Invalid JSON received: {json_e}")
                    continue # Skip to the next packet

                # Determine action type and execute
                action_type = action_data.get('type')

                if action_type == 'key_event':
                    execute_key_event(action_data)
                elif action_type == 'mouse_event':
                    execute_mouse_event(action_data)
                elif action_type == 'mouse_scroll':
                    execute_mouse_scroll(action_data) # Now handles modifiers
                else:
                    print(f"    -> Warning: Unknown action type '{action_type}' received.")

            except UnicodeDecodeError:
                print(f"    -> Error: Received data from {addr} could not be decoded as UTF-8.")
            except Exception as loop_e:
                # Catch other potential errors within the loop (e.g., network issues)
                print(f"    -> Error processing packet from {addr}: {loop_e}")

            sys.stdout.flush() # Flush output buffer after processing each packet

    except Exception as e:
        print(f"\nCritical error: Failed to start or run server: {e}")
    finally:
        server_socket.close()
        print("\nServer socket closed.")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
