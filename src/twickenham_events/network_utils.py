"""
Network utilities for dynamic URL building.

This module provides utilities for detecting local network addresses,
particularly useful for Docker deployments and dynamic external URL generation.
"""

import logging
import os
import socket
from typing import Optional

logger = logging.getLogger(__name__)


def get_local_ipv4() -> Optional[str]:
    """
    Get the local IPv4 address of this machine.

    This function attempts to determine the machine's primary IPv4 address
    by connecting to a remote endpoint and inspecting the local socket.
    Works in Docker containers to get the container's IP or host IP.

    Returns:
        str: The local IPv4 address, or None if detection fails
    """
    try:
        # Create a socket and connect to a remote address to determine local IP
        # Use Google's DNS server as a reliable endpoint
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to Google DNS (8.8.8.8:80)
            # This doesn't actually send data, just determines routing
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            logger.debug("Detected local IPv4 address: %s", local_ip)
            return local_ip
    except Exception as e:
        logger.debug("Failed to detect local IPv4 address: %s", e)
        return None


def get_docker_host_ip() -> Optional[str]:
    """
    Get the Docker host IP address when running inside a container.

    This function attempts various methods to determine the Docker host IP:
    1. Extract IP from WEB_SERVER_EXTERNAL_URL environment variable (most reliable)
    2. Check for host.docker.internal (Docker Desktop)
    3. Auto-detect by probing common private network ranges
    4. Check the default gateway (Docker bridge) as fallback

    Returns:
        str: The Docker host IP address, or None if detection fails

    Note:
        For reliable Docker deployment, set WEB_SERVER_EXTERNAL_URL environment variable
        to your complete external URL (e.g., http://10.10.10.20:47476).
    """
    # Method 1: Extract IP from external URL environment variable (most reliable)
    external_url = os.getenv("WEB_SERVER_EXTERNAL_URL")
    if external_url:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(external_url)
            if parsed.hostname:
                logger.debug(
                    "Using host IP from WEB_SERVER_EXTERNAL_URL: %s", parsed.hostname
                )
                return parsed.hostname
        except Exception as e:
            logger.debug(
                "Failed to parse WEB_SERVER_EXTERNAL_URL %s: %s", external_url, e
            )

    # Legacy: Check DOCKER_HOST_IP environment variable (deprecated but still supported)
    env_host_ip = os.getenv("DOCKER_HOST_IP")
    if env_host_ip:
        logger.debug("Found Docker host IP from environment: %s", env_host_ip)
        return env_host_ip

    # Method 2: Try host.docker.internal (Docker Desktop)
    try:
        host_ip = socket.gethostbyname("host.docker.internal")
        logger.debug("Found Docker host via host.docker.internal: %s", host_ip)
        return host_ip
    except socket.gaierror:
        pass

    # Method 3: Auto-detect by probing private network ranges
    logger.debug("Attempting auto-detection of Docker host IP...")
    detected_ip = _probe_for_host_ip()
    if detected_ip:
        logger.debug("Auto-detected Docker host IP: %s", detected_ip)
        return detected_ip

    # Method 4: Fallback to Docker bridge gateway
    try:
        with open("/proc/net/route") as f:
            for line in f:
                fields = line.strip().split()
                if fields[1] == "00000000":  # Default route
                    gateway_hex = fields[2]
                    gateway_ip = socket.inet_ntoa(
                        bytes.fromhex(gateway_hex)[::-1]  # Reverse byte order
                    )
                    logger.debug(
                        "Using Docker gateway IP %s (may not be host's LAN IP)",
                        gateway_ip,
                    )
                    return gateway_ip
    except (FileNotFoundError, ValueError, OSError) as e:
        logger.debug("Failed to read Docker gateway from /proc/net/route: %s", e)

    logger.debug("Could not detect Docker host IP via any method")
    return None


