#!/usr/bin/env python3
"""Minimal test for Poetry script issues"""

import sys


def main():
    print("Main function called with args:", sys.argv)

    try:
        import argparse

        print("✓ argparse imported successfully")

        parser = argparse.ArgumentParser()
        parser.add_argument("--version", action="version", version="test-version")
        print("✓ ArgumentParser created successfully")

        args = parser.parse_args()
        print("✓ Arguments parsed successfully")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
