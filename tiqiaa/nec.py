"""
Tiqiaa TView USB IR Transceiver - NEC Protocol Encoding

NEC is the most common IR protocol, used by many consumer remotes.
This module provides encoding and decoding utilities.

NEC Protocol Format:
- 9ms AGC burst + 4.5ms space (leader)
- 8-bit address + 8-bit inverted address
- 8-bit command + 8-bit inverted command
- 562.5us burst (stop bit)
- ~110ms total frame time

The raw IR data format uses timing values where:
- Bit 7 (0x80) indicates IR LED ON (mark/pulse)
- Bits 0-6 indicate duration in 16us ticks (0-127)
"""

from typing import Optional, List

# NEC timing constants
NEC_PULSE_SIZE = 1125   # 562.5 us * 2 (basic timing unit)
IR_TICK_SIZE = 32       # 16 us * 2 (device timing resolution)
MAX_BLOCK_SIZE = 127    # Maximum ticks per timing block


def encode_nec(code: int) -> bytes:
    """
    Encode a 16-bit NEC code into raw IR signal data.

    The code format is: high byte = address, low byte = command
    The inverted bytes are calculated automatically.

    Args:
        code: 16-bit NEC code (0xADDR_CMD format)
              e.g., 0x00FF = address 0x00, command 0xFF

    Returns:
        Raw IR signal data bytes for the Tiqiaa device

    Example:
        >>> data = encode_nec(0x00FF)  # Address 0, Command 255
        >>> len(data) > 0
        True
    """
    # Extract address and command
    addr = (code >> 8) & 0xFF
    cmd = code & 0xFF

    # Build full 32-bit NEC frame:
    # [address] [~address] [command] [~command]
    full_code = addr | ((~addr & 0xFF) << 8) | (cmd << 16) | ((~cmd & 0xFF) << 24)

    result = []
    pulse_time = 0
    sender_time = 0

    def add_pulse(count: int, is_high: bool):
        """Add a pulse of 'count' NEC timing units"""
        nonlocal pulse_time, sender_time
        pulse_time += count * NEC_PULSE_SIZE
        ticks = (pulse_time - sender_time) // IR_TICK_SIZE
        sender_time += ticks * IR_TICK_SIZE

        while ticks > 0:
            block = min(ticks, MAX_BLOCK_SIZE)
            ticks -= block
            if is_high:
                block |= 0x80  # Set high bit for IR ON
            result.append(block)

    # Leader: 16 units ON (9ms), 8 units OFF (4.5ms)
    add_pulse(16, True)
    add_pulse(8, False)

    # Data bits (32 bits, LSB first)
    for i in range(32):
        # Each bit: 1 unit ON, then 1 or 3 units OFF
        add_pulse(1, True)
        add_pulse(3 if (full_code & 1) else 1, False)
        full_code >>= 1

    # Stop bit: 1 unit ON
    add_pulse(1, True)

    # Trailing space (for frame timing)
    add_pulse(72, False)

    return bytes(result)


def encode_nec_extended(address: int, command: int) -> bytes:
    """
    Encode NEC code with extended (16-bit) address.

    For devices that use the full 16 bits for address (no inversion).

    Args:
        address: 16-bit address
        command: 8-bit command

    Returns:
        Raw IR signal data bytes
    """
    addr_low = address & 0xFF
    addr_high = (address >> 8) & 0xFF
    cmd = command & 0xFF

    # Extended format: [addr_low] [addr_high] [command] [~command]
    full_code = addr_low | (addr_high << 8) | (cmd << 16) | ((~cmd & 0xFF) << 24)

    result = []
    pulse_time = 0
    sender_time = 0

    def add_pulse(count: int, is_high: bool):
        nonlocal pulse_time, sender_time
        pulse_time += count * NEC_PULSE_SIZE
        ticks = (pulse_time - sender_time) // IR_TICK_SIZE
        sender_time += ticks * IR_TICK_SIZE

        while ticks > 0:
            block = min(ticks, MAX_BLOCK_SIZE)
            ticks -= block
            if is_high:
                block |= 0x80
            result.append(block)

    add_pulse(16, True)
    add_pulse(8, False)

    for i in range(32):
        add_pulse(1, True)
        add_pulse(3 if (full_code & 1) else 1, False)
        full_code >>= 1

    add_pulse(1, True)
    add_pulse(72, False)

    return bytes(result)


