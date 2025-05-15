# auto_drag_handler.py
# Handles capturing mouse positions and managing the auto drag-and-drop loop.

import pyautogui
import time
import threading
import sys
import logging # Use logging instead of print for better control

logger = logging.getLogger("StarButtonBoxAutoDrag") # Specific logger

# --- Global variables to store state ---
captured_src_position = None
captured_dest_position = None
stop_drag_loop_event = threading.Event()  # Event to signal the loop to stop
auto_drag_thread = None  # To hold the reference to the drag loop thread

# --- Configuration for drag operation (can be adjusted) ---
DRAG_DURATION_SECONDS = 0.1  # Duration of the mouse movement during drag
POST_DRAG_SLEEP_SECONDS = 0.05 # Sleep after each drag action
LOOP_WAIT_SECONDS = 0.1 # Sleep between drag iterations in the loop

def capture_mouse_position(purpose: str):
    """
    Captures the current mouse position and stores it based on the purpose.
    Args:
        purpose (str): "SRC" to store as source, "DES" to store as destination.
    """
    global captured_src_position, captured_dest_position
    try:
        current_pos = pyautogui.position()
        if purpose == "SRC":
            captured_src_position = current_pos
            logger.info(f"Source position captured: {captured_src_position}")
        elif purpose == "DES":
            captured_dest_position = current_pos
            logger.info(f"Destination position captured: {captured_dest_position}")
        else:
            logger.error(f"Invalid purpose '{purpose}' for capture_mouse_position.")
    except Exception as e:
        logger.error(f"Failed to capture mouse position: {e}")
    # No sys.stdout.flush() needed if using logger properly configured at app level

def _perform_single_drag(src_pos, dest_pos):
    """
    Private helper function to perform a single drag-and-drop operation.
    Args:
        src_pos (tuple): The (x, y) coordinates for the start of the drag.
        dest_pos (tuple): The (x, y) coordinates for the end of the drag.
    """
    try:
        logger.debug(f"Dragging from {src_pos} to {dest_pos}...") # Changed to debug for less noise
        pyautogui.moveTo(src_pos[0], src_pos[1])
        pyautogui.mouseDown(button='left')
        time.sleep(0.05) 
        pyautogui.moveTo(dest_pos[0], dest_pos[1], duration=DRAG_DURATION_SECONDS)
        time.sleep(POST_DRAG_SLEEP_SECONDS) 
        pyautogui.mouseUp(button='left')
        logger.debug(f"Drag complete.") # Changed to debug
    except Exception as e:
        logger.error(f"Exception during drag: {e}")

def _auto_drag_loop_task():
    """
    Private helper task that runs in a separate thread to perform the drag-and-drop loop.
    The loop continues until stop_drag_loop_event is set.
    """
    global captured_src_position, captured_dest_position, stop_drag_loop_event
    logger.info("Auto drag loop task started.")

    while not stop_drag_loop_event.is_set():
        if captured_src_position is None or captured_dest_position is None:
            logger.warning("Source or Destination position not set. Auto drag loop waiting...")
            time.sleep(1)
            continue

        _perform_single_drag(captured_src_position, captured_dest_position)
        
        if stop_drag_loop_event.is_set():
            break
        
        time.sleep(LOOP_WAIT_SECONDS)

    logger.info("Auto drag loop task finished.")

def start_auto_drag_loop():
    """
    Starts the automated drag-and-drop loop in a new thread.
    If a loop is already running, it will be stopped first.
    """
    global auto_drag_thread, stop_drag_loop_event, captured_src_position, captured_dest_position

    if captured_src_position is None or captured_dest_position is None:
        logger.error("Cannot start auto drag loop. Source and/or Destination position not set.")
        return

    if auto_drag_thread and auto_drag_thread.is_alive():
        logger.info("Existing auto drag loop found. Stopping it before starting a new one.")
        stop_auto_drag_loop() 

    stop_drag_loop_event.clear()
    auto_drag_thread = threading.Thread(target=_auto_drag_loop_task, daemon=True, name="AutoDragLoopThread")
    auto_drag_thread.start()
    logger.info("Auto drag loop initiated.")

def stop_auto_drag_loop():
    """
    Signals the auto drag-and-drop loop to stop and waits for the thread to finish.
    """
    global auto_drag_thread, stop_drag_loop_event
    if auto_drag_thread and auto_drag_thread.is_alive():
        logger.info("Sending stop signal to auto drag loop...")
        stop_drag_loop_event.set()
        auto_drag_thread.join(timeout=2.0) 
        if auto_drag_thread.is_alive():
            logger.warning("Auto drag loop thread did not terminate in time.")
        else:
            logger.info("Auto drag loop thread terminated.")
        auto_drag_thread = None
    else:
        logger.info("No active auto drag loop to stop.")
    # Removed sys.stdout.flush() as logger should handle flushing if configured

if __name__ == '__main__':
    # Setup basic console logging for testing this module directly
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, # Changed to INFO for less noise
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger_main_test = logging.getLogger("AutoDragTestMain")

    logger_main_test.info("Testing auto_drag_handler.py...")
    logger_main_test.info("Move mouse to SOURCE position and press Enter...")
    input()
    capture_mouse_position("SRC")
    
    logger_main_test.info("Move mouse to DESTINATION position and press Enter...")
    input()
    capture_mouse_position("DES")

    if captured_src_position and captured_dest_position:
        logger_main_test.info("Starting auto drag loop in 3 seconds. Press Ctrl+C to stop this test script.")
        time.sleep(3)
        start_auto_drag_loop()
        try:
            while True: 
                if auto_drag_thread and not auto_drag_thread.is_alive():
                    logger_main_test.info("Test: Drag loop thread seems to have finished.")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            logger_main_test.info("\nTest script interrupted. Stopping drag loop...")
            stop_auto_drag_loop()
            logger_main_test.info("Test finished.")
    else:
        logger_main_test.error("Failed to set SRC or DES positions. Test aborted.")

