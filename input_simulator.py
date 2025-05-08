# input_simulator.py
# Functions for simulating keyboard and mouse input using pydirectinput.

import pydirectinput
import time
import sys

def execute_key_event(data):
    """Handles 'key_event' actions from the parsed JSON data."""
    key = data.get('key')
    modifiers = data.get('modifiers', [])
    press_type_data = data.get('pressType', {})
    press_type = press_type_data.get('type', 'tap')
    duration_ms = press_type_data.get('durationMs')

    if not key:
        print("    -> Error (input_simulator): 'key' field missing.", file=sys.stderr)
        sys.stdout.flush()
        return

    # Press modifiers down
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
        except Exception as mod_e:
            print(f"    -> Warning (input_simulator): Failed modifier down '{mod_key}': {mod_e}", file=sys.stderr)
            sys.stdout.flush()
    try:
        # Execute main key action
        if press_type == 'tap':
            print(f"    -> Simulating key tap: '{key}' mods {modifiers}")
            sys.stdout.flush()
            pydirectinput.press(key)
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                print(f"    -> Warning (input_simulator): Invalid hold duration ({duration_ms}ms). Tapping.", file=sys.stderr)
                sys.stdout.flush()
                pydirectinput.press(key)
            else:
                print(f"    -> Simulating key hold: '{key}' for {duration_sec:.2f}s mods {modifiers}")
                sys.stdout.flush()
                pydirectinput.keyDown(key)
                time.sleep(duration_sec)
                pydirectinput.keyUp(key)
        else:
            print(f"    -> Warning (input_simulator): Invalid pressType/duration. Tapping.", file=sys.stderr)
            sys.stdout.flush()
            pydirectinput.press(key)
    except Exception as action_e:
        print(f"    -> Error (input_simulator): executing key action '{key}': {action_e}", file=sys.stderr)
        sys.stdout.flush()
    finally:
        # Release modifiers in reverse order
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
            except Exception as mod_e:
                print(f"    -> Warning (input_simulator): Failed modifier up '{mod_key}': {mod_e}", file=sys.stderr)
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
        print(f"    -> Error (input_simulator): Invalid mouse button '{button_str}'", file=sys.stderr)
        sys.stdout.flush()
        return

    # Press modifiers down
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
        except Exception as mod_e:
            print(f"    -> Warning (input_simulator): Failed modifier down '{mod_key}': {mod_e}", file=sys.stderr)
            sys.stdout.flush()
    try:
        # Execute main mouse action
        if press_type == 'tap':
            print(f"    -> Simulating mouse click: '{button}' mods {modifiers}")
            sys.stdout.flush()
            pydirectinput.click(button=button)
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                 print(f"    -> Warning (input_simulator): Invalid hold duration ({duration_ms}ms). Clicking.", file=sys.stderr)
                 sys.stdout.flush()
                 pydirectinput.click(button=button)
            else:
                print(f"    -> Simulating mouse hold: '{button}' for {duration_sec:.2f}s mods {modifiers}")
                sys.stdout.flush()
                pydirectinput.mouseDown(button=button)
                time.sleep(duration_sec)
                pydirectinput.mouseUp(button=button)
        else:
             print(f"    -> Warning (input_simulator): Invalid pressType/duration. Clicking.", file=sys.stderr)
             sys.stdout.flush()
             pydirectinput.click(button=button)
    except Exception as mouse_e:
        print(f"    -> Error (input_simulator): executing mouse action '{button}': {mouse_e}", file=sys.stderr)
        sys.stdout.flush()
    finally:
        # Release modifiers in reverse order
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
            except Exception as mod_e:
                print(f"    -> Warning (input_simulator): Failed modifier up '{mod_key}': {mod_e}", file=sys.stderr)
                sys.stdout.flush()

def execute_mouse_scroll(data):
    """Handles 'mouse_scroll' actions from the parsed JSON data."""
    direction = data.get('direction')
    clicks = data.get('clicks', 1)
    modifiers = data.get('modifiers', [])
    scroll_amount = clicks if direction == "UP" else -clicks if direction == "DOWN" else 0

    if scroll_amount == 0:
        print(f"    -> Error (input_simulator): Invalid scroll direction '{direction}'", file=sys.stderr)
        sys.stdout.flush()
        return

    # Press modifiers down
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
        except Exception as mod_e:
            print(f"    -> Warning (input_simulator): Failed modifier down '{mod_key}': {mod_e}", file=sys.stderr)
            sys.stdout.flush()
    try:
        # Execute scroll action
        print(f"    -> Simulating mouse scroll: dir '{direction}', clicks {clicks} mods {modifiers}")
        sys.stdout.flush()
        pydirectinput.scroll(scroll_amount)
    except Exception as scroll_e:
        print(f"    -> Error (input_simulator): executing mouse scroll: {scroll_e}", file=sys.stderr)
        sys.stdout.flush()
    finally:
        # Release modifiers in reverse order
        for mod_key in reversed(modifiers):
            try:
                pydirectinput.keyUp(mod_key)
            except Exception as mod_e:
                print(f"    -> Warning (input_simulator): Failed modifier up '{mod_key}': {mod_e}", file=sys.stderr)
                sys.stdout.flush()