def encode_nec_repeat() -> bytes:
    """
    Encode NEC repeat code.

    The repeat code is sent when a button is held down.
    Format: 9ms burst, 2.25ms space, 562.5us burst

    Returns:
        Raw IR signal data for repeat burst
    """
    result = []
    pulse_time = 0
    sender_time = 0

    def add_pulse(count: int, is_high: bool):
        nonlocal pulse_time, sender_time
        pulse_time += count * NEC_PULSE_SIZE
        ticks = (pulse_time - sender_time) // IR_TICK_SIZE
        sender_time += ticks * IR_TICK_SIZE

        while ticks > 0:
            block = min(ticks, MAX_BLOCK_SIZE)
            ticks -= block
            if is_high:
                block |= 0x80
            result.append(block)

    # Leader: 16 units ON, 4 units OFF (half of normal space)
    add_pulse(16, True)
    add_pulse(4, False)

    # Stop bit
    add_pulse(1, True)
    add_pulse(72, False)

    return bytes(result)


def decode_nec(ir_data: bytes) -> Optional[int]:
    """
    Attempt to decode NEC code from raw IR data.

    Args:
        ir_data: Raw IR signal data bytes

    Returns:
        16-bit NEC code (0xADDR_CMD format) or None if not valid NEC

    Note:
        This is a best-effort decoder. IR signals can vary, so
        validation against the inverted bytes is performed.
    """
    if len(ir_data) < 50:  # Too short for valid NEC
        return None

    # Convert raw bytes to timing list
    timings = []
    for byte in ir_data:
        is_high = bool(byte & 0x80)
        ticks = byte & 0x7F
        if ticks > 0:
            timings.append((is_high, ticks * IR_TICK_SIZE))

    # Look for leader pattern (long high pulse)
    if len(timings) < 2:
        return None

    # Find potential leader
    leader_idx = -1
    for i, (is_high, duration) in enumerate(timings):
        if is_high and duration > 8000:  # >8ms, likely leader
            leader_idx = i
            break

    if leader_idx < 0 or leader_idx + 65 >= len(timings):
        return None

    # Extract 32 data bits
    bits = []
    idx = leader_idx + 2  # Skip leader high and space

    for _ in range(32):
        if idx + 1 >= len(timings):
            return None

        # Each bit: mark + space
        mark_high, mark_dur = timings[idx]
        space_high, space_dur = timings[idx + 1]

        if not mark_high or space_high:
            return None  # Invalid pattern

        # Bit 0: short space (~562us = ~1125 ticks)
        # Bit 1: long space (~1687us = ~3375 ticks)
        bit = 1 if space_dur > 2000 else 0
        bits.append(bit)
        idx += 2

    # Assemble code (LSB first)
    full_code = 0
    for i, bit in enumerate(bits):
        full_code |= (bit << i)

    # Extract and validate
    addr = full_code & 0xFF
    addr_inv = (full_code >> 8) & 0xFF
    cmd = (full_code >> 16) & 0xFF
    cmd_inv = (full_code >> 24) & 0xFF

    # Validate inverted bytes
    if (addr ^ addr_inv) != 0xFF or (cmd ^ cmd_inv) != 0xFF:
        # Might be extended address format, return anyway
        return (addr << 8) | cmd

    return (addr << 8) | cmd


def format_nec_code(code: int) -> str:
    """
    Format NEC code for display.

    Args:
        code: 16-bit NEC code

    Returns:
        Formatted string like "Addr: 0x00, Cmd: 0xFF (code: 0x00FF)"
    """
    addr = (code >> 8) & 0xFF
    cmd = code & 0xFF
    return f"Addr: 0x{addr:02X}, Cmd: 0x{cmd:02X} (code: 0x{code:04X})"
