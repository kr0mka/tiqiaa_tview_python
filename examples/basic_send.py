#!/usr/bin/env python3
"""
Basic Send Example

Demonstrates how to send IR codes with the Tiqiaa library.
"""

from tiqiaa import TiqiaaIR, load_ir_code

def main():
    # Create device instance
    ir = TiqiaaIR()

    # Open connection
    if not ir.open():
        print("Failed to open device")
        print("Make sure the device is connected and WinUSB driver is installed")
        return

    try:
        # Method 1: Send a raw NEC code
        print("Sending NEC code 0x00FF...")
        ir.send_nec(0x00FF)
        print("Sent!")

        # Method 2: Send a saved IR code
        print("\nTrying to send saved 'power' code...")
        ir_data, freq = load_ir_code("power")
        if ir_data:
            ir.send_ir(ir_data, freq)
            print("Sent saved code!")
        else:
            print("No saved 'power' code found")
            print("Use 'python tiqiaa_cli.py learn power' to learn one")

    finally:
        # Always close the device
        ir.close()


if __name__ == "__main__":
    main()
