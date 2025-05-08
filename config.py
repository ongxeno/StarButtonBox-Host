# config.py
# Holds configuration constants for the StarButtonBox server.

import sys

# --- Network Configuration ---
COMMAND_PORT = 5005  # Port for receiving commands and health checks
BUFFER_SIZE = 2048 # UDP receive buffer size

# --- mDNS Configuration ---
MDNS_SERVICE_TYPE = "_starbuttonbox._udp.local."
# Service name includes hostname, making it unique on the network
# MDNS_SERVICE_NAME = "StarButtonBox Server._starbuttonbox._udp.local." # This will be constructed dynamically in mdns_handler

# --- Packet Types (mirroring Android's UdpPacketType) ---
PACKET_TYPE_HEALTH_CHECK_PING = "HEALTH_CHECK_PING"
PACKET_TYPE_HEALTH_CHECK_PONG = "HEALTH_CHECK_PONG"
PACKET_TYPE_MACRO_COMMAND = "MACRO_COMMAND"
PACKET_TYPE_MACRO_ACK = "MACRO_ACK"
PACKET_TYPE_TRIGGER_IMPORT_BROWSER = "TRIGGER_IMPORT_BROWSER"

# --- Tkinter Availability Check ---
# Check if Tkinter is available when this module is imported
try:
    import tkinter as tk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    print("Warning (config.py): Tkinter library not found. Install it for graphical prompts.", file=sys.stderr)
    sys.stdout.flush()

