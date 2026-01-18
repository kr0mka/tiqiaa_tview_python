"""
Tiqiaa TView USB IR Transceiver - Protocol Constants

This module contains all protocol constants for communicating with
the Tiqiaa TView USB IR dongle.
"""

# Device identifiers
VID = 0x10C4  # Silicon Labs
PID = 0x8468  # Tiqiaa TView

# USB endpoints
EP_OUT = 0x01  # Host to device
EP_IN = 0x81   # Device to host

# Packet framing
PACK_START = 0x5453  # "TS" - packet start marker
PACK_END = 0x4E45    # "EN" - packet end marker
MAX_FRAG_SIZE = 56   # Maximum fragment payload size
MAX_PACKET_SIZE = 1024  # Maximum assembled packet size

# Commands
CMD_VERSION = ord('V')    # Get firmware version
CMD_IDLE_MODE = ord('L')  # Set device to idle mode
CMD_SEND_MODE = ord('S')  # Set device to send (transmit) mode
CMD_RECV_MODE = ord('R')  # Set device to receive (learn) mode
CMD_DATA = ord('D')       # IR data packet
CMD_OUTPUT = ord('O')     # Start output/receive operation
CMD_CANCEL = ord('C')     # Cancel current operation

# Device states
STATE_IDLE = 3   # Idle, ready for commands
STATE_SEND = 9   # Transmit mode active
STATE_RECV = 19  # Receive mode active

# IR frequency table (Hz) - 30 supported frequencies
# Index 0 is the default (38kHz), common for most consumer remotes
IR_FREQ_TABLE = [
    38000,  # 0 - Most common (NEC, Samsung, LG, etc.)
    37900,  # 1
    37917,  # 2
    36000,  # 3 - RC5/RC6
    40000,  # 4 - Sony
    39700,  # 5
    35750,  # 6
    36400,  # 7
    36700,  # 8
    37000,  # 9
    37700,  # 10
    38380,  # 11
    38400,  # 12
    38462,  # 13
    38740,  # 14
    39200,  # 15
    42000,  # 16
    43600,  # 17
    44000,  # 18
    33000,  # 19
    33500,  # 20
    34000,  # 21
    34500,  # 22
    35000,  # 23
    40500,  # 24
    41000,  # 25
    41500,  # 26
    42500,  # 27
    43000,  # 28
    45000,  # 29
]

# Default frequency for NEC protocol
DEFAULT_FREQ = 38000


def get_freq_index(freq: int) -> int:
    """
    Get the frequency table index for a given frequency.

    Args:
        freq: IR carrier frequency in Hz

    Returns:
        Index into IR_FREQ_TABLE, or 0 if frequency not found
    """
    try:
        return IR_FREQ_TABLE.index(freq)
    except ValueError:
        return 0


def get_freq_by_index(index: int) -> int:
    """
    Get the frequency for a given table index.

    Args:
        index: Index into the frequency table

    Returns:
        Frequency in Hz, or 38000 if index out of range
    """
    if 0 <= index < len(IR_FREQ_TABLE):
        return IR_FREQ_TABLE[index]
    return DEFAULT_FREQ
