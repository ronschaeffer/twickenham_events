#!/usr/bin/env python3
"""
Simple test to verify the CLI argument parsing works.
"""

from core.__main__ import create_parser


def test_cli():
    parser = create_parser()

    # Test help
    print("=== Testing help ===")
    try:
        parser.parse_args(["--help"])
    except SystemExit:
        print("Help displayed correctly")

    # Test no arguments
    print("\n=== Testing no arguments ===")
    args = parser.parse_args([])
    print(f"Command: {args.command}")
    print(f"All args: {vars(args)}")

    # Test status command
    print("\n=== Testing status command ===")
    args = parser.parse_args(["status"])
    print(f"Command: {args.command}")
    print(f"All args: {vars(args)}")

    # Test dry run
    print("\n=== Testing dry run ===")
    args = parser.parse_args(["--dry-run", "scrape"])
    print(f"Command: {args.command}")
    print(f"Dry run: {args.dry_run}")


if __name__ == "__main__":
    test_cli()
