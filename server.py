# server.py
# Main script for the StarButtonBox PC server.
# Refactored to be controllable by a GUI, run in a separate thread,
# and provide callbacks for logging and status updates.

import socket
import json
import time
import sys
import signal
import threading
import logging # Using the logging module
from concurrent.futures import ThreadPoolExecutor

# Import modules from the project structure
import config
import input_simulator
import mdns_handler
import dialog_handler
import auto_drag_handler

# --- Global Variables for Server Control ---
server_thread = None
stop_server_event = threading.Event()
server_socket = None # Made global to be accessible by stop_server
executor = None # ThreadPoolExecutor for macro commands

# --- Logging Setup ---
# Basic configuration for file logging. GUI can add its own handler.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    filename='server.log', # Log to a file
    filemode='a' # Append to the log file
)
# Create a logger instance
logger = logging.getLogger("StarButtonBoxServer")

# --- Callback Placeholders ---
# These will be set by the GUI when it starts the server.
log_to_gui_callback = None
update_gui_status_callback = None

def _server_loop_task(port_to_use, mdns_service_enabled):
    """
    The main task that runs in the server_thread.
    Handles socket binding, mDNS, and packet listening.
    """
    global server_socket, executor, log_to_gui_callback, update_gui_status_callback

    # Initialize ThreadPoolExecutor for macro commands within this thread's context if needed
    # Or ensure the global one is used carefully. For simplicity, using the global one.
    if executor is None: # Should be initialized by start_server before thread starts
        logger.error("ThreadPoolExecutor not initialized before server loop task.")
        if update_gui_status_callback:
            update_gui_status_callback("Error: Executor not ready.")
        return

    if mdns_service_enabled:
        if not mdns_handler.register_mdns_service():
            logger.warning("Failed to initialize mDNS. Server will run without mDNS.")
            if update_gui_status_callback:
                update_gui_status_callback(f"Running on Port {port_to_use} (mDNS Failed)")
        else:
            logger.info("mDNS service registered successfully.")
            if update_gui_status_callback:
                 update_gui_status_callback(f"Running on Port {port_to_use} (mDNS Active)")
    else:
        logger.info("mDNS service is disabled by configuration.")
        if update_gui_status_callback:
            update_gui_status_callback(f"Running on Port {port_to_use} (mDNS Disabled)")

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(('0.0.0.0', port_to_use))
        # Set a timeout so that recvfrom doesn't block indefinitely,
        # allowing the stop_server_event to be checked periodically.
        server_socket.settimeout(1.0) # 1 second timeout
        logger.info(f"UDP server listening on port {port_to_use}...")
        if log_to_gui_callback:
            log_to_gui_callback(f"INFO: UDP server listening on port {port_to_use}...")

    except Exception as e:
        logger.error(f"Critical error binding server socket to port {port_to_use}: {e}")
        if log_to_gui_callback:
            log_to_gui_callback(f"ERROR: Could not bind to port {port_to_use}: {e}")
        if update_gui_status_callback:
            update_gui_status_callback(f"Error: Port {port_to_use} in use?")
        mdns_handler.unregister_mdns_service() # Clean up mDNS if it was started
        return

    # Main Listening Loop
    while not stop_server_event.is_set():
        try:
            data_bytes, addr = server_socket.recvfrom(config.BUFFER_SIZE)
            packet_received_time_ns = time.perf_counter_ns()
            json_string = data_bytes.decode('utf-8').strip()

            try:
                packet_data = json.loads(json_string)
            except json.JSONDecodeError as json_e:
                logger.warning(f"Invalid JSON from {addr}: {json_e} - Data: '{json_string[:100]}'")
                if log_to_gui_callback:
                    log_to_gui_callback(f"WARN: Invalid JSON from {addr}: {json_e}")
                continue

            packet_type = packet_data.get('type')
            packet_id = packet_data.get('packetId')
            payload_str = packet_data.get('payload')

            log_message = f"Received packet: Type='{packet_type}', ID='{packet_id}', From={addr}"
            logger.info(log_message)
            if log_to_gui_callback: # Send to GUI
                log_to_gui_callback(f"INFO: {log_message}")


            # Packet Handling Logic (Simplified for brevity, same as before but using logger)
            if packet_type == config.PACKET_TYPE_HEALTH_CHECK_PING:
                if packet_id:
                    pong_timestamp = int(time.time() * 1000)
                    pong_packet = {
                        "packetId": packet_id, "timestamp": pong_timestamp,
                        "type": config.PACKET_TYPE_HEALTH_CHECK_PONG, "payload": None
                    }
                    try:
                        server_socket.sendto(json.dumps(pong_packet).encode('utf-8'), addr)
                    except Exception as send_e:
                        logger.error(f"Error sending PONG: {send_e}")
                else:
                    logger.warning("PING missing packetId.")

            elif packet_type == config.PACKET_TYPE_MACRO_COMMAND:
                if not packet_id:
                    logger.warning("MACRO_COMMAND missing packetId. Cannot send ACK or process.")
                    continue
                ack_timestamp = int(time.time() * 1000)
                ack_packet = {
                    "packetId": packet_id, "timestamp": ack_timestamp,
                    "type": config.PACKET_TYPE_MACRO_ACK, "payload": None
                }
                try:
                    server_socket.sendto(json.dumps(ack_packet).encode('utf-8'), addr)
                    logger.info(f"Sent ACK (ID: {packet_id})")
                except Exception as send_e:
                    logger.error(f"Error sending ACK for MACRO_COMMAND (ID: {packet_id}): {send_e}")

                if payload_str and executor:
                    executor.submit(input_simulator.process_macro_in_thread, payload_str, packet_id, packet_received_time_ns)
                elif not payload_str:
                    logger.warning(f"MACRO_COMMAND (ID: {packet_id}) missing payload.")
                elif not executor:
                    logger.error("Executor not available for MACRO_COMMAND.")


            elif packet_type == config.PACKET_TYPE_TRIGGER_IMPORT_BROWSER:
                logger.info(f"Handling TRIGGER_IMPORT_BROWSER (ID: {packet_id})")
                if payload_str:
                    try:
                        trigger_data = json.loads(payload_str)
                        url_to_open = trigger_data.get('url')
                        if url_to_open:
                            # dialog_handler.trigger_pc_browser is synchronous for printing,
                            # but webbrowser.open might be better in a thread if it blocks.
                            # For now, keeping it simple.
                            dialog_handler.trigger_pc_browser(url_to_open)
                        else:
                            logger.error("Missing 'url' in TRIGGER_IMPORT_BROWSER payload.")
                    except Exception as e:
                        logger.error(f"Error processing TRIGGER_IMPORT_BROWSER payload: {e}")
                else:
                    logger.warning(f"TRIGGER_IMPORT_BROWSER (ID: {packet_id}) missing payload.")

            elif packet_type == config.PACKET_TYPE_CAPTURE_MOUSE_POSITION:
                logger.info(f"Handling CAPTURE_MOUSE_POSITION (ID: {packet_id})")
                if payload_str:
                    try:
                        capture_payload = json.loads(payload_str)
                        purpose = capture_payload.get('purpose')
                        if purpose in ["SRC", "DES"]:
                            auto_drag_handler.capture_mouse_position(purpose)
                        else:
                            logger.error(f"Invalid 'purpose' ('{purpose}') in CAPTURE_MOUSE_POSITION payload.")
                    except Exception as e:
                        logger.error(f"Error processing CAPTURE_MOUSE_POSITION: {e}")
                else:
                    logger.warning(f"CAPTURE_MOUSE_POSITION (ID: {packet_id}) missing payload.")

            elif packet_type == config.PACKET_TYPE_AUTO_DRAG_LOOP_COMMAND:
                logger.info(f"Handling AUTO_DRAG_LOOP_COMMAND (ID: {packet_id})")
                if payload_str:
                    try:
                        loop_payload = json.loads(payload_str)
                        action = loop_payload.get('action')
                        if action == "START":
                            auto_drag_handler.start_auto_drag_loop()
                        elif action == "STOP":
                            auto_drag_handler.stop_auto_drag_loop()
                        else:
                            logger.error(f"Invalid 'action' ('{action}') in AUTO_DRAG_LOOP_COMMAND payload.")
                    except Exception as e:
                        logger.error(f"Error processing AUTO_DRAG_LOOP_COMMAND: {e}")
                else:
                    logger.warning(f"AUTO_DRAG_LOOP_COMMAND (ID: {packet_id}) missing payload.")
            else:
                logger.warning(f"Unknown packet type '{packet_type}'.")

        except socket.timeout:
            # This is expected due to settimeout(1.0)
            # Allows the loop to check stop_server_event.is_set()
            continue
        except UnicodeDecodeError:
            logger.error(f"Cannot decode UTF-8 from {addr if 'addr' in locals() else 'unknown sender'}.")
        except Exception as loop_e:
            logger.error(f"Error processing packet from {addr if 'addr' in locals() else 'unknown sender'}: {loop_e}")
        sys.stdout.flush() # Ensure logs are written

    # Loop finished (stop_server_event was set)
    logger.info("Server loop task stopping.")
    if server_socket:
        server_socket.close()
        logger.info("Server socket closed in loop task.")
    mdns_handler.unregister_mdns_service()
    logger.info("mDNS service unregistered in loop task.")
    if update_gui_status_callback:
        update_gui_status_callback("Server Stopped")


