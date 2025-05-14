# server.py
# Main script for the StarButtonBox PC server. Listens for UDP packets,
# handles health checks, dispatches commands to input_simulator,
# triggers mDNS registration, and manages auto drag-and-drop logic.
# Macro commands and auto drag operations are processed in threads.

import socket
import json
import time
import sys
import signal
import threading
from concurrent.futures import ThreadPoolExecutor

# Import modules from the project structure
import config
import input_simulator
import mdns_handler
import dialog_handler
import auto_drag_handler # New import for auto drag-and-drop logic

# Global executor variable
executor = None

def handle_shutdown(signum, frame):
    """Signal handler for graceful shutdown."""
    print(f"\nReceived signal {signum}. Shutting down server...")
    sys.stdout.flush()

    global executor
    if executor:
        print("Shutting down thread pool...")
        sys.stdout.flush()
        executor.shutdown(wait=True)
        print("Thread pool shutdown complete.")
        sys.stdout.flush()

    # Ensure auto_drag_loop is also stopped gracefully
    print("Stopping auto drag loop if active...")
    sys.stdout.flush()
    auto_drag_handler.stop_auto_drag_loop() # Call stop for the auto drag loop
    print("Auto drag loop stop signal sent.")
    sys.stdout.flush()

    mdns_handler.unregister_mdns_service()
    sys.exit(0)


