# input_simulator.py
# Functions for simulating keyboard and mouse input using pydirectinput.
# Now includes the function to process macro commands in a thread
# and logs server-side processing latency.

import pydirectinput
import time
import sys
import json 

def _log_server_latency(event_type, packet_id, packet_decoded_time_ns, action_execution_start_time_ns):
    """Helper function to log the calculated server-side processing latency."""
    if packet_decoded_time_ns is None or action_execution_start_time_ns is None:
        print(f"    -> THREAD (ID: {packet_id}): Latency timing data incomplete for {event_type}.", file=sys.stderr)
        return
    
    processing_latency_ms = (action_execution_start_time_ns - packet_decoded_time_ns) / 1_000_000.0
    print(f"    -> THREAD (ID: {packet_id}): Server-side latency for {event_type} to action start: {processing_latency_ms:.3f} ms")
    sys.stdout.flush()

def execute_key_event(data, packet_decoded_time_ns, packet_id_for_log):
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

    # Press modifiers down (these are preparatory, not the primary action for latency timing)
    for mod_key in modifiers:
        try:
            pydirectinput.keyDown(mod_key)
        except Exception as mod_e:
            print(f"    -> Warning (input_simulator): Failed modifier down '{mod_key}': {mod_e}", file=sys.stderr)
            sys.stdout.flush()
    try:
        # Execute main key action
        action_execution_start_time_ns = time.perf_counter_ns()
        _log_server_latency(f"key_event ({press_type} '{key}')", packet_id_for_log, packet_decoded_time_ns, action_execution_start_time_ns)

        if press_type == 'tap':
            print(f"    -> Simulating key tap: '{key}' mods {modifiers}")
            sys.stdout.flush()
            pydirectinput.press(key)
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                print(f"    -> Warning (input_simulator): Invalid hold duration ({duration_ms}ms). Tapping.", file=sys.stderr)
                sys.stdout.flush()
                pydirectinput.press(key) # Fallback to tap
            else:
                print(f"    -> Simulating key hold: '{key}' for {duration_sec:.2f}s mods {modifiers}")
                sys.stdout.flush()
                pydirectinput.keyDown(key)
                time.sleep(duration_sec)
                pydirectinput.keyUp(key)
        else:
            print(f"    -> Warning (input_simulator): Invalid pressType/duration for key. Tapping.", file=sys.stderr)
            sys.stdout.flush()
            pydirectinput.press(key) # Fallback to tap
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

def execute_mouse_event(data, packet_decoded_time_ns, packet_id_for_log):
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
        action_execution_start_time_ns = time.perf_counter_ns()
        _log_server_latency(f"mouse_event ({press_type} '{button}')", packet_id_for_log, packet_decoded_time_ns, action_execution_start_time_ns)
        
        if press_type == 'tap':
            print(f"    -> Simulating mouse click: '{button}' mods {modifiers}")
            sys.stdout.flush()
            pydirectinput.click(button=button)
        elif press_type == 'hold' and duration_ms is not None:
            duration_sec = duration_ms / 1000.0
            if duration_sec <= 0:
                 print(f"    -> Warning (input_simulator): Invalid hold duration ({duration_ms}ms). Clicking.", file=sys.stderr)
                 sys.stdout.flush()
                 pydirectinput.click(button=button) # Fallback to click
            else:
                print(f"    -> Simulating mouse hold: '{button}' for {duration_sec:.2f}s mods {modifiers}")
                sys.stdout.flush()
                pydirectinput.mouseDown(button=button)
                time.sleep(duration_sec)
                pydirectinput.mouseUp(button=button)
        else:
             print(f"    -> Warning (input_simulator): Invalid pressType/duration for mouse. Clicking.", file=sys.stderr)
             sys.stdout.flush()
             pydirectinput.click(button=button) # Fallback to click
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

def execute_mouse_scroll(data, packet_decoded_time_ns, packet_id_for_log):
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
        action_execution_start_time_ns = time.perf_counter_ns()
        _log_server_latency(f"mouse_scroll (dir '{direction}')", packet_id_for_log, packet_decoded_time_ns, action_execution_start_time_ns)

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

def process_macro_in_thread(action_data_str, packet_id_for_log, packet_decoded_time_ns):
    """
    Processes and executes the macro command in a separate thread.
    Receives the initial packet_decoded_time_ns from the main server thread.
    """
    try:
        action_data = json.loads(action_data_str) 
        action_subtype = action_data.get('type')
        # Log when thread starts processing, not the latency yet
        print(f"    THREAD (ID: {packet_id_for_log}): Starting processing of {action_subtype}")
        sys.stdout.flush()

        if action_subtype == 'key_event':
            execute_key_event(action_data, packet_decoded_time_ns, packet_id_for_log)
        elif action_subtype == 'mouse_event':
            execute_mouse_event(action_data, packet_decoded_time_ns, packet_id_for_log)
        elif action_subtype == 'mouse_scroll':
            execute_mouse_scroll(action_data, packet_decoded_time_ns, packet_id_for_log)
        else:
            print(f"    THREAD (ID: {packet_id_for_log}): Warning: Unknown action subtype '{action_subtype}'...", file=sys.stderr)
        
        print(f"    THREAD (ID: {packet_id_for_log}): Finished processing of {action_subtype}")
        sys.stdout.flush()

    except json.JSONDecodeError as e:
        print(f"    THREAD (ID: {packet_id_for_log}): Error decoding action_data in thread: {e}", file=sys.stderr)
    except Exception as e:
        print(f"    THREAD (ID: {packet_id_for_log}): Error during input simulation in thread: {e}", file=sys.stderr)
    sys.stdout.flush()
