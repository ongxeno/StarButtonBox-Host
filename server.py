import socket
import pydirectinput
import json
import time
import sys
import threading
import ipaddress
from zeroconf import ServiceInfo, Zeroconf, IPVersion
import signal

# --- Configuration ---
COMMAND_PORT = 5005  # Port for receiving commands and health checks
BUFFER_SIZE = 1024
MDNS_SERVICE_TYPE = "_starbuttonbox._udp.local."
MDNS_SERVICE_NAME = "StarButtonBox Server._starbuttonbox._udp.local." # Default, can be made more dynamic

# --- Packet Types (mirroring Android's UdpPacketType) ---
PACKET_TYPE_HEALTH_CHECK_PING = "HEALTH_CHECK_PING"
PACKET_TYPE_HEALTH_CHECK_PONG = "HEALTH_CHECK_PONG"
PACKET_TYPE_MACRO_COMMAND = "MACRO_COMMAND"
PACKET_TYPE_MACRO_ACK = "MACRO_ACK"


# --- Input Execution Functions (execute_key_event, execute_mouse_event, execute_mouse_scroll) ---
# These functions remain the same as in the previous version.
# For brevity, they are not repeated here but should be included from the previous artifact.
def execute_key_event(data):
    """Handles 'key_event' actions (keyboard keys only) from the parsed JSON data."""
    key = data.get('key')
    modifiers = data.get('modifiers', [])
    press_type_data = data.get('pressType', {})
    press_type = press_type_data.get('type', 'tap')
    duration_ms = press_type_data.get('durationMs')

    if not key:
        print("    -> Error: 'key' field missing in key_event data.")
        sys.stdout.flush()
        return

    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")
            sys.stdout.flush()
    try:
        if press_type == 'tap':
            print(f"    -> Simulating key tap: '{key}' with modifiers {modifiers}")
            sys.stdout.flush()
            pydirectinput.press(key)
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                print(f"    -> Warning: Invalid hold duration ({duration_ms}ms) for key '{key}'. Performing tap instead.")
                sys.stdout.flush()
                pydirectinput.press(key)
            else:
                print(f"    -> Simulating key hold: '{key}' for {duration_sec:.2f}s with modifiers {modifiers}")
                sys.stdout.flush()
                pydirectinput.keyDown(key)
                time.sleep(duration_sec)
                pydirectinput.keyUp(key)
        else:
            print(f"    -> Warning: Invalid pressType ('{press_type}') or missing durationMs for key '{key}'. Performing tap.")
            sys.stdout.flush()
            pydirectinput.press(key)
    except Exception as action_e:
        print(f"    -> Error executing action for key '{key}': {action_e}")
        sys.stdout.flush()
    finally:
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
    modifiers = data.get('modifiers', [])
    button_map = {"LEFT": "left", "RIGHT": "right", "MIDDLE": "middle"}
    button = button_map.get(button_str)

    if not button:
        print(f"    -> Error: Invalid or missing 'button' field ('{button_str}') in mouse_event data.")
        sys.stdout.flush()
        return

    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
            print(f"    -> Holding modifier: {mod_key}")
            sys.stdout.flush()
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")
            sys.stdout.flush()
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
    clicks = data.get('clicks', 1)
    modifiers = data.get('modifiers', [])
    scroll_amount = clicks if direction == "UP" else -clicks if direction == "DOWN" else 0

    if scroll_amount == 0:
        print(f"    -> Error: Invalid or missing 'direction' field ('{direction}') in mouse_scroll data.")
        sys.stdout.flush()
        return

    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
            print(f"    -> Holding modifier: {mod_key}")
            sys.stdout.flush()
        except Exception as mod_e:
            print(f"    -> Warning: Failed to press down modifier '{mod_key}': {mod_e}")
            sys.stdout.flush()
    try:
        print(f"    -> Simulating mouse scroll: direction '{direction}', clicks {clicks} (amount {scroll_amount}) with modifiers {modifiers}")
        sys.stdout.flush()
        pydirectinput.scroll(scroll_amount)
    except Exception as scroll_e:
         print(f"    -> Error executing mouse scroll: {scroll_e}")
         sys.stdout.flush()
    finally:
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
                print(f"    -> Releasing modifier: {mod_key}")
                sys.stdout.flush()
            except Exception as mod_e:
                print(f"    -> Warning: Failed to release modifier '{mod_key}': {mod_e}")
                sys.stdout.flush()

