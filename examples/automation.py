#!/usr/bin/env python3
"""
Home Automation Example

Demonstrates integrating the Tiqiaa library into an automation script.
"""

import time
from tiqiaa import TiqiaaIR, load_ir_code, list_ir_codes

def send_code_by_name(ir: TiqiaaIR, name: str, repeat: int = 1) -> bool:
    """Send a saved IR code by name with optional repeat."""
    ir_data, freq = load_ir_code(name)
    if ir_data is None:
        print(f"Code '{name}' not found")
        return False

    for i in range(repeat):
        ir.send_ir(ir_data, freq)
        if repeat > 1:
            time.sleep(0.1)

    return True


def tv_power_sequence(ir: TiqiaaIR):
    """Example: Turn on TV and set volume."""
    print("Starting TV power-on sequence...")

    # Send power
    if send_code_by_name(ir, "power"):
        print("  Sent power command")
        time.sleep(2)  # Wait for TV to turn on

    # Mute first (in case volume was high)
    if send_code_by_name(ir, "mute"):
        print("  Sent mute command")
        time.sleep(0.5)

    # Set volume to comfortable level
    if send_code_by_name(ir, "volume_up", repeat=10):
        print("  Set volume")

    print("Sequence complete!")


def scheduled_action():
    """Example: Periodic action (like turning off at night)."""
    print("Scheduled shutdown...")

    ir = TiqiaaIR()
    if not ir.open():
        print("Device not available")
        return

    try:
        send_code_by_name(ir, "power")
        print("Power off sent")
    finally:
        ir.close()


def main():
    print("Tiqiaa IR Automation Example")
    print("=" * 40)

    # Check available codes
    codes = list_ir_codes()
    if not codes:
        print("\nNo IR codes found!")
        print("Learn some codes first with: python tiqiaa_cli.py learn <name>")
        print("\nSuggested codes to learn:")
        print("  - power")
        print("  - mute")
        print("  - volume_up")
        print("  - volume_down")
        return

    print(f"\nAvailable codes: {', '.join(codes)}")

    # Open device
    ir = TiqiaaIR()
    if not ir.open():
        return

    try:
        # Interactive menu
        while True:
            print("\n--- Menu ---")
            print("1. Send a code")
            print("2. Run TV power sequence (needs: power, mute, volume_up)")
            print("3. List codes")
            print("q. Quit")

            choice = input("\nChoice: ").strip().lower()

            if choice == '1':
                name = input("Code name: ").strip()
                if name in list_ir_codes():
                    send_code_by_name(ir, name)
                    print("Sent!")
                else:
                    print(f"Code '{name}' not found")

            elif choice == '2':
                tv_power_sequence(ir)

            elif choice == '3':
                codes = list_ir_codes()
                print(f"Available: {', '.join(codes)}")

            elif choice == 'q':
                break

    finally:
        ir.close()
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
