# auto_drag_handler.py
# Handles capturing mouse positions and managing the auto drag-and-drop loop.

import pyautogui
import time
import threading
import sys

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
            print(f"  SERVER: Source position captured: {captured_src_position}", file=sys.stderr)
        elif purpose == "DES":
            captured_dest_position = current_pos
            print(f"  SERVER: Destination position captured: {captured_dest_position}", file=sys.stderr)
        else:
            print(f"  SERVER ERROR: Invalid purpose '{purpose}' for capture_mouse_position.", file=sys.stderr)
    except Exception as e:
        print(f"  SERVER ERROR: Failed to capture mouse position: {e}", file=sys.stderr)
    sys.stdout.flush()

def _perform_single_drag(src_pos, dest_pos):
    """
    Private helper function to perform a single drag-and-drop operation.
    Args:
        src_pos (tuple): The (x, y) coordinates for the start of the drag.
        dest_pos (tuple): The (x, y) coordinates for the end of the drag.
    """
    try:
        print(f"    DRAG_LOOP: Dragging from {src_pos} to {dest_pos}...", file=sys.stderr)
        pyautogui.moveTo(src_pos[0], src_pos[1])
        pyautogui.mouseDown(button='left')
        # Add a small delay after mouseDown before moving, can help some applications register the click
        time.sleep(0.05) 
        pyautogui.moveTo(dest_pos[0], dest_pos[1], duration=DRAG_DURATION_SECONDS)
        time.sleep(POST_DRAG_SLEEP_SECONDS) # Ensure movement is complete
        pyautogui.mouseUp(button='left')
        print(f"    DRAG_LOOP: Drag complete.", file=sys.stderr)
    except Exception as e:
        print(f"    DRAG_LOOP ERROR: Exception during drag: {e}", file=sys.stderr)
    sys.stdout.flush()

def _auto_drag_loop_task():
    """
    Private helper task that runs in a separate thread to perform the drag-and-drop loop.
    The loop continues until stop_drag_loop_event is set.
    """
    global captured_src_position, captured_dest_position, stop_drag_loop_event
    print("  DRAG_LOOP_THREAD: Auto drag loop task started.", file=sys.stderr)
    sys.stdout.flush()

    while not stop_drag_loop_event.is_set():
        if captured_src_position is None or captured_dest_position is None:
            print("  DRAG_LOOP_THREAD: Source or Destination position not set. Waiting...", file=sys.stderr)
            sys.stdout.flush()
            time.sleep(1)  # Wait for positions to be set
            continue

        _perform_single_drag(captured_src_position, captured_dest_position)
        
        # Check the event immediately after a drag, and before sleeping for the next iteration
        if stop_drag_loop_event.is_set():
            break
        
        time.sleep(LOOP_WAIT_SECONDS) # Wait before the next drag iteration

    print("  DRAG_LOOP_THREAD: Auto drag loop task finished.", file=sys.stderr)
    sys.stdout.flush()

def start_auto_drag_loop():
    """
    Starts the automated drag-and-drop loop in a new thread.
    If a loop is already running, it will be stopped first.
    """
    global auto_drag_thread, stop_drag_loop_event, captured_src_position, captured_dest_position

    if captured_src_position is None or captured_dest_position is None:
        print("  SERVER: Cannot start auto drag loop. Source and/or Destination position not set.", file=sys.stderr)
        sys.stdout.flush()
        return

    if auto_drag_thread and auto_drag_thread.is_alive():
        print("  SERVER: Existing auto drag loop found. Stopping it before starting a new one.", file=sys.stderr)
        sys.stdout.flush()
        stop_auto_drag_loop() # This will set the event and join the thread

    stop_drag_loop_event.clear()  # Clear the event flag for the new loop
    auto_drag_thread = threading.Thread(target=_auto_drag_loop_task, daemon=True, name="AutoDragLoopThread")
    auto_drag_thread.start()
    print("  SERVER: Auto drag loop initiated.", file=sys.stderr)
    sys.stdout.flush()

def stop_auto_drag_loop():
    """
    Signals the auto drag-and-drop loop to stop and waits for the thread to finish.
    """
    global auto_drag_thread, stop_drag_loop_event
    if auto_drag_thread and auto_drag_thread.is_alive():
        print("  SERVER: Sending stop signal to auto drag loop...", file=sys.stderr)
        sys.stdout.flush()
        stop_drag_loop_event.set()
        auto_drag_thread.join(timeout=2.0) # Wait for the thread to finish, with a timeout
        if auto_drag_thread.is_alive():
            print("  SERVER WARNING: Auto drag loop thread did not terminate in time.", file=sys.stderr)
        else:
            print("  SERVER: Auto drag loop thread terminated.", file=sys.stderr)
        auto_drag_thread = None
    else:
        print("  SERVER: No active auto drag loop to stop.", file=sys.stderr)
    sys.stdout.flush()

if __name__ == '__main__':
    # Example usage for testing this module directly
    print("Testing auto_drag_handler.py...")
    print("Move mouse to SOURCE position and press Enter...")
    input()
    capture_mouse_position("SRC")
    
    print("Move mouse to DESTINATION position and press Enter...")
    input()
    capture_mouse_position("DES")

    if captured_src_position and captured_dest_position:
        print("Starting auto drag loop in 3 seconds. Press Ctrl+C to stop this test script.")
        time.sleep(3)
        start_auto_drag_loop()
        try:
            while True: # Keep main thread alive for daemon thread to run
                if auto_drag_thread and not auto_drag_thread.is_alive():
                    print("Test: Drag loop thread seems to have finished.")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nTest script interrupted. Stopping drag loop...")
            stop_auto_drag_loop()
            print("Test finished.")
    else:
        print("Failed to set SRC or DES positions. Test aborted.")

