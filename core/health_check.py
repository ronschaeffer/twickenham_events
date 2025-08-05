#!/usr/bin/env python3
"""
Health check command for Twickenham Events
"""


def main():
    """Main entry point for the health check command."""
    print("Health check works!")
    return 0


if __name__ == "__main__":
    import sys

    exit_code = main()
    sys.exit(exit_code)
