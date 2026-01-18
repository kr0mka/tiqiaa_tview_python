"""
Tiqiaa TView USB IR Transceiver - Python Library

A clean, reusable Python library for the Tiqiaa TView USB IR
transmitter/receiver dongle.

Features:
    - Core USB communication with the dongle
    - IR code learning (receive mode)
    - IR code transmission (send mode)
    - NEC protocol encoding/decoding
    - IR code storage (JSON format)

Based on protocol reverse-engineering from:
https://gitlab.com/XenRE/tiqiaa-usb-ir

Requirements:
    - pyusb >= 1.2.1
    - libusb-package >= 1.0.26.1
    - WinUSB driver (Windows only, install via Zadig)

Quick Start:
    >>> from tiqiaa import TiqiaaIR
    >>> ir = TiqiaaIR()
    >>> if ir.open():
    ...     ir.send_nec(0x00FF)  # Send NEC code
    ...     ir.close()

    # Or use context manager:
    >>> with TiqiaaIR() as ir:
    ...     ir.send_nec(0x00FF)

License: MIT
"""

__version__ = "1.0.0"
__author__ = "Tiqiaa Python Library Contributors"
__credits__ = "Based on protocol work from https://gitlab.com/XenRE/tiqiaa-usb-ir"

# Core device driver
from .device import TiqiaaIR

# Protocol constants
from .protocol import (
    VID,
    PID,
    IR_FREQ_TABLE,
    DEFAULT_FREQ,
    get_freq_index,
    get_freq_by_index,
)

# NEC protocol utilities
from .nec import (
    encode_nec,
    encode_nec_extended,
    encode_nec_repeat,
    decode_nec,
    format_nec_code,
)

# Storage utilities
from .storage import (
    save_ir_code,
    load_ir_code,
    load_ir_code_full,
    load_smart_code,
    list_ir_codes,
    delete_ir_code,
    export_codes,
    import_codes,
)

__all__ = [
    # Version
    "__version__",

    # Core
    "TiqiaaIR",

    # Protocol
    "VID",
    "PID",
    "IR_FREQ_TABLE",
    "DEFAULT_FREQ",
    "get_freq_index",
    "get_freq_by_index",

    # NEC
    "encode_nec",
    "encode_nec_extended",
    "encode_nec_repeat",
    "decode_nec",
    "format_nec_code",

    # Storage
    "save_ir_code",
    "load_ir_code",
    "load_ir_code_full",
    "load_smart_code",
    "list_ir_codes",
    "delete_ir_code",
    "export_codes",
    "import_codes",
]
