#!/usr/bin/env python3
"""
Tiqiaa TView USB IR - Command Line Interface

A CLI tool for learning, saving, and sending IR codes.

Usage:
    python tiqiaa_cli.py learn <name>      Learn an IR code and save it
    python tiqiaa_cli.py send <name>       Send a saved IR code
    python tiqiaa_cli.py send-nec <code>   Send a raw NEC code (e.g. 0x1234)
    python tiqiaa_cli.py list              List saved IR codes
    python tiqiaa_cli.py delete <name>     Delete a saved IR code
    python tiqiaa_cli.py test              Test IR transmission
    python tiqiaa_cli.py info              Show device info

Based on protocol work from: https://gitlab.com/XenRE/tiqiaa-usb-ir
"""

import sys
import time
import argparse
from pathlib import Path

from tiqiaa import (
    TiqiaaIR,
    save_ir_code,
    load_ir_code,
    list_ir_codes,
    delete_ir_code,
    decode_nec,
    format_nec_code,
    __version__,
)


def cmd_learn(args):
    """Learn an IR code and save it."""
    name = args.name

    ir = TiqiaaIR()
    if not ir.open():
        return 1

    try:
        timeout = args.timeout or 15
        print(f"\nLearning IR code: {name}")

        ir_data = ir.receive_ir(timeout_sec=timeout)
        if ir_data:
            # Try to decode as NEC
            nec_code = decode_nec(ir_data)
            if nec_code:
                print(f"Detected NEC: {format_nec_code(nec_code)}")

            # Save the code
            filepath = save_ir_code(
                name,
                ir_data,
                freq=args.freq or 38000,
                learned_from=args.source,
                notes=args.notes
            )
            print(f"Saved to: {filepath}")
            return 0
        else:
            print("Learning failed - no IR signal received")
            return 1
    finally:
        ir.close()


def cmd_send(args):
    """Send a saved IR code."""
    name = args.name

    ir_data, freq = load_ir_code(name)
    if ir_data is None:
        print(f"IR code '{name}' not found")
        print("Use 'tiqiaa_cli.py list' to see available codes")
        return 1

    ir = TiqiaaIR()
    if not ir.open():
        return 1

    try:
        repeat = args.repeat or 1
        delay = args.delay or 0.1

        print(f"Sending '{name}' ({len(ir_data)} bytes at {freq}Hz)")
        for i in range(repeat):
            ir.send_ir(ir_data, freq)
            if repeat > 1:
                print(f"  Sent {i + 1}/{repeat}")
            if i < repeat - 1:
                time.sleep(delay)

        print("Done!")
        return 0
    finally:
        ir.close()


def cmd_send_nec(args):
    """Send a raw NEC code."""
    try:
        code = int(args.code, 0)  # Auto-detect base (0x for hex)
    except ValueError:
        print(f"Invalid code: {args.code}")
        print("Use hex (0x1234) or decimal (4660) format")
        return 1

    if code < 0 or code > 0xFFFF:
        print(f"Code out of range: {code}. Must be 0x0000-0xFFFF")
        return 1

    ir = TiqiaaIR()
    if not ir.open():
        return 1

    try:
        repeat = args.repeat or 1
        delay = args.delay or 0.1

        print(f"Sending NEC {format_nec_code(code)}")
        for i in range(repeat):
            ir.send_nec(code)
            if repeat > 1:
                print(f"  Sent {i + 1}/{repeat}")
            if i < repeat - 1:
                time.sleep(delay)

        print("Done!")
        return 0
    finally:
        ir.close()


def cmd_list(args):
    """List saved IR codes."""
    codes = list_ir_codes()

    if not codes:
        print("No IR codes saved yet")
        print("Use 'tiqiaa_cli.py learn <name>' to learn a new code")
        return 0

    print(f"Saved IR codes ({len(codes)}):")
    for name in codes:
        ir_data, freq = load_ir_code(name)
        size = len(ir_data) if ir_data else 0
        print(f"  - {name} ({size} bytes, {freq}Hz)")

    return 0


def cmd_delete(args):
    """Delete a saved IR code."""
    name = args.name

    if delete_ir_code(name):
        print(f"Deleted: {name}")
        return 0
    else:
        print(f"IR code '{name}' not found")
        return 1


def cmd_test(args):
    """Test IR transmission."""
    ir = TiqiaaIR()
    if not ir.open():
        return 1

    try:
        print("\nSending test NEC codes...")
        print("Watch the IR LED (use phone camera to see IR light)")
        print()

        test_codes = [0x1234, 0x00FF, 0xFF00]
        for code in test_codes:
            print(f"  Sending {format_nec_code(code)}...")
            ir.send_nec(code)
            time.sleep(0.5)

        print("\nTest complete!")
        print("If you saw the IR LED flash (purple/white in phone camera),")
        print("the device is working correctly.")
        return 0
    finally:
        ir.close()