def main():
    global executor

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Initialize ThreadPoolExecutor for macro commands
    executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='MacroWorker')
    print(f"ThreadPoolExecutor initialized with max_workers={executor._max_workers}")
    sys.stdout.flush()

    # Register mDNS service
    if not mdns_handler.register_mdns_service():
        print("Failed to initialize mDNS. Exiting.", file=sys.stderr)
        sys.stdout.flush()
        if executor:
            executor.shutdown(wait=False)
        return

    # Create UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Bind the socket
        server_socket.bind(('0.0.0.0', config.COMMAND_PORT))
        print(f"UDP server listening on port {config.COMMAND_PORT}...")
        sys.stdout.flush()

        # Main Listening Loop
        while True:
            try:
                data_bytes, addr = server_socket.recvfrom(config.BUFFER_SIZE)
                packet_received_time_ns = time.perf_counter_ns()
                json_string = data_bytes.decode('utf-8').strip()

                try:
                    packet_data = json.loads(json_string)
                except json.JSONDecodeError as json_e:
                    print(f"    -> Error: Invalid JSON from {addr}: {json_e}", file=sys.stderr)
                    sys.stdout.flush()
                    continue

                packet_type = packet_data.get('type')
                packet_id = packet_data.get('packetId')
                payload_str = packet_data.get('payload')

                print(f"  -> Received packet: Type='{packet_type}', ID='{packet_id}', From={addr}")
                sys.stdout.flush()

                # Packet Handling Logic
                if packet_type == config.PACKET_TYPE_HEALTH_CHECK_PING:
                    if packet_id:
                        pong_timestamp = int(time.time() * 1000)
                        pong_packet = {
                            "packetId": packet_id,
                            "timestamp": pong_timestamp,
                            "type": config.PACKET_TYPE_HEALTH_CHECK_PONG,
                            "payload": None
                        }
                        try:
                            server_socket.sendto(json.dumps(pong_packet).encode('utf-8'), addr)
                        except Exception as send_e:
                            print(f"    -> Error sending PONG: {send_e}", file=sys.stderr)
                    else:
                        print(f"    -> Warning: PING missing packetId.", file=sys.stderr)

                elif packet_type == config.PACKET_TYPE_MACRO_COMMAND:
                    if not packet_id:
                        print(f"    -> Warning: MACRO_COMMAND missing packetId. Cannot send ACK or process.", file=sys.stderr)
                        continue

                    ack_timestamp = int(time.time() * 1000)
                    ack_packet = {
                        "packetId": packet_id,
                        "timestamp": ack_timestamp,
                        "type": config.PACKET_TYPE_MACRO_ACK,
                        "payload": None
                    }
                    try:
                        server_socket.sendto(json.dumps(ack_packet).encode('utf-8'), addr)
                        print(f"    -> Sent ACK (ID: {packet_id}) at server time: {ack_timestamp}")
                    except Exception as send_e:
                        print(f"    -> Error sending ACK for MACRO_COMMAND (ID: {packet_id}): {send_e}", file=sys.stderr)

                    if payload_str:
                        executor.submit(input_simulator.process_macro_in_thread, payload_str, packet_id, packet_received_time_ns)
                    else:
                        print(f"    -> Warning: MACRO_COMMAND (ID: {packet_id}) missing payload. No action submitted.", file=sys.stderr)

                elif packet_type == config.PACKET_TYPE_TRIGGER_IMPORT_BROWSER:
                    print(f"  -> Handling TRIGGER_IMPORT_BROWSER (ID: {packet_id})")
                    if payload_str:
                        try:
                            trigger_data = json.loads(payload_str)
                            url_to_open = trigger_data.get('url')
                            if url_to_open:
                                dialog_thread = threading.Thread(
                                    target=dialog_handler.trigger_pc_browser,
                                    args=(url_to_open,),
                                    daemon=True
                                )
                                dialog_thread.start()
                            else:
                                print(f"    -> Error: Missing 'url' in TRIGGER_IMPORT_BROWSER payload...", file=sys.stderr)
                        except Exception as e:
                            print(f"    -> Error processing TRIGGER_IMPORT_BROWSER payload: {e}", file=sys.stderr)
                    else:
                        print(f"    -> Warning: TRIGGER_IMPORT_BROWSER missing payload.", file=sys.stderr)

                # --- New Auto Drag and Drop Packet Handling ---
                elif packet_type == config.PACKET_TYPE_CAPTURE_MOUSE_POSITION:
                    print(f"  -> Handling CAPTURE_MOUSE_POSITION (ID: {packet_id})")
                    if payload_str:
                        try:
                            capture_payload = json.loads(payload_str)
                            purpose = capture_payload.get('purpose')
                            if purpose in ["SRC", "DES"]:
                                # No need to run in a separate thread as pyautogui.position() is quick
                                auto_drag_handler.capture_mouse_position(purpose)
                            else:
                                print(f"    -> Error: Invalid 'purpose' ('{purpose}') in CAPTURE_MOUSE_POSITION payload.", file=sys.stderr)
                        except json.JSONDecodeError as e:
                            print(f"    -> Error decoding CAPTURE_MOUSE_POSITION payload: {e}", file=sys.stderr)
                        except Exception as e:
                            print(f"    -> Error processing CAPTURE_MOUSE_POSITION: {e}", file=sys.stderr)
                    else:
                        print(f"    -> Warning: CAPTURE_MOUSE_POSITION (ID: {packet_id}) missing payload.", file=sys.stderr)

                elif packet_type == config.PACKET_TYPE_AUTO_DRAG_LOOP_COMMAND:
                    print(f"  -> Handling AUTO_DRAG_LOOP_COMMAND (ID: {packet_id})")
                    if payload_str:
                        try:
                            loop_payload = json.loads(payload_str)
                            action = loop_payload.get('action')
                            if action == "START":
                                auto_drag_handler.start_auto_drag_loop()
                            elif action == "STOP":
                                auto_drag_handler.stop_auto_drag_loop()
                            else:
                                print(f"    -> Error: Invalid 'action' ('{action}') in AUTO_DRAG_LOOP_COMMAND payload.", file=sys.stderr)
                        except json.JSONDecodeError as e:
                            print(f"    -> Error decoding AUTO_DRAG_LOOP_COMMAND payload: {e}", file=sys.stderr)
                        except Exception as e:
                            print(f"    -> Error processing AUTO_DRAG_LOOP_COMMAND: {e}", file=sys.stderr)
                    else:
                        print(f"    -> Warning: AUTO_DRAG_LOOP_COMMAND (ID: {packet_id}) missing payload.", file=sys.stderr)
                # --- End New Packet Handling ---

                else:
                    print(f"    -> Warning: Unknown packet type '{packet_type}'.", file=sys.stderr)

            except UnicodeDecodeError:
                print(f"    -> Error: Cannot decode UTF-8 from {addr}.", file=sys.stderr)
            except Exception as loop_e:
                print(f"    -> Error processing packet from {addr}: {loop_e}", file=sys.stderr)
            sys.stdout.flush()

    except Exception as e:
        print(f"\nCritical error running server: {e}", file=sys.stderr)
        sys.stdout.flush()
    finally:
        print("\nInitiating final server cleanup...")
        sys.stdout.flush()
        if server_socket:
            server_socket.close()
            print("Server socket closed.")
            sys.stdout.flush()

        if executor:
            print("Shutting down thread pool in finally block...")
            sys.stdout.flush()
            executor.shutdown(wait=True)
            print("Thread pool shutdown complete in finally block.")
            sys.stdout.flush()
        
        # Ensure auto_drag_loop is also stopped gracefully during final cleanup
        print("Stopping auto drag loop if active (final cleanup)...")
        sys.stdout.flush()
        auto_drag_handler.stop_auto_drag_loop()
        print("Auto drag loop stop signal sent (final cleanup).")
        sys.stdout.flush()

        mdns_handler.unregister_mdns_service()
        print("Server shutdown complete.")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
