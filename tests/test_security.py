"""Unit tests for ribeira_platform.security.

Covers the pure validation logic of NetworkPolicy.validate. No database,
network or external provider is required: DNS resolution is replaced with a
deterministic fake so every branch is exercised without real socket access.

The real resolver behaviour (actual DNS lookup) is intentionally not covered
here; it is an infrastructure dependency and would make the suite flaky and
network-dependent.
"""

from __future__ import annotations

import socket
import unittest
from unittest.mock import patch

from ribeira_platform.security import NetworkPolicy, SSRFBlocked


def _addrinfo(*addresses: str, port: int = 443):
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
        for address in addresses
    ]


class NetworkPolicyValidateTests(unittest.TestCase):
    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_allows_public_host(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("93.184.216.34")
        policy = NetworkPolicy()
        policy.validate("https://example.com/data")
        getaddrinfo.assert_called_once()

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_allows_public_host_with_explicit_port(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("93.184.216.34", port=8443)
        policy = NetworkPolicy()
        policy.validate("https://example.com:8443/data")
        getaddrinfo.assert_called_once_with(
            "example.com",
            8443,
            type=socket.SOCK_STREAM,
        )

    def test_non_http_scheme_is_blocked(self) -> None:
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("ftp://example.com/data")

    def test_missing_hostname_is_blocked(self) -> None:
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("https:///only-a-path")

    def test_allowlist_rejects_unlisted_host(self) -> None:
        policy = NetworkPolicy(allowed_hosts=frozenset({"api.example.com"}))
        with self.assertRaises(SSRFBlocked):
            policy.validate("https://other.example.com/data")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_allowlist_accepts_listed_host(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("93.184.216.34")
        policy = NetworkPolicy(allowed_hosts=frozenset({"api.example.com"}))
        policy.validate("https://api.example.com/data")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_hostname_is_normalized_case_and_trailing_dot(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("93.184.216.34")
        policy = NetworkPolicy(allowed_hosts=frozenset({"api.example.com"}))
        policy.validate("https://API.Example.COM./data")
        getaddrinfo.assert_called_once_with(
            "api.example.com",
            443,
            type=socket.SOCK_STREAM,
        )

    def test_localhost_is_blocked(self) -> None:
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://localhost/admin")

    def test_metadata_host_is_blocked(self) -> None:
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://metadata.google.internal/computeMetadata/v1/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_private_address_is_blocked(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("10.0.0.5")
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://internal.example.com/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_loopback_address_is_blocked(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("127.0.0.1")
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://example.com/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_link_local_address_is_blocked(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("169.254.169.254")
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://example.com/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_unspecified_address_is_blocked(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("0.0.0.0")
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://example.com/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_multicast_address_is_blocked(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("224.0.0.1")
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://example.com/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_reserved_address_is_blocked(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("240.0.0.1")
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://example.com/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_any_non_public_address_in_resolution_is_blocked(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("93.184.216.34", "10.0.0.5")
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://example.com/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_allow_private_hosts_permits_private_address(self, getaddrinfo) -> None:
        getaddrinfo.return_value = _addrinfo("10.0.0.5")
        policy = NetworkPolicy(allow_private_hosts=True)
        policy.validate("http://internal.example.com/")

    @patch("ribeira_platform.security.socket.getaddrinfo")
    def test_unresolvable_host_is_blocked(self, getaddrinfo) -> None:
        getaddrinfo.side_effect = socket.gaierror("name resolution failed")
        policy = NetworkPolicy()
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://does-not-resolve.example.com/")

    def test_localhost_is_blocked_even_when_allowlisted(self) -> None:
        policy = NetworkPolicy(allowed_hosts=frozenset({"localhost"}))
        with self.assertRaises(SSRFBlocked):
            policy.validate("http://localhost/admin")


if __name__ == "__main__":
    unittest.main()
