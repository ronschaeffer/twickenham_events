#!/usr/bin/env python3
"""Debug script for gateway parsing."""

import socket

# Test the hex parsing
gateway_hex = "FE11A8C0"
gateway_ip = socket.inet_ntoa(bytes.fromhex(gateway_hex)[::-1])
print(f"Gateway hex: {gateway_hex}")
print(f"Gateway IP: {gateway_ip}")

# Manual calculation
byte_data = bytes.fromhex(gateway_hex)
print(f"Bytes: {[hex(b) for b in byte_data]}")
print(f"Reversed: {[hex(b) for b in byte_data[::-1]]}")

# Let's see what we actually get
expected_bytes = [0xC0, 0xA8, 0x11, 0xFE]  # 192.168.17.254
actual_bytes = [0xFE, 0x11, 0xA8, 0xC0]  # What we have
print(f"Expected: {expected_bytes} -> {'.'.join(map(str, expected_bytes))}")
print(f"Actual: {actual_bytes} -> {'.'.join(map(str, actual_bytes))}")
