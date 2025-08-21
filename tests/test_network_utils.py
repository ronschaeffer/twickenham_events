"""
Test network utilities for smart URL building.
"""

import socket
from unittest.mock import mock_open, patch

from twickenham_events.network_utils import (
    build_smart_external_url,
    get_docker_host_ip,
    get_local_ipv4,
    is_running_in_docker,
)


class TestNetworkUtils:
    """Test network utility functions."""

    def test_get_local_ipv4_success(self):
        """Test successful local IPv4 detection."""
        with patch("socket.socket") as mock_socket:
            mock_sock = mock_socket.return_value.__enter__.return_value
            mock_sock.getsockname.return_value = ("192.168.1.100", 12345)

            result = get_local_ipv4()
            assert result == "192.168.1.100"

    def test_get_local_ipv4_failure(self):
        """Test failed local IPv4 detection."""
        with patch("socket.socket", side_effect=Exception("Network error")):
            result = get_local_ipv4()
            assert result is None

    def test_build_smart_external_url_explicit(self):
        """Test explicit external URL base takes priority."""
        result = build_smart_external_url(
            "0.0.0.0", 8080, external_url_base="https://example.com"
        )
        assert result == "https://example.com"

    def test_build_smart_external_url_with_trailing_slash(self):
        """Test explicit external URL base strips trailing slash."""
        result = build_smart_external_url(
            "0.0.0.0", 8080, external_url_base="https://example.com/"
        )
        assert result == "https://example.com"

    def test_build_smart_external_url_explicit_with_port(self):
        """Test explicit external URL base with port specified."""
        result = build_smart_external_url(
            "0.0.0.0", 8080, external_url_base="https://example.com:9090"
        )
        assert result == "https://example.com:9090"

    def test_build_smart_external_url_localhost_binding(self):
        """Test localhost binding uses host directly."""
        result = build_smart_external_url("localhost", 8080)
        assert result == "http://localhost:8080"

    def test_build_smart_external_url_auto_detect(self):
        """Test auto-detection for 0.0.0.0 binding."""
        with (
            patch(
                "twickenham_events.network_utils.get_local_ipv4",
                return_value="192.168.1.100",
            ),
            patch(
                "twickenham_events.network_utils.is_running_in_docker",
                return_value=False,
            ),
        ):
            result = build_smart_external_url("0.0.0.0", 8080)
            assert result == "http://192.168.1.100:8080"

    def test_build_smart_external_url_docker_fallback(self):
        """Test Docker host detection fallback."""
        with (
            patch(
                "twickenham_events.network_utils.is_running_in_docker",
                return_value=True,
            ),
            patch(
                "twickenham_events.network_utils.get_docker_host_ip",
                return_value="172.17.0.1",
            ),
        ):
            result = build_smart_external_url("0.0.0.0", 8080)
            assert result == "http://172.17.0.1:8080"

    def test_build_smart_external_url_localhost_fallback(self):
        """Test localhost fallback when detection fails."""
        with (
            patch(
                "twickenham_events.network_utils.is_running_in_docker",
                return_value=False,
            ),
            patch("twickenham_events.network_utils.get_local_ipv4", return_value=None),
        ):
            result = build_smart_external_url("0.0.0.0", 8080)
            assert result == "http://localhost:8080"

    def test_get_docker_host_ip_host_internal(self):
        """Test Docker host detection via host.docker.internal."""
        with patch("socket.gethostbyname", return_value="192.168.65.254"):
            result = get_docker_host_ip()
            assert result == "192.168.65.254"

    def test_get_docker_host_ip_gateway(self):
        """Test Docker host detection via gateway route."""
        # Use a standard Docker bridge gateway: 172.17.0.1 = 010011AC in hex (little endian)
        route_content = (
            "Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
            "eth0\t00000000\t010011AC\t0003\t0\t0\t0\t00000000\t0\t0\t0\n"
        )

        with (
            patch("socket.gethostbyname", side_effect=socket.gaierror),
            patch("builtins.open", mock_open(read_data=route_content)),
            patch(
                "twickenham_events.network_utils._probe_for_host_ip", return_value=None
            ),
        ):
            result = get_docker_host_ip()
            assert (
                result == "172.17.0.1"
            )  # Falls back to gateway when auto-detect fails

    def test_get_docker_host_ip_failure(self):
        """Test Docker host detection failure."""
        with (
            patch("socket.gethostbyname", side_effect=socket.gaierror),
            patch("builtins.open", side_effect=FileNotFoundError),
            patch(
                "twickenham_events.network_utils._probe_for_host_ip", return_value=None
            ),
        ):
            result = get_docker_host_ip()
            assert result is None

    def test_get_docker_host_ip_auto_detect(self):
        """Test Docker host detection via auto-detection."""
        with (
            patch("socket.gethostbyname", side_effect=socket.gaierror),
            patch(
                "twickenham_events.network_utils._probe_for_host_ip",
                return_value="10.10.10.20",
            ),
        ):
            result = get_docker_host_ip()
            assert result == "10.10.10.20"

    def test_is_running_in_docker_dockerenv(self):
        """Test Docker detection via .dockerenv file."""
        with patch("os.path.exists", return_value=True):
            assert is_running_in_docker() is True

    def test_is_running_in_docker_cgroup(self):
        """Test Docker detection via cgroup."""
        cgroup_content = "12:perf_event:/docker/abc123\n11:memory:/docker/abc123\n"

        with (
            patch("os.path.exists", return_value=False),
            patch("builtins.open", mock_open(read_data=cgroup_content)),
        ):
            assert is_running_in_docker() is True

    def test_is_running_in_docker_false(self):
        """Test non-Docker environment detection."""
        cgroup_content = "12:perf_event:/\n11:memory:/\n"

        with (
            patch("os.path.exists", return_value=False),
            patch("builtins.open", mock_open(read_data=cgroup_content)),
        ):
            assert is_running_in_docker() is False

    def test_is_running_in_docker_error(self):
        """Test Docker detection with errors."""
        with patch("os.path.exists", side_effect=Exception):
            assert is_running_in_docker() is False
