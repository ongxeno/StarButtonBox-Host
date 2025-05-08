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
import dialog_handler # Handles the Tkinter dialog or fallback

def handle_shutdown(signum, frame):
    """Signal handler for graceful shutdown."""
    print(f"\nReceived signal {signum}. Shutting down...")
    sys.stdout.flush()
    mdns_handler.unregister_mdns_service()
    sys.exit(0)

def main():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Register mDNS service
    if not mdns_handler.register_mdns_service():
        print("Failed to initialize mDNS. Exiting.", file=sys.stderr)
        sys.stdout.flush()
        return # Exit if mDNS registration fails

    # Create UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Bind the socket to listen on all interfaces on the specified port
        server_socket.bind(('0.0.0.0', config.COMMAND_PORT))
        print(f"UDP server listening on port {config.COMMAND_PORT}...")
        sys.stdout.flush()

        # --- Main Listening Loop ---
        while True:
            try:
                # Wait for and receive data
                data_bytes, addr = server_socket.recvfrom(config.BUFFER_SIZE)
                # Decode received bytes to UTF-8 string
                json_string = data_bytes.decode('utf-8').strip()

                # Attempt to parse the JSON string
                try:
                    packet_data = json.loads(json_string)
                except json.JSONDecodeError as json_e:
                    print(f"    -> Error: Invalid JSON received from {addr}: {json_e}", file=sys.stderr)
                    sys.stdout.flush()
                    continue # Skip processing this malformed packet

                # Extract packet details
                packet_type = packet_data.get('type')
                packet_id = packet_data.get('packetId')
                payload_str = packet_data.get('payload') # Payload is expected to be a string

                # --- Packet Handling Logic ---
                if packet_type == config.PACKET_TYPE_HEALTH_CHECK_PING:
                    # Handle PING: Send PONG back
                    # print(f"  -> Received PING (ID: {packet_id}) from {addr}") # Reduce verbosity
                    # sys.stdout.flush()
                    if packet_id:
                        pong_packet = {
                            "packetId": packet_id,
                            "timestamp": int(time.time() * 1000), # Server's timestamp
                            "type": config.PACKET_TYPE_HEALTH_CHECK_PONG,
                            "payload": None
                        }
                        try:
                            server_socket.sendto(json.dumps(pong_packet).encode('utf-8'), addr)
                        except Exception as send_e:
                            print(f"    -> Error sending PONG for ID {packet_id}: {send_e}", file=sys.stderr)
                            sys.stdout.flush()
                    else:
                        print(f"    -> Warning: PING from {addr} missing packetId.", file=sys.stderr)
                        sys.stdout.flush()

                elif packet_type == config.PACKET_TYPE_MACRO_COMMAND:
                    # Handle MACRO: Process payload and send ACK
                    # print(f"  -> Received MACRO (ID: {packet_id}) from {addr}") # Reduce verbosity
                    # sys.stdout.flush()
                    ack_sent = False
                    if payload_str:
                        try:
                            # Decode the payload string (which is JSON for the action)
                            action_data = json.loads(payload_str)
                            action_subtype = action_data.get('type') # e.g., 'key_event'

                            # Dispatch to the appropriate input simulator function
                            if action_subtype == 'key_event':
                                input_simulator.execute_key_event(action_data)
                            elif action_subtype == 'mouse_event':
                                input_simulator.execute_mouse_event(action_data)
                            elif action_subtype == 'mouse_scroll':
                                input_simulator.execute_mouse_scroll(action_data)
                            else:
                                print(f"    -> Warning: Unknown action subtype '{action_subtype}' in MACRO payload.", file=sys.stderr)
                                sys.stdout.flush()
                        except json.JSONDecodeError as e:
                            print(f"    -> Error decoding MACRO payload string: {e}", file=sys.stderr)
                            sys.stdout.flush()
                        except Exception as e:
                            print(f"    -> Error processing MACRO payload: {e}", file=sys.stderr)
                            sys.stdout.flush()
                        # --- Send ACK regardless of payload processing success ---
                        finally:
                            if packet_id:
                                ack_packet = {
                                    "packetId": packet_id,
                                    "timestamp": int(time.time() * 1000), # Server's timestamp
                                    "type": config.PACKET_TYPE_MACRO_ACK,
                                    "payload": None
                                }
                                try:
                                    server_socket.sendto(json.dumps(ack_packet).encode('utf-8'), addr)
                                    ack_sent = True
                                except Exception as send_e:
                                    print(f"    -> Error sending ACK for ID {packet_id}: {send_e}", file=sys.stderr)
                                    sys.stdout.flush()
                    else:
                        # Payload missing, still try to ACK if ID exists
                        print(f"    -> Warning: MACRO_COMMAND from {addr} missing payload.", file=sys.stderr)
                        sys.stdout.flush()

                    if not ack_sent and packet_id:
                         ack_packet = { "packetId": packet_id, "timestamp": int(time.time() * 1000), "type": config.PACKET_TYPE_MACRO_ACK, "payload": None }
                         try:
                             server_socket.sendto(json.dumps(ack_packet).encode('utf-8'), addr)
                         except Exception as send_e:
                             print(f"    -> Error sending ACK for ID {packet_id} (missing payload case): {send_e}", file=sys.stderr)
                             sys.stdout.flush()

                elif packet_type == config.PACKET_TYPE_TRIGGER_IMPORT_BROWSER:
                    # Handle Import Trigger: Extract URL and call dialog handler
                    print(f"  -> Received TRIGGER_IMPORT_BROWSER (ID: {packet_id}) from {addr}")
                    sys.stdout.flush()
                    if payload_str:
                        try:
                            # Decode the payload string (contains TriggerImportPayload JSON)
                            trigger_data = json.loads(payload_str)
                            url_to_open = trigger_data.get('url')
                            if url_to_open:
                                # Call the handler function (which runs dialog in a thread)
                                dialog_handler.trigger_pc_browser(url_to_open)
                            else:
                                print(f"    -> Error: Missing 'url' in TRIGGER_IMPORT_BROWSER payload.", file=sys.stderr)
                                sys.stdout.flush()
                        except json.JSONDecodeError as e:
                            print(f"    -> Error decoding TRIGGER_IMPORT_BROWSER payload: {e}", file=sys.stderr)
                            sys.stdout.flush()
                        except Exception as e:
                            print(f"    -> Error processing TRIGGER_IMPORT_BROWSER payload: {e}", file=sys.stderr)
                            sys.stdout.flush()
                    else:
                        print(f"    -> Warning: TRIGGER_IMPORT_BROWSER from {addr} missing payload.", file=sys.stderr)
                        sys.stdout.flush()
                    # No ACK needed for this type

                else:
                    # Handle unknown packet types
                    print(f"    -> Warning: Unknown packet type '{packet_type}' received from {addr}.", file=sys.stderr)
                    sys.stdout.flush()

            # --- Error handling for the inner loop (processing a single packet) ---
            except UnicodeDecodeError:
                print(f"    -> Error: Received data from {addr} could not be decoded as UTF-8.", file=sys.stderr)
                sys.stdout.flush()
            except Exception as loop_e:
                print(f"    -> Error processing packet from {addr}: {loop_e}", file=sys.stderr)
                sys.stdout.flush()
            # Ensure output buffer is flushed regularly
            sys.stdout.flush()

    # --- Error handling for the outer loop (binding the socket, etc.) ---
    except Exception as e:
        print(f"\nCritical error running server: {e}", file=sys.stderr)
        sys.stdout.flush()
    # --- Cleanup ---
    finally:
        if server_socket:
            server_socket.close()
            print("Server socket closed.")
            sys.stdout.flush()
        # Ensure mDNS is unregistered on exit
        mdns_handler.unregister_mdns_service()

# --- Script Entry Point ---
if __name__ == "__main__":
    main()