def start_server(port, mdns_enabled, gui_log_cb, gui_status_cb):
    """
    Starts the server in a new thread.
    Args:
        port (int): The port number for the server to listen on.
        mdns_enabled (bool): Whether to enable mDNS service registration.
        gui_log_cb (function): Callback to send log messages to the GUI.
        gui_status_cb (function): Callback to update server status in the GUI.
    """
    global server_thread, stop_server_event, executor
    global log_to_gui_callback, update_gui_status_callback

    log_to_gui_callback = gui_log_cb
    update_gui_status_callback = gui_status_cb

    if server_thread and server_thread.is_alive():
        logger.warning("Server is already running.")
        if log_to_gui_callback:
            log_to_gui_callback("WARN: Server is already running.")
        return False

    # Initialize ThreadPoolExecutor if not already (e.g. first start)
    if executor is None or executor._shutdown: # Check if it was shutdown previously
        executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='MacroWorker')
        logger.info(f"ThreadPoolExecutor initialized/re-initialized with max_workers={executor._max_workers}")


    stop_server_event.clear() # Clear the stop event before starting
    server_thread = threading.Thread(
        target=_server_loop_task,
        args=(port, mdns_enabled),
        name="ServerLoopThread",
        daemon=True # Daemon thread will exit when main program exits
    )
    server_thread.start()
    logger.info(f"Server thread started. Target port: {port}, mDNS: {mdns_enabled}")
    if log_to_gui_callback:
        log_to_gui_callback(f"INFO: Server thread starting. Port: {port}, mDNS: {mdns_enabled}")
    if update_gui_status_callback:
        update_gui_status_callback("Server Starting...")
    return True

