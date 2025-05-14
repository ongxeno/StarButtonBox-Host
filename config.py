# config.py
# Holds configuration constants for the StarButtonBox server.

# --- Network Configuration ---
COMMAND_PORT = 5005  # Port for receiving commands and health checks
BUFFER_SIZE = 2048 # UDP receive buffer size

# --- mDNS Configuration ---
MDNS_SERVICE_TYPE = "_starbuttonbox._udp.local."
# Service name includes hostname, making it unique on the network
# MDNS_SERVICE_NAME = "StarButtonBox Server._starbuttonbox._udp.local." # Constructed in mdns_handler

# --- Packet Types (mirroring Android's UdpPacketType) ---
PACKET_TYPE_HEALTH_CHECK_PING = "HEALTH_CHECK_PING"
PACKET_TYPE_HEALTH_CHECK_PONG = "HEALTH_CHECK_PONG"
PACKET_TYPE_MACRO_COMMAND = "MACRO_COMMAND"
PACKET_TYPE_MACRO_ACK = "MACRO_ACK"
PACKET_TYPE_TRIGGER_IMPORT_BROWSER = "TRIGGER_IMPORT_BROWSER"

# --- New Packet Types for Auto Drag and Drop ---
PACKET_TYPE_CAPTURE_MOUSE_POSITION = "CAPTURE_MOUSE_POSITION"
PACKET_TYPE_AUTO_DRAG_LOOP_COMMAND = "AUTO_DRAG_LOOP_COMMAND"
# Optional: PACKET_TYPE_AUTO_DRAG_STATUS_UPDATE = "AUTO_DRAG_STATUS_UPDATE" # For server to send status back