def _probe_for_host_ip() -> Optional[str]:
    """
    Probe common private network ranges to auto-detect the Docker host IP.

    This function quickly scans private network ranges to find reachable IPs
    that might be the Docker host machine.

    Returns:
        str: Most likely host IP, or None if none found
    """
    import threading

    # Common private network ranges that might contain the host
    network_ranges = [
        "10.10.10",  # Common enterprise/lab networks
        "192.168.1",  # Common home network
        "192.168.0",  # Alternative home network
        "10.0.0",  # Docker Desktop / enterprise
        "172.16.0",  # Docker custom networks
    ]

    def _probe_ip_range(base_ip: str, start: int, end: int, reachable_ips: list):
        """Probe a range of IPs to see which ones are reachable."""
        for i in range(start, end):
            ip = f"{base_ip}.{i}"
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)  # Quick timeout for speed
                result = sock.connect_ex((ip, 22))  # Try SSH port (commonly open)
                sock.close()
                if result == 0:
                    reachable_ips.append(ip)
            except Exception:
                pass

    all_reachable = []

    # Quick scan of each network range
    for network in network_ranges:
        reachable_in_range = []
        threads = []

        # Scan key IP ranges (avoid scanning all 254 IPs for speed)
        # Focus on common host IP ranges
        scan_ranges = [(2, 50), (100, 150), (200, 254)]

        for start, end in scan_ranges:
            thread = threading.Thread(
                target=_probe_ip_range,
                args=(network, start, min(end, 255), reachable_in_range),
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)

        # Wait for threads with short timeout (speed vs accuracy tradeoff)
        for thread in threads:
            thread.join(timeout=1.0)

        all_reachable.extend(reachable_in_range)

        # If we found IPs in this range, prefer it (first match wins)
        if reachable_in_range:
            logger.debug("Found reachable IPs in %s.x: %s", network, reachable_in_range)
            break

    if not all_reachable:
        logger.debug("No reachable host IPs found via network probing")
        return None

    # Filter out likely router/gateway IPs and pick the best candidate
    likely_hosts = []
    for ip in all_reachable:
        parts = ip.split(".")
        last_octet = int(parts[3])

        # Skip common router/gateway IPs
        if last_octet not in [1, 254, 255]:
            likely_hosts.append(ip)

    if likely_hosts:
        # Return the first likely host IP found
        best_host = likely_hosts[0]
        logger.debug("Selected host IP from candidates %s: %s", likely_hosts, best_host)
        return best_host
    elif all_reachable:
        # If no non-gateway IPs found, use the first reachable IP
        fallback_host = all_reachable[0]
        logger.debug("Using fallback host IP: %s", fallback_host)
        return fallback_host

    return None


def build_smart_external_url(
    host: str,
    port: int,
    protocol: str = "http",
    external_url_base: Optional[str] = None,
) -> str:
    """
    Build a smart external URL that works in both Docker and non-Docker environments.

    This function intelligently determines the best IP address to use:
    1. If external_url_base is provided, use it directly
    2. If running in Docker, try to get the host's IP via various methods
    3. Filter out Docker bridge IPs (172.17.x.x) for non-Docker environments
    4. Fall back to localhost as last resort

    For Docker deployments, consider setting DOCKER_HOST_IP environment variable
    or using host networking (--network host) for best results.

    Args:
        host: The base hostname/IP (may be overridden by smart detection)
        port: The port number
        protocol: The protocol (http/https)
        external_url_base: Optional explicit base URL to use instead of auto-detection

    Returns:
        str: A complete URL suitable for external access
    """
    # If explicit external URL base is provided, use it
    if external_url_base:
        # Remove trailing slash
        base = external_url_base.rstrip("/")

        # If the external URL base includes a protocol, use it as-is
        # This assumes the external URL is complete (e.g., behind a reverse proxy)
        if "://" in base:
            return base
        else:
            # No protocol specified, add both protocol and port
            return f"{protocol}://{base}:{port}"

    # Determine the best host to use
    best_host = host

    # Special case: if someone explicitly specified localhost, respect it
    if host == "localhost":
        return f"{protocol}://localhost:{port}"

    # Check if we're running in Docker
    if is_running_in_docker():
        logger.debug("Detected Docker environment, attempting to get host IP")
        docker_host_ip = get_docker_host_ip()
        if docker_host_ip:
            logger.debug("Using Docker host IP: %s", docker_host_ip)
            best_host = docker_host_ip
        else:
            logger.warning(
                "Could not detect Docker host IP. Consider setting DOCKER_HOST_IP "
                "environment variable or using --network host for Docker deployment"
            )
    else:
        # Not in Docker - try to get a good local IP, but filter Docker bridge IPs
        local_ip = get_local_ipv4()
        if local_ip and not local_ip.startswith("172.17."):
            # Only use local IP if it's not a Docker bridge IP
            best_host = local_ip
        elif local_ip and local_ip.startswith("172.17."):
            logger.debug(
                "Detected Docker bridge IP %s, falling back to original host", local_ip
            )

    # Fall back to localhost if we still don't have a good host
    if best_host in ["0.0.0.0", "127.0.0.1"] or not best_host:
        best_host = "localhost"

    return f"{protocol}://{best_host}:{port}"


def is_running_in_docker() -> bool:
    """
    Detect if the current process is running inside a Docker container.

    Returns:
        bool: True if running in Docker, False otherwise
    """
    try:
        # Check for .dockerenv file (most reliable method)
        if os.path.exists("/.dockerenv"):
            return True

        # Check cgroup for docker (backup method)
        try:
            with open("/proc/1/cgroup") as f:
                content = f.read()
                return "docker" in content or "containerd" in content
        except FileNotFoundError:
            pass

        return False
    except Exception:
        return False