# --- mDNS and Shutdown Handling (get_local_ip, register_mdns_service, unregister_mdns_service, handle_shutdown) ---
# These functions remain the same as in the previous version.
# For brevity, they are not repeated here but should be included from the previous artifact.
def get_local_ip():
    """Attempts to find a non-loopback local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            return "127.0.0.1"

zeroconf = None
service_info = None

def register_mdns_service():
    """Registers the StarButtonBox service using Zeroconf."""
    global zeroconf, service_info
    try:
        zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        local_ip = get_local_ip()
        if local_ip == "127.0.0.1":
             print("Warning: Could not determine a non-loopback IP address. mDNS registration might fail or use loopback.")
             sys.stdout.flush()

        host_name = socket.gethostname().split('.')[0]
        service_name_str = f"{host_name} StarButtonBox Server._starbuttonbox._udp.local."

        service_info = ServiceInfo(
            type_=MDNS_SERVICE_TYPE,
            name=service_name_str,
            addresses=[socket.inet_aton(local_ip)],
            port=COMMAND_PORT,
            properties={},
            server=f"{host_name}.local.",
        )
        print(f"Registering mDNS service:")
        print(f"  Name: {service_name_str}")
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
        zeroconf = None

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
    unregister_mdns_service()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    register_mdns_service()
    if not zeroconf:
        print("Failed to initialize mDNS. Exiting.")
        sys.stdout.flush()
        return

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        server_socket.bind(('0.0.0.0', COMMAND_PORT))
        print(f"UDP command and health check server listening on port {COMMAND_PORT}...")
        sys.stdout.flush()

        while True:
            try:
                data_bytes, addr = server_socket.recvfrom(BUFFER_SIZE)
                json_string = data_bytes.decode('utf-8').strip()
                # print(f"\nReceived raw data: '{json_string}' from {addr}") # Debug
                # sys.stdout.flush()

                try:
                    packet_data = json.loads(json_string)
                except json.JSONDecodeError as json_e:
                    print(f"    -> Error: Invalid JSON received from {addr}: {json_e}")
                    sys.stdout.flush()
                    continue

                packet_type = packet_data.get('type')
                packet_id = packet_data.get('packetId')
                payload_str = packet_data.get('payload') # This is the stringified InputAction JSON

                if packet_type == PACKET_TYPE_HEALTH_CHECK_PING:
                    print(f"  -> Received HEALTH_CHECK_PING (ID: {packet_id}) from {addr}")
                    sys.stdout.flush()
                    if packet_id:
                        pong_packet = {
                            "packetId": packet_id,
                            "timestamp": int(time.time() * 1000),
                            "type": PACKET_TYPE_HEALTH_CHECK_PONG,
                            "payload": None
                        }
                        try:
                            server_socket.sendto(json.dumps(pong_packet).encode('utf-8'), addr)
                            print(f"    -> Sent HEALTH_CHECK_PONG (ID: {packet_id}) to {addr}")
                            sys.stdout.flush()
                        except Exception as send_e:
                            print(f"    -> Error sending PONG: {send_e}")
                            sys.stdout.flush()
                    else:
                        print(f"    -> Warning: HEALTH_CHECK_PING from {addr} missing packetId.")
                        sys.stdout.flush()

                elif packet_type == PACKET_TYPE_MACRO_COMMAND:
                    print(f"  -> Received MACRO_COMMAND (ID: {packet_id}, Has Payload: {payload_str is not None}) from {addr}")
                    sys.stdout.flush()
                    ack_sent = False
                    if payload_str:
                        try:
                            action_data = json.loads(payload_str) # The payload IS the action_data
                            action_subtype = action_data.get('type') # This is the inner type like 'key_event'

                            if action_subtype == 'key_event':
                                execute_key_event(action_data)
                            elif action_subtype == 'mouse_event':
                                execute_mouse_event(action_data)
                            elif action_subtype == 'mouse_scroll':
                                execute_mouse_scroll(action_data)
                            else:
                                print(f"    -> Warning: Unknown action subtype '{action_subtype}' in MACRO_COMMAND payload from {addr}.")
                                sys.stdout.flush()
                        except json.JSONDecodeError as e:
                            print(f"    -> Error decoding MACRO_COMMAND payload: {e}")
                            sys.stdout.flush()
                        except Exception as e:
                            print(f"    -> Error processing MACRO_COMMAND payload: {e}")
                            sys.stdout.flush()
                        finally:
                            # Send ACK regardless of payload processing success, as long as packet_id is present
                            if packet_id:
                                ack_packet = {
                                    "packetId": packet_id,
                                    "timestamp": int(time.time() * 1000),
                                    "type": PACKET_TYPE_MACRO_ACK,
                                    "payload": None # No payload needed for ACK
                                }
                                try:
                                    server_socket.sendto(json.dumps(ack_packet).encode('utf-8'), addr)
                                    print(f"    -> Sent MACRO_ACK (ID: {packet_id}) to {addr}")
                                    sys.stdout.flush()
                                    ack_sent = True
                                except Exception as send_e:
                                    print(f"    -> Error sending MACRO_ACK for ID {packet_id}: {send_e}")
                                    sys.stdout.flush()
                    else:
                        print(f"    -> Warning: MACRO_COMMAND from {addr} missing payload.")
                        sys.stdout.flush()
                    
                    if not ack_sent and packet_id: # If payload was missing but we have an ID, still try to ACK
                         print(f"    -> MACRO_COMMAND (ID: {packet_id}) had missing payload, but sending ACK anyway.")
                         sys.stdout.flush()
                         ack_packet = { "packetId": packet_id, "timestamp": int(time.time() * 1000), "type": PACKET_TYPE_MACRO_ACK, "payload": None }
                         try:
                             server_socket.sendto(json.dumps(ack_packet).encode('utf-8'), addr)
                             print(f"    -> Sent MACRO_ACK (ID: {packet_id}) to {addr} despite missing payload.")
                             sys.stdout.flush()
                         except Exception as send_e:
                             print(f"    -> Error sending MACRO_ACK for ID {packet_id} (missing payload case): {send_e}")
                             sys.stdout.flush()


                else:
                    print(f"    -> Warning: Unknown packet type '{packet_type}' received from {addr}.")
                    sys.stdout.flush()

            except UnicodeDecodeError:
                print(f"    -> Error: Received data from {addr} could not be decoded as UTF-8.")
                sys.stdout.flush()
            except Exception as loop_e:
                print(f"    -> Error processing packet from {addr}: {loop_e}")
                sys.stdout.flush()
            sys.stdout.flush()

    except Exception as e:
        print(f"\nCritical error running command server: {e}")
        sys.stdout.flush()
    finally:
        if server_socket:
            server_socket.close()
            print("Command server socket closed.")
            sys.stdout.flush()
        unregister_mdns_service()

if __name__ == "__main__":
    main()
