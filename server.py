import socket
import pydirectinput

# Configuration
PORT = 5005  # Port to listen on
BUFFER_SIZE = 1024  # Maximum size of incoming UDP packets
COMMAND_TO_KEY_MAPPING = {
    # Flight / Systems
    "FlightReady":          ['altright', 'r'], # Default Flight Ready seems to be RAlt+R
    "Engines_Toggle":       'i',               # Toggle Engines Power (Matches Engines_Toggle)
    "Shields_Toggle":       'o',               # Toggle Shields Power
    "Weapons_Toggle":       'p',               # Toggle Weapons Power
    "Lights":               'l',               # Toggle Lights
    "LandingGear":          'n',               # Toggle Landing Gear
    "Decoupled":            'c',               # Toggle Decoupled Mode (HOLD C often, but press might work)
    "VTOL":                 'k',               # Toggle VTOL Mode
    "Cruise":               ['altright', 'c'], # Toggle Cruise Control (RAlt+C seems common)

    # Quantum Travel
    "Quantum_Spool":        'b',               # Tap B often toggles QT mode / starts spool
    "Quantum_Engage":       'b',               # HOLD B engages - pydirectinput.press('b') might work, or need hold logic later

    # Scanning
    "ScanMode":             'v',               # Toggle Scan Mode
    "Scan_Ping":            'tab',             # Activate Ping (often TAB)

    # Targeting (Based on common defaults / 3.23 notes)
    "Target_Hostile_Nearest": 't',             # Target nearest hostile / cycle forward
    "Target_Friendly_Nearest": '6',            # Cycle friendlies forward (no direct "nearest")
    "Target_Pin":           None,              # No clear universal default - Map in SC or assign key here
    "Target_Subcomponent_Reset": ['altleft', 'r'], # Reset subtarget targeting

    # Countermeasures
    "CM_Launch_Decoy":      'h',               # Launch Decoy burst
    "CM_Launch_Noise":      'j',               # Launch Noise
    "CM_Panic":             ['h', 'j'],        # Example: Press both Decoy and Noise for Panic

    # Emergency
    "Eject":                ['altright', 'y'], # Default Eject seems to be RAlt+Y
    "SelfDestruct":         'backspace',       # HOLD Backspace - press might initiate, need hold logic later

    # ATC / Doors
    "Request_Landing":      ['altleft', 'n'],  # Request Landing Clearance
    "Doors":                None,              # No clear universal default for general 'Doors' - Map in SC

    # Power Management (+/- Power commands from app)
    # Default SC uses F5-F8 for presets or Numpad for shield facings.
    # Direct "+/- Power" isn't standard. Mapping these conceptually:
    "Weapons_IncreasePower": ['f7'],             # Conceptual: Set Power to Weapons Preset
    "Weapons_DecreasePower": ['f8'],             # Conceptual: Reset Power Triangle
    "Shields_IncreasePower": ['f6'],             # Conceptual: Set Power to Shields Preset
    "Shields_DecreasePower": ['f8'],             # Conceptual: Reset Power Triangle
    "Engines_IncreasePower": ['f5'],             # Conceptual: Set Power to Engines Preset
    "Engines_DecreasePower": ['f8'],             # Conceptual: Reset Power Triangle
    # Coolers don't have direct power toggle/presets typically bound
    "Coolers_Toggle":       None,
    "Coolers_IncreasePower":None,
    "Coolers_DecreasePower":None,

    # Other (if needed)
    # Add any other commands sent by your specific app layout here
}

def main():
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # Bind the socket to all available network interfaces and the specified port
        server_socket.bind(('0.0.0.0', PORT))
        print(f"UDP server is listening on port {PORT}...")
        
        while True:
            # Inside the main while True loop, after decoding the command:
            try:
                # Wait for a UDP packet
                data, addr = server_socket.recvfrom(BUFFER_SIZE)
                command = data.decode('utf-8').strip()
                print(f"Received command: '{command}' from {addr}")

                # Look up the key(s) for the command using .get() for safety
                keys_to_press = COMMAND_TO_KEY_MAPPING.get(command) # Use .get()

                if keys_to_press is not None:
                    if isinstance(keys_to_press, list) and len(keys_to_press) > 0:
                        # Handle key combinations using keyDown/keyUp
                        modifier_keys = keys_to_press[:-1] # All keys except the last one are modifiers
                        main_key = keys_to_press[-1]       # The last key is the main one to press

                        print(f"    -> Simulating combination: Hold {modifier_keys}, Press '{main_key}'")

                        # Press down modifier keys
                        for mod_key in modifier_keys:
                            pydirectinput.keyDown(mod_key)
                            # time.sleep(0.01) # Optional small delay

                        # Press and release the main key
                        pydirectinput.press(main_key)
                        # time.sleep(0.01) # Optional small delay

                        # Release modifier keys in reverse order (good practice)
                        for mod_key in reversed(modifier_keys):
                            pydirectinput.keyUp(mod_key)
                            # time.sleep(0.01) # Optional small delay
                    elif isinstance(keys_to_press, str):
                        # Handle single key press
                        print(f"    -> Simulating key press: '{keys_to_press}'")
                        pydirectinput.press(keys_to_press)
                    else:
                        # Should not happen with a well-formed dictionary, but good practice
                        print(f"    -> Warning: Invalid key type '{type(keys_to_press)}' in mapping for command '{command}'")
                # Handle commands explicitly mapped to None (no action)
                elif command in COMMAND_TO_KEY_MAPPING: # Check if key exists but value is None
                     print(f"    -> Info: Command '{command}' is configured for no action (None).")
                # Handle commands not found in the dictionary at all
                else:
                    print(f"    -> Warning: Command '{command}' not found in key mapping.")
                    
            except UnicodeDecodeError:
                print(f"Error: Received data from {addr} could not be decoded as UTF-8.")
            except Exception as e:
                print(f"Error processing command from {addr}: {e}")
    
    except Exception as e:
        print(f"Failed to start server: {e}")
    finally:
        server_socket.close()
        print("Server socket closed.")

if __name__ == "__main__":
    main()