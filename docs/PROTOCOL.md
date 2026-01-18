# USB Protocol Documentation

Technical documentation for the Tiqiaa TView USB IR transceiver protocol.

**Credits:** Protocol reverse-engineered from [XenRE/tiqiaa-usb-ir](https://gitlab.com/XenRE/tiqiaa-usb-ir)

## Device Information

| Property | Value |
|----------|-------|
| Vendor ID | 0x10C4 (Silicon Labs) |
| Product ID | 0x8468 |
| USB Class | HID |
| Endpoints | OUT 0x01, IN 0x81 |

## Packet Structure

All communication uses a fragmented packet structure.

### USB Report Format

Reports are 61 bytes with the following structure:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | Report ID | 0x02 (out) or 0x01 (in) |
| 1 | 1 | Frag Size | Payload size + 3 |
| 2 | 1 | Packet Index | 1-15, increments per packet |
| 3 | 1 | Frag Count | Total fragments in packet |
| 4 | 1 | Frag Index | 1-based fragment number |
| 5 | 56 | Payload | Fragment data |

### Packet Framing

Reassembled packets have this structure:

| Offset | Size | Field | Value |
|--------|------|-------|-------|
| 0 | 2 | Start Marker | 0x5453 ("TS") |
| 2 | 1 | Command ID | Sequence number (1-127) |
| 3 | 1 | Command Type | See command types |
| 4+ | N | Data | Command-specific data |
| -2 | 2 | End Marker | 0x4E45 ("EN") |

## Commands

### Command Types

| Command | Byte | ASCII | Description |
|---------|------|-------|-------------|
| VERSION | 0x56 | 'V' | Get firmware version |
| IDLE_MODE | 0x4C | 'L' | Set idle mode |
| SEND_MODE | 0x53 | 'S' | Set transmit mode |
| RECV_MODE | 0x52 | 'R' | Set receive mode |
| DATA | 0x44 | 'D' | IR data packet |
| OUTPUT | 0x4F | 'O' | Start output/receive |
| CANCEL | 0x43 | 'C' | Cancel operation |

### Device States

| State | Value | Description |
|-------|-------|-------------|
| IDLE | 3 | Ready for commands |
| SEND | 9 | Transmit mode active |
| RECV | 19 | Receive mode active |

## Sending IR

### Set Send Mode

```
[TS] [CmdID] [0x53 'S'] [EN]
```

Device responds with same packet + state byte.

### Send IR Data

```
[TS] [CmdID] [0x44 'D'] [FreqID] [IR Data...] [EN]
```

- FreqID: Index into frequency table (0=38kHz)
- IR Data: Timing bytes (see below)

### IR Timing Format

Each byte in the IR data represents a timing period:

| Bit | Meaning |
|-----|---------|
| 7 | 1 = IR LED ON (mark), 0 = OFF (space) |
| 0-6 | Duration in 16µs ticks (0-127) |

Example: `0x8F` = LED ON for 143 ticks (2.3ms)
Example: `0x20` = LED OFF for 32 ticks (0.5ms)

## Receiving IR

### Set Receive Mode

```
[TS] [CmdID] [0x52 'R'] [EN]
```

### Start Receiving

```
[TS] [CmdID] [0x4F 'O'] [EN]
```

### Received IR Data

Device sends when IR signal is captured:

```
[TS] [CmdID] [0x44 'D'] [IR Data...] [EN]
```

## Frequency Table

The device supports 30 IR carrier frequencies:

| Index | Frequency | Common Use |
|-------|-----------|------------|
| 0 | 38000 Hz | NEC, Samsung, LG (most common) |
| 1 | 37900 Hz | - |
| 2 | 37917 Hz | - |
| 3 | 36000 Hz | RC5, RC6 |
| 4 | 40000 Hz | Sony |
| 5 | 39700 Hz | - |
| ... | ... | ... |

Default is 38kHz (index 0), which works for most consumer remotes.

## NEC Protocol

NEC is the most common IR protocol. Encoding details:

### Timing

- Base unit: 562.5µs
- Leader: 9ms mark + 4.5ms space
- Bit 0: 562.5µs mark + 562.5µs space
- Bit 1: 562.5µs mark + 1687.5µs space
- Stop bit: 562.5µs mark

### Frame Format

32 bits, LSB first:
1. Address (8 bits)
2. Inverted Address (8 bits)
3. Command (8 bits)
4. Inverted Command (8 bits)

### Repeat Code

When button is held, send repeat code:
- 9ms mark + 2.25ms space + 562.5µs mark

## Example: Sending NEC Code 0x00FF

1. Set send mode: `[5453] [01] [53] [4E45]`
2. Wait for response
3. Send IR data:
   - Packet: `[5453] [02] [44] [00] [IR_DATA] [4E45]`
   - FreqID 0 = 38kHz
   - IR_DATA encodes NEC frame

## Implementation Notes

### Fragment Size

Maximum fragment payload is 56 bytes. Larger packets are automatically fragmented.

### Packet Index

The packet index (1-15) should increment for each new packet. This helps with reassembly.

### Command ID

The command ID (1-127) identifies request/response pairs. Increment for each command.

### Timeouts

- USB write timeout: 2000ms
- USB read timeout: 100ms (for polling)
- Command response timeout: 1000ms
- IR receive timeout: Configurable (default 15s)

## Error Handling

### USB Errors

- Timeout on write: Retry up to 5 times with 100ms delay
- Stalled endpoint: Clear halt and retry
- Device not found: Check driver (WinUSB required on Windows)

### No Response

If device doesn't respond to mode change:
1. Send CANCEL command
2. Drain any pending data
3. Retry mode change
4. If still failing, reconnect device
