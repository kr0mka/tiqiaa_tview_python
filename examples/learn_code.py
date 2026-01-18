#!/usr/bin/env python3
"""
Learn Code Example

Demonstrates how to learn IR codes from a remote control.
"""

from tiqiaa import TiqiaaIR, save_ir_code, decode_nec, format_nec_code

def main():
    # Create device instance
    ir = TiqiaaIR()

    # Open connection
    if not ir.open():
        print("Failed to open device")
        return

    try:
        print("Learning IR code...")
        print("Point your remote at the dongle and press a button.")
        print()

        # Wait for IR signal (15 second timeout)
        ir_data = ir.receive_ir(timeout_sec=15)

        if ir_data:
            print(f"\nReceived {len(ir_data)} bytes of IR data")

            # Try to decode as NEC
            nec_code = decode_nec(ir_data)
            if nec_code:
                print(f"Detected NEC: {format_nec_code(nec_code)}")

            # Save the code
            name = input("\nEnter a name for this code (or press Enter to skip): ").strip()
            if name:
                filepath = save_ir_code(name, ir_data)
                print(f"Saved to: {filepath}")
            else:
                print("Code not saved")

        else:
            print("\nNo IR signal received (timeout)")

    finally:
        ir.close()


if __name__ == "__main__":
    main()