def stop_server():
    """Stops the server thread and cleans up resources."""
    global server_thread, stop_server_event, server_socket, executor
    global log_to_gui_callback, update_gui_status_callback

    logger.info("Attempting to stop server...")
    if log_to_gui_callback:
        log_to_gui_callback("INFO: Attempting to stop server...")

    stop_server_event.set() # Signal the server loop to stop

    # Stop the auto_drag_handler's loop as well
    auto_drag_handler.stop_auto_drag_loop()

    if server_thread and server_thread.is_alive():
        logger.info("Waiting for server thread to join...")
        server_thread.join(timeout=3.0) # Wait for the thread to finish
        if server_thread.is_alive():
            logger.warning("Server thread did not join in time.")
            if log_to_gui_callback:
                log_to_gui_callback("WARN: Server thread did not join in time.")
        else:
            logger.info("Server thread joined successfully.")
            if log_to_gui_callback:
                log_to_gui_callback("INFO: Server thread stopped.")
    else:
        logger.info("Server thread was not running or already stopped.")
        if log_to_gui_callback:
            log_to_gui_callback("INFO: Server was not running.")


    # Socket is closed inside _server_loop_task, but as a fallback:
    if server_socket:
        try:
            server_socket.close()
            logger.info("Server socket closed by stop_server function.")
        except Exception as e:
            logger.error(f"Error closing server socket in stop_server: {e}")
    server_socket = None

    # mDNS is unregistered inside _server_loop_task, but as a fallback:
    mdns_handler.unregister_mdns_service() # Ensure mDNS is unregistered

    if executor and not executor._shutdown:
        logger.info("Shutting down ThreadPoolExecutor...")
        executor.shutdown(wait=True) # Wait for pending tasks
        logger.info("ThreadPoolExecutor shutdown complete.")
    executor = None # Allow re-initialization on next start

    if update_gui_status_callback:
        update_gui_status_callback("Server Stopped")
    logger.info("Server stop process complete.")

# The old main() function is removed as server_gui.py will be the entry point.
# If you need to run this script directly for testing without the GUI:
#
# def simple_log_callback(message):
#     print(f"GUI_LOG: {message}", file=sys.stderr)
#
# def simple_status_callback(status):
#     print(f"GUI_STATUS: {status}", file=sys.stderr)
#
# if __name__ == "__main__":
#     print("Starting server directly for testing (no GUI)...")
#     # Load settings to get port and mDNS status
#     import config_manager
#     settings = config_manager.load_settings()
#     test_port = settings.get("server_port", config.COMMAND_PORT)
#     test_mdns = settings.get("mdns_enabled", True)
#
#     start_server(test_port, test_mdns, simple_log_callback, simple_status_callback)
#
#     # Keep main thread alive, listen for Ctrl+C
#     try:
#         while True:
#             if not server_thread or not server_thread.is_alive():
#                 print("Server thread appears to have stopped. Exiting test.")
#                 break
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("\nCtrl+C received. Shutting down server...")
#     finally:
#         stop_server()
#         print("Test server shutdown complete.")

