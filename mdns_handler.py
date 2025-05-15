# mdns_handler.py
# Handles mDNS service registration/unregistration using Zeroconf.

import socket
import sys
# import ipaddress # Not strictly needed here anymore, but good practice
from zeroconf import ServiceInfo, Zeroconf, IPVersion
import config # Import constants from config.py
import logging

logger = logging.getLogger("StarButtonBoxMDNS") # Specific logger for this module

# --- Module-level variables for Zeroconf instance and service info ---
_zeroconf_instance = None
_service_info_instance = None

def get_local_ip():
    """Attempts to find a non-loopback local IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('8.8.8.8', 1)) # Doesn't send data
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != '127.0.0.1':
            return ip
    except Exception:
        pass 

    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and ip != '127.0.0.1':
            return ip
    except socket.gaierror:
        pass 

    logger.warning("Could not determine a non-loopback IP address. Using 127.0.0.1.")
    return "127.0.0.1"

def register_mdns_service():
    """Registers the StarButtonBox service using Zeroconf."""
    global _zeroconf_instance, _service_info_instance
    if _zeroconf_instance:
        logger.warning("mDNS service already registered or registration in progress.")
        return True 

    try:
        _zeroconf_instance = Zeroconf(ip_version=IPVersion.V4Only)
        local_ip = get_local_ip()

        host_name = socket.gethostname().split('.')[0] or "StarButtonBoxPC"
        service_name_str = f"{host_name} StarButtonBox Server.{config.MDNS_SERVICE_TYPE}"

        _service_info_instance = ServiceInfo(
            type_=config.MDNS_SERVICE_TYPE,
            name=service_name_str,
            addresses=[socket.inet_aton(local_ip)], 
            port=config.COMMAND_PORT,
            properties={}, 
            server=f"{host_name}.local.", 
        )
        logger.info(f"Registering mDNS service:")
        logger.info(f"  Name: {service_name_str}")
        logger.info(f"  Type: {config.MDNS_SERVICE_TYPE}")
        logger.info(f"  Address: {local_ip}")
        logger.info(f"  Port: {config.COMMAND_PORT}")
        
        _zeroconf_instance.register_service(_service_info_instance)
        logger.info("mDNS service registered successfully.")
        return True
    except Exception as e:
        logger.error(f"Error registering mDNS service: {e}")
        if _zeroconf_instance:
            try:
                _zeroconf_instance.close()
            except Exception as close_e:
                logger.error(f"Error closing Zeroconf instance during register_mdns_service error handling: {close_e}")
        _zeroconf_instance = None
        _service_info_instance = None
        return False

def unregister_mdns_service():
    """Unregisters the mDNS service and closes Zeroconf."""
    global _zeroconf_instance, _service_info_instance
    if _zeroconf_instance and _service_info_instance:
        logger.info("Unregistering mDNS service...")
        try:
            _zeroconf_instance.unregister_service(_service_info_instance)
        except Exception as e:
            logger.error(f"Error during mDNS service unregistration: {e}")
        
        try:
            _zeroconf_instance.close()
            logger.info("mDNS service unregistered and Zeroconf closed.")
        except Exception as e:
            logger.error(f"Error closing Zeroconf: {e}")

    elif _zeroconf_instance:
        logger.info("Closing Zeroconf (service likely not registered or already unregistered)...")
        try:
            _zeroconf_instance.close()
        except Exception as e:
            logger.error(f"Error closing Zeroconf (when service_info was None): {e}")

    _zeroconf_instance = None
    _service_info_instance = None

if __name__ == '__main__':
    # Setup basic console logging for testing this module directly
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger_test_main = logging.getLogger("MDNSHandlerTest")

    logger_test_main.info("--- Testing mDNS Handler ---")
    if register_mdns_service():
        logger_test_main.info("mDNS service registration initiated (check with mDNS browser).")
        logger_test_main.info("Press Ctrl+C to unregister and exit test.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger_test_main.info("\nKeyboard interrupt received.")
        finally:
            unregister_mdns_service()
            logger_test_main.info("mDNS test finished.")
    else:
        logger_test_main.error("Failed to register mDNS service during test.")

 