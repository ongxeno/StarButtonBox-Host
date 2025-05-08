# server.py
# Main script for the StarButtonBox PC server. Listens for UDP packets,
# handles health checks, dispatches commands to input_simulator,
# triggers mDNS registration, and manages the import dialog flow.

import socket
import json
import time
import sys
import signal

# Import modules from the project structure
import config
import input_simulator
import mdns_handler
import dialog_handler # Handles the browser opening trigger

def handle_shutdown(signum, frame):
    """Signal handler for graceful shutdown."""
    print(f"\nReceived signal {signum}. Shutting down...")
    sys.stdout.flush()
    mdns_handler.unregister_mdns_service()
    sys.exit(0)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Register mDNS service
    if not mdns_handler.register_mdns_service():
        print("Failed to initialize mDNS. Exiting.", file=sys.stderr)
        sys.stdout.flush()
        return

    # Create UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Bind the socket
        server_socket.bind(('0.0.0.0', config.COMMAND_PORT))
        print(f"UDP server listening on port {config.COMMAND_PORT}...")
        sys.stdout.flush()

        # --- Main Listening Loop ---
        while True:
            try:
                data_bytes, addr = server_socket.recvfrom(config.BUFFER_SIZE)
                json_string = data_bytes.decode('utf-8').strip()

                try: packet_data = json.loads(json_string)
                except json.JSONDecodeError as json_e:
                    print(f"    -> Error: Invalid JSON from {addr}: {json_e}", file=sys.stderr)
                    sys.stdout.flush(); continue

                packet_type = packet_data.get('type')
                packet_id = packet_data.get('packetId')
                payload_str = packet_data.get('payload')

                # --- Packet Handling Logic ---
                if packet_type == config.PACKET_TYPE_HEALTH_CHECK_PING:
                    if packet_id:
                        pong_packet = {"packetId": packet_id, "timestamp": int(time.time() * 1000), "type": config.PACKET_TYPE_HEALTH_CHECK_PONG, "payload": None}
                        try: server_socket.sendto(json.dumps(pong_packet).encode('utf-8'), addr)
                        except Exception as send_e: print(f"    -> Error sending PONG: {send_e}", file=sys.stderr); sys.stdout.flush()
                    else: print(f"    -> Warning: PING missing packetId.", file=sys.stderr); sys.stdout.flush()

                elif packet_type == config.PACKET_TYPE_MACRO_COMMAND:
                    ack_sent = False
                    if payload_str:
                        try:
                            action_data = json.loads(payload_str)
                            action_subtype = action_data.get('type')
                            if action_subtype == 'key_event': input_simulator.execute_key_event(action_data)
                            elif action_subtype == 'mouse_event': input_simulator.execute_mouse_event(action_data)
                            elif action_subtype == 'mouse_scroll': input_simulator.execute_mouse_scroll(action_data)
                            else: print(f"    -> Warning: Unknown action subtype '{action_subtype}'...", file=sys.stderr)
                        except Exception as e: print(f"    -> Error processing MACRO payload: {e}", file=sys.stderr)
                        finally:
                            if packet_id:
                                ack_packet = {"packetId": packet_id, "timestamp": int(time.time() * 1000), "type": config.PACKET_TYPE_MACRO_ACK, "payload": None}
                                try: server_socket.sendto(json.dumps(ack_packet).encode('utf-8'), addr); ack_sent = True
                                except Exception as send_e: print(f"    -> Error sending ACK: {send_e}", file=sys.stderr)
                    else: print(f"    -> Warning: MACRO_COMMAND missing payload.", file=sys.stderr)

                    if not ack_sent and packet_id:
                         ack_packet = { "packetId": packet_id, "timestamp": int(time.time() * 1000), "type": config.PACKET_TYPE_MACRO_ACK, "payload": None }
                         try: server_socket.sendto(json.dumps(ack_packet).encode('utf-8'), addr)
                         except Exception as send_e: print(f"    -> Error sending ACK (missing payload case): {send_e}", file=sys.stderr)

                elif packet_type == config.PACKET_TYPE_TRIGGER_IMPORT_BROWSER:
                    print(f"  -> Received TRIGGER_IMPORT_BROWSER (ID: {packet_id}) from {addr}"); sys.stdout.flush()
                    if payload_str:
                        try:
                            trigger_data = json.loads(payload_str)
                            url_to_open = trigger_data.get('url')
                            if url_to_open:
                                # Call the simplified handler function
                                dialog_handler.trigger_pc_browser(url_to_open)
                            else: print(f"    -> Error: Missing 'url' in payload...", file=sys.stderr)
                        except Exception as e: print(f"    -> Error processing TRIGGER payload: {e}", file=sys.stderr)
                    else: print(f"    -> Warning: TRIGGER_IMPORT_BROWSER missing payload.", file=sys.stderr)

                else: print(f"    -> Warning: Unknown packet type '{packet_type}'.", file=sys.stderr)

            except UnicodeDecodeError: print(f"    -> Error: Cannot decode UTF-8.", file=sys.stderr); sys.stdout.flush()
            except Exception as loop_e: print(f"    -> Error processing packet: {loop_e}", file=sys.stderr); sys.stdout.flush()
            sys.stdout.flush() # Flush after processing each packet

    except Exception as e: print(f"\nCritical error running server: {e}", file=sys.stderr); sys.stdout.flush()
    finally:
        if server_socket: server_socket.close(); print("Server socket closed."); sys.stdout.flush()
        mdns_handler.unregister_mdns_service()

# --- Script Entry Point ---
if __name__ == "__main__":
    main()
