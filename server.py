# server.py
# Main script for the StarButtonBox PC server. Listens for UDP packets,
# handles health checks, dispatches commands to input_simulator,
# triggers mDNS registration, and manages the import dialog flow.
# Macro commands are now processed using a ThreadPoolExecutor.

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

    mdns_handler.unregister_mdns_service()
    sys.exit(0)


def main():
    global executor 

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Initialize ThreadPoolExecutor
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
                # Capture time as soon as data is received, before extensive processing
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
                            sys.stdout.flush()
                    else:
                        print(f"    -> Warning: PING missing packetId.", file=sys.stderr)
                        sys.stdout.flush()

                elif packet_type == config.PACKET_TYPE_MACRO_COMMAND:
                    if not packet_id:
                        print(f"    -> Warning: MACRO_COMMAND missing packetId. Cannot send ACK or process.", file=sys.stderr)
                        sys.stdout.flush()
                        continue 

                    # 1. Send ACK immediately
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
                        sys.stdout.flush()
                    except Exception as send_e:
                        print(f"    -> Error sending ACK for MACRO_COMMAND (ID: {packet_id}): {send_e}", file=sys.stderr)
                        sys.stdout.flush()
                    
                    # 2. Submit the macro command processing to the ThreadPoolExecutor
                    if payload_str:
                        # Pass the packet_received_time_ns to the worker thread
                        executor.submit(input_simulator.process_macro_in_thread, payload_str, packet_id, packet_received_time_ns)
                    else:
                        print(f"    -> Warning: MACRO_COMMAND (ID: {packet_id}) missing payload. No action submitted.", file=sys.stderr)
                        sys.stdout.flush()

                elif packet_type == config.PACKET_TYPE_TRIGGER_IMPORT_BROWSER:
                    print(f"  -> Received TRIGGER_IMPORT_BROWSER (ID: {packet_id}) from {addr}")
                    sys.stdout.flush()
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
                    sys.stdout.flush()

                else:
                    print(f"    -> Warning: Unknown packet type '{packet_type}'.", file=sys.stderr)
                    sys.stdout.flush()

            except UnicodeDecodeError:
                print(f"    -> Error: Cannot decode UTF-8 from {addr}.", file=sys.stderr)
                sys.stdout.flush()
            except Exception as loop_e:
                print(f"    -> Error processing packet from {addr}: {loop_e}", file=sys.stderr)
                sys.stdout.flush()
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
            
        mdns_handler.unregister_mdns_service()
        print("Server shutdown complete.")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
