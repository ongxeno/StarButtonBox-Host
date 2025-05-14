import time
import pyautogui  # Changed from pydirectinput
import keyboard    # Add this import for keypress detection

# Set mode: "report" or "execute"
mode = "execute"  # Change to "execute" to perform drag and drop

# Hardcoded positions for execute mode (example values, change as needed)
SRC = (2800, 480)  # (x1, y1)
DES = (2800, 1800)  # (x2, y2)

# Number of times to perform drag and drop in execute mode
NUM_DRAGS = 200  # Change this value as needed

def report_mouse_position():
    """Reports the current mouse position until Ctrl+C is pressed."""
    print("Move your mouse. Press Ctrl+C to stop.")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"Mouse position: ({x}, {y})", end="\r")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopped reporting mouse position.")

def execute_drag_and_drop(src_pos, dest_pos, times):
    """
    Performs a drag and drop operation from src_pos to dest_pos multiple times
    using pyautogui. Stops if left Ctrl key is pressed.
    """
    for i in range(times):
        print(f"Dragging from {src_pos} to {dest_pos} using pyautogui... (#{i+1})")
        pyautogui.moveTo(src_pos[0], src_pos[1])
        pyautogui.mouseDown(button='left')
        pyautogui.moveTo(dest_pos[0], dest_pos[1], duration=0.1)
        time.sleep(0.1)
        pyautogui.mouseUp(button='left')
        print(f"Drag and drop #{i+1} complete.")
        time.sleep(0.05)
        # Stop if left Ctrl is pressed
        if keyboard.is_pressed('left ctrl'):
            print("Left Ctrl detected. Stopping drag and drop loop.")
            break

if __name__ == "__main__":
    pyautogui.FAILSAFE = True

    if mode == "report":
        report_mouse_position()
    elif mode == "execute":
        delay_seconds = 3  # Set your desired delay before starting
        print(f"Waiting {delay_seconds} seconds before starting drag and drop...")
        print("Please ensure the target window is active/focused.")
        print("To stop the script in an emergency, move the mouse to any corner of the screen.")
        print("Or press any key to stop after the next drag.")
        time.sleep(delay_seconds)
        execute_drag_and_drop(SRC, DES, NUM_DRAGS)
        print("All drag and drop operations finished.")
    else:
        print("Invalid mode. Set mode to 'report' or 'execute'.")

