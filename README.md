# Tview USB IR - Python Library

A clean, reusable Python library for the Tview USB IR transmitter/receiver dongle.

**Features:**
- Learn IR codes from any remote control
- Save and replay IR codes
- NEC protocol encoding/decoding
- Command-line interface (CLI)
- Graphical interface (GUI)
- Easy integration into home automation projects

## Supported Hardware

- **Device:** Tview
- **VID:** 0x10C4 (Silicon Labs)
- **PID:** 0x8468

## Driver Setup (Windows)

The dongle requires the **WinUSB** driver for Python/libusb access. Windows automatically installs a generic HID driver which must be replaced.

### Steps:

1. Download [Zadig](https://zadig.akeo.ie/) (portable, no install needed)
2. Connect the USB dongle
3. Run Zadig
4. Go to **Options → List All Devices**
5. Select **Tview** from the dropdown (or by USB ID `10C4:8468`)
6. Ensure **WinUSB** is selected as the replacement driver
7. Click **Replace Driver**
8. Wait for "Driver Installation Successful" message

### Verification:

```bash
python -c "from tiqiaa import TiqiaaIR; ir = TiqiaaIR(); print('Found!' if ir.open() else 'Not found')"
```

### Reverting to Original Driver:

If you need to use the device with the original Windows software:
1. Open Device Manager
2. Find "Tview" under "Universal Serial Bus devices"
3. Right-click → Update driver → Search automatically

See [docs/DRIVER_SETUP.md](docs/DRIVER_SETUP.md) for detailed instructions.

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/kr0mka/tiqiaa-tview-python.git
cd tiqiaa-tview-python

# Install dependencies
pip install -r requirements.txt

# Or install as editable package
pip install -e .
```

### Dependencies

- `pyusb>=1.2.1` - USB communication
- `libusb-package>=1.0.26.1` - Bundled libusb for Windows

## Quick Start

### Python API

```python
from tiqiaa import TiqiaaIR, save_ir_code, load_ir_code

# Open device
ir = TiqiaaIR()
if ir.open():
    # Send a NEC code directly
    ir.send_nec(0x00FF)  # Address 0x00, Command 0xFF

    # Learn a code from a remote
    data = ir.receive_ir(timeout_sec=10)
    if data:
        save_ir_code("power", data)

    # Send a saved code
    data, freq = load_ir_code("power")
    if data:
        ir.send_ir(data, freq)

    ir.close()
```

### Context Manager

```python
from tiqiaa import TiqiaaIR

with TiqiaaIR() as ir:
    ir.send_nec(0x00FF)
```

### CLI Tool

```bash
# Learn an IR code
python tiqiaa_cli.py learn power

# Send a saved code
python tiqiaa_cli.py send power

# Send code 3 times
python tiqiaa_cli.py send power -r 3

# Send a raw NEC code
python tiqiaa_cli.py send-nec 0x00FF

# List saved codes
python tiqiaa_cli.py list

# Test device
python tiqiaa_cli.py test

# Show device info
python tiqiaa_cli.py info
```

### GUI Tool

```bash
python tiqiaa_gui.py
```

The GUI provides:
- Buttons for each saved IR code
- Click to send once, hold to repeat
- Learn new codes interactively
- Delete codes

## CLI Reference

| Command | Description |
|---------|-------------|
| `learn <name>` | Learn an IR code and save it |
| `send <name>` | Send a saved IR code |
| `send-nec <code>` | Send a raw NEC code (e.g., 0x1234) |
| `receive` | Receive and display IR signals |
| `list` | List saved IR codes |
| `delete <name>` | Delete a saved IR code |
| `test` | Test IR transmission |
| `info` | Show device info |

### Options

```bash
# Learn with options
python tiqiaa_cli.py learn power -t 20 -s "Samsung TV" -n "Power toggle"

# Send with repeat
python tiqiaa_cli.py send volume_up -r 5 -d 0.05
```

## API Reference

### TiqiaaIR Class

```python
class TiqiaaIR:
    def open(self, verbose: bool = True) -> bool:
        """Open connection to device."""

    def close(self):
        """Close device connection."""

    def send_ir(self, ir_data: bytes, freq: int = 38000) -> bool:
        """Send raw IR signal data at specified frequency."""

    def send_nec(self, code: int) -> bool:
        """Send a 16-bit NEC protocol code."""

    def receive_ir(self, timeout_sec: int = 15) -> Optional[bytes]:
        """Wait for and capture an IR signal."""

    def is_connected(self) -> bool:
        """Check if device is connected."""
```

### Storage Functions

```python
def save_ir_code(name, ir_data, freq=38000, learned_from=None, notes=None) -> Path
def load_ir_code(name) -> Tuple[Optional[bytes], int]
def list_ir_codes() -> List[str]
def delete_ir_code(name) -> bool
```

### NEC Protocol

```python
def encode_nec(code: int) -> bytes
def decode_nec(ir_data: bytes) -> Optional[int]
def format_nec_code(code: int) -> str
```

## IR Code File Format

IR codes are stored as JSON files with `.ir` extension in the `ir_codes/` directory:

```json
{
    "name": "power",
    "frequency": 38000,
    "data": [143, 127, 71, 63, 17, 17, 17, ...],
    "learned_from": "Samsung TV Remote",
    "notes": "Power toggle button"
}
```

### Optional Tap/Hold Support

For codes that behave differently on tap vs hold:

```json
{
    "name": "volume_up",
    "frequency": 38000,
    "data": [143, 127, ...],
    "tap": [71, 63, 17, ...],
    "notes": "Tap for single step, hold for continuous"
}
```

## Project Structure

```
tiqiaa-tview-python/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
│
├── tiqiaa/
│   ├── __init__.py
│   ├── device.py
│   ├── protocol.py
│   ├── nec.py
│   └── storage.py
│
├── tiqiaa_cli.py
├── tiqiaa_gui.py
│
├── examples/
│   ├── basic_send.py
│   ├── learn_code.py
│   └── automation.py
│
├── ir_codes/
│
└── docs/
    ├── DRIVER_SETUP.md
    └── PROTOCOL.md
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Credits

Based on protocol reverse-engineering from [XenRE/tiqiaa-usb-ir](https://gitlab.com/XenRE/tiqiaa-usb-ir)