def cmd_info(args):
    """Show device info."""
    print(f"Tiqiaa TView IR Library v{__version__}")
    print()

    ir = TiqiaaIR()
    print("Searching for device...")

    if ir.open(verbose=False):
        print("Device: Connected")
        print(f"  VID: 0x{0x10C4:04X} (Silicon Labs)")
        print(f"  PID: 0x{0x8468:04X} (Tiqiaa TView)")
        ir.close()
    else:
        print("Device: Not found")
        print()
        print("Troubleshooting:")
        print("  1. Is the Tiqiaa dongle plugged in?")
        print("  2. Is WinUSB driver installed? (Use Zadig)")
        print("  3. Try unplugging and replugging the device")

    print()
    codes = list_ir_codes()
    print(f"Saved codes: {len(codes)}")

    return 0


def cmd_receive(args):
    """Receive and display IR signals without saving."""
    ir = TiqiaaIR()
    if not ir.open():
        return 1

    try:
        timeout = args.timeout or 15
        count = args.count or 1

        print(f"\nReceive mode - waiting for {count} signal(s)")

        for i in range(count):
            if count > 1:
                print(f"\n--- Signal {i + 1}/{count} ---")

            ir_data = ir.receive_ir(timeout_sec=timeout)
            if ir_data:
                print(f"Data ({len(ir_data)} bytes):")
                # Print hex dump
                hex_str = ' '.join(f'{b:02X}' for b in ir_data[:64])
                print(f"  {hex_str}")
                if len(ir_data) > 64:
                    print(f"  ... ({len(ir_data) - 64} more bytes)")

                # Try NEC decode
                nec_code = decode_nec(ir_data)
                if nec_code:
                    print(f"NEC: {format_nec_code(nec_code)}")
            else:
                print("Timeout")

            if i < count - 1:
                time.sleep(0.5)

        return 0
    finally:
        ir.close()


def main():
    parser = argparse.ArgumentParser(
        description="Tiqiaa TView USB IR - Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s learn power              Learn and save an IR code named 'power'
  %(prog)s send power               Send the saved 'power' code
  %(prog)s send power -r 3          Send 'power' code 3 times
  %(prog)s send-nec 0x00FF          Send NEC code (address=0x00, cmd=0xFF)
  %(prog)s list                     List all saved codes
  %(prog)s test                     Test device with sample codes
  %(prog)s receive -c 5             Receive and display 5 IR signals

Based on protocol work from: https://gitlab.com/XenRE/tiqiaa-usb-ir
"""
    )

    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # learn
    learn_parser = subparsers.add_parser('learn', help='Learn an IR code and save it')
    learn_parser.add_argument('name', help='Name for the IR code')
    learn_parser.add_argument('-t', '--timeout', type=int, default=15,
                              help='Timeout in seconds (default: 15)')
    learn_parser.add_argument('-f', '--freq', type=int, default=38000,
                              help='IR frequency in Hz (default: 38000)')
    learn_parser.add_argument('-s', '--source', help='Source description (e.g., "Samsung TV Remote")')
    learn_parser.add_argument('-n', '--notes', help='Notes about this code')
    learn_parser.set_defaults(func=cmd_learn)

    # send
    send_parser = subparsers.add_parser('send', help='Send a saved IR code')
    send_parser.add_argument('name', help='Name of the IR code to send')
    send_parser.add_argument('-r', '--repeat', type=int, default=1,
                             help='Number of times to send (default: 1)')
    send_parser.add_argument('-d', '--delay', type=float, default=0.1,
                             help='Delay between repeats in seconds (default: 0.1)')
    send_parser.set_defaults(func=cmd_send)

    # send-nec
    nec_parser = subparsers.add_parser('send-nec', help='Send a raw NEC code')
    nec_parser.add_argument('code', help='NEC code in hex (0x1234) or decimal')
    nec_parser.add_argument('-r', '--repeat', type=int, default=1,
                            help='Number of times to send (default: 1)')
    nec_parser.add_argument('-d', '--delay', type=float, default=0.1,
                            help='Delay between repeats in seconds (default: 0.1)')
    nec_parser.set_defaults(func=cmd_send_nec)

    # list
    list_parser = subparsers.add_parser('list', help='List saved IR codes')
    list_parser.set_defaults(func=cmd_list)

    # delete
    delete_parser = subparsers.add_parser('delete', help='Delete a saved IR code')
    delete_parser.add_argument('name', help='Name of the IR code to delete')
    delete_parser.set_defaults(func=cmd_delete)

    # test
    test_parser = subparsers.add_parser('test', help='Test IR transmission')
    test_parser.set_defaults(func=cmd_test)

    # info
    info_parser = subparsers.add_parser('info', help='Show device info')
    info_parser.set_defaults(func=cmd_info)

    # receive
    receive_parser = subparsers.add_parser('receive', help='Receive and display IR signals')
    receive_parser.add_argument('-t', '--timeout', type=int, default=15,
                                help='Timeout per signal in seconds (default: 15)')
    receive_parser.add_argument('-c', '--count', type=int, default=1,
                                help='Number of signals to receive (default: 1)')
    receive_parser.set_defaults(func=cmd_receive)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
