# mdns_handler.py
# Handles mDNS service registration/unregistration using Zeroconf.

import socket
import sys
import ipaddress # Not strictly needed here anymore, but good practice
from zeroconf import ServiceInfo, Zeroconf, IPVersion
import config # Import constants from config.py

# --- Module-level variables for Zeroconf instance and service info ---
# This keeps the state within this module.
_zeroconf_instance = None
_service_info_instance = None

def get_local_ip():
    """Attempts to find a non-loopback local IPv4 address."""
    # Try connecting to an external host (doesn't send data)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        # Use a known public DNS server
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != '127.0.0.1':
            return ip
    except Exception:
        pass # Ignore errors and try the next method

    # Fallback to gethostbyname
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and ip != '127.0.0.1':
            return ip
    except socket.gaierror:
        pass # Ignore errors if hostname resolution fails

    # Last resort fallback
    print("Warning (mdns_handler): Could not determine a non-loopback IP address. Using 127.0.0.1.", file=sys.stderr)
    sys.stdout.flush()
    return "127.0.0.1"

def register_mdns_service():
    """Registers the StarButtonBox service using Zeroconf."""
    global _zeroconf_instance, _service_info_instance
    if _zeroconf_instance:
        print("Warning (mdns_handler): mDNS service already registered or registration in progress.", file=sys.stderr)
        sys.stdout.flush()
        return True # Indicate it might already be okay

    try:
        _zeroconf_instance = Zeroconf(ip_version=IPVersion.V4Only)
        local_ip = get_local_ip()

        host_name = socket.gethostname().split('.')[0] or "StarButtonBoxPC" # Fallback hostname
        # Construct dynamic service name
        service_name_str = f"{host_name} StarButtonBox Server.{config.MDNS_SERVICE_TYPE}"

        _service_info_instance = ServiceInfo(
            type_=config.MDNS_SERVICE_TYPE,
            name=service_name_str,
            addresses=[socket.inet_aton(local_ip)], # Requires bytes
            port=config.COMMAND_PORT,
            properties={}, # No specific properties needed for now
            server=f"{host_name}.local.", # Standard mDNS server naming
        )
        print(f"Registering mDNS service:")
        print(f"  Name: {service_name_str}")
        print(f"  Type: {config.MDNS_SERVICE_TYPE}")
        print(f"  Address: {local_ip}")
        print(f"  Port: {config.COMMAND_PORT}")
        sys.stdout.flush()
        _zeroconf_instance.register_service(_service_info_instance)
        print("mDNS service registered successfully.")
        sys.stdout.flush()
        return True
    except Exception as e:
        print(f"Error registering mDNS service: {e}", file=sys.stderr)
        sys.stdout.flush()
        if _zeroconf_instance:
            _zeroconf_instance.close()
        _zeroconf_instance = None
        _service_info_instance = None
        return False

def unregister_mdns_service():
    """Unregisters the mDNS service and closes Zeroconf."""
    global _zeroconf_instance, _service_info_instance
    if _zeroconf_instance and _service_info_instance:
        print("\nUnregistering mDNS service...")
        sys.stdout.flush()
        try:
            _zeroconf_instance.unregister_service(_service_info_instance)
            # Close should happen after unregistering
        except Exception as e:
            print(f"Error during mDNS service unregistration: {e}", file=sys.stderr)
            sys.stdout.flush()
        # Always try to close zeroconf if it exists
        try:
            _zeroconf_instance.close()
            print("mDNS service unregistered and Zeroconf closed.")
            sys.stdout.flush()
        except Exception as e:
            print(f"Error closing Zeroconf: {e}", file=sys.stderr)
            sys.stdout.flush()

    elif _zeroconf_instance:
        # If service_info was somehow None but zeroconf exists
        print("\nClosing Zeroconf (service likely not registered)...")
        sys.stdout.flush()
        try:
            _zeroconf_instance.close()
        except Exception as e:
            print(f"Error closing Zeroconf: {e}", file=sys.stderr)
            sys.stdout.flush()

    # Reset module variables
    _zeroconf_instance = None
    _service_info_instance = None

