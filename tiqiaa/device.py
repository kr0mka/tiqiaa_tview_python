"""
Tiqiaa TView USB IR Transceiver - Device Driver

Core driver for USB communication with the Tiqiaa TView IR dongle.

Based on protocol reverse-engineering from:
https://gitlab.com/XenRE/tiqiaa-usb-ir

Requirements:
    - pyusb >= 1.2.1
    - libusb-package >= 1.0.26.1 (provides bundled libusb)
    - WinUSB driver installed via Zadig (Windows only)
"""

import usb.core
import usb.util
import struct
import time
import threading
from typing import Optional, Callable

try:
    import libusb_package
    HAS_LIBUSB_PACKAGE = True
except ImportError:
    HAS_LIBUSB_PACKAGE = False

from .protocol import (
    VID, PID, EP_OUT, EP_IN,
    PACK_START, PACK_END, MAX_FRAG_SIZE,
    CMD_VERSION, CMD_IDLE_MODE, CMD_SEND_MODE, CMD_RECV_MODE,
    CMD_DATA, CMD_OUTPUT, CMD_CANCEL,
    STATE_IDLE, STATE_SEND, STATE_RECV,
    IR_FREQ_TABLE, get_freq_index
)
from .nec import encode_nec


class TiqiaaIR:
    """
    USB IR transceiver driver for Tiqiaa TView dongle.

    This class handles all low-level USB communication including:
    - Device discovery and connection
    - Packet fragmentation and reassembly
    - Mode switching (send/receive)
    - IR signal transmission and reception

    Example:
        >>> ir = TiqiaaIR()
        >>> if ir.open():
        ...     ir.send_nec(0x00FF)  # Send NEC code
        ...     ir.close()
    """

    def __init__(self):
        """Initialize the IR transceiver (does not connect)."""
        self.dev = None
        self.packet_idx = 0
        self.cmd_id = 0
        self.device_state = 0
        self.read_thread = None
        self.read_active = False
        self.received_packets = []
        self.packet_event = threading.Event()
        self.lock = threading.Lock()

        # For packet reassembly
        self._recv_buffer = bytearray()
        self._recv_packet_idx = 0
        self._recv_frag_count = 0
        self._recv_last_frag = 0

    def open(self, verbose: bool = True) -> bool:
        """
        Open connection to the IR device.

        Args:
            verbose: Print status messages (default True)

        Returns:
            True if device found and initialized, False otherwise

        Note:
            On Windows, the device must have the WinUSB driver installed.
            Use Zadig (https://zadig.akeo.ie/) to install it.
        """
        # Get libusb backend
        backend = None
        if HAS_LIBUSB_PACKAGE:
            backend = libusb_package.get_libusb1_backend()

        self.dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)

        if self.dev is None:
            if verbose:
                print("Device not found!")
                print("Make sure:")
                print("  1. Tiqiaa TView dongle is plugged in")
                print("  2. WinUSB driver is installed (use Zadig)")
            return False

        try:
            self.dev.set_configuration()
        except usb.core.USBError:
            pass  # Already configured

        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        except (usb.core.USBError, NotImplementedError):
            pass

        usb.util.claim_interface(self.dev, 0)

        # Clear stalled endpoints
        try:
            self.dev.clear_halt(EP_OUT)
        except:
            pass
        try:
            self.dev.clear_halt(EP_IN)
        except:
            pass

        # Drain pending data
        for _ in range(10):
            try:
                self.dev.read(EP_IN, 64, timeout=50)
            except:
                pass

        # Start background read thread
        self.read_active = True
        self.read_thread = threading.Thread(target=self._read_thread, daemon=True)
        self.read_thread.start()

        time.sleep(0.2)

        # Initialize to send mode
        for attempt in range(3):
            try:
                self._send_cmd(CMD_SEND_MODE)
                time.sleep(0.2)
                self.device_state = STATE_SEND
                if verbose:
                    print("Device opened successfully!")
                return True
            except usb.core.USBTimeoutError:
                if verbose:
                    print(f"Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(0.3)
            except usb.core.USBError as e:
                if verbose:
                    print(f"USB error on attempt {attempt + 1}: {e}, retrying...")
                time.sleep(0.3)

        if verbose:
            print("Failed to initialize device - try unplugging and replugging")
        return False

    def close(self):
        """Close the device connection and release resources."""
        if self.dev:
            self.read_active = False
            try:
                self._send_cmd(CMD_IDLE_MODE)
            except:
                pass
            try:
                usb.util.release_interface(self.dev, 0)
            except:
                pass
            self.dev = None

    def is_connected(self) -> bool:
        """
        Check if device is connected.

        Returns:
            True if device handle is valid
        """
        return self.dev is not None

    def send_ir(self, ir_data: bytes, freq: int = 38000) -> bool:
        """
        Send raw IR signal data.

        Args:
            ir_data: Raw IR signal bytes (timing data)
            freq: Carrier frequency in Hz (default 38000)

        Returns:
            True if sent successfully

        Note:
            The ir_data format uses timing bytes where bit 7 indicates
            IR LED state (on/off) and bits 0-6 indicate duration in
            16us ticks.
        """
        if self.device_state != STATE_SEND:
            if not self._send_cmd_wait(CMD_SEND_MODE):
                return False

        freq_id = get_freq_index(freq)
        cmd_id = self._get_cmd_id()

        # Build IR packet
        packet = struct.pack('<HBB', PACK_START, cmd_id, CMD_DATA)
        packet += bytes([freq_id])
        packet += ir_data
        packet += struct.pack('<H', PACK_END)

        with self.lock:
            self.received_packets.clear()
            self.packet_event.clear()

        self._send_report(packet)

        # Wait for completion acknowledgment
        start = time.time()
        while time.time() - start < 2.0:
            if self.packet_event.wait(timeout=0.1):
                with self.lock:
                    for pkt in self.received_packets:
                        if len(pkt) >= 2 and pkt[0] == cmd_id and pkt[1] == CMD_OUTPUT:
                            return True
                    self.packet_event.clear()

        return True  # Assume sent even without confirmation

    def send_nec(self, code: int) -> bool:
        """
        Send a NEC protocol code.

        Args:
            code: 16-bit NEC code (high byte=address, low byte=command)

        Returns:
            True if sent successfully

        Example:
            >>> ir.send_nec(0x00FF)  # Address 0x00, Command 0xFF
        """
        ir_data = encode_nec(code)
        return self.send_ir(ir_data, 38000)

    def receive_ir(
        self,
        timeout_sec: int = 15,
        callback: Optional[Callable[[bytes], None]] = None,
        verbose: bool = True
    ) -> Optional[bytes]:
        """
        Receive/learn an IR signal.

        Puts the device in receive mode and waits for an IR signal.

        Args:
            timeout_sec: Maximum time to wait in seconds
            callback: Optional callback called when signal received
            verbose: Print status messages

        Returns:
            Raw IR signal data, or None if timeout/error

        Example:
            >>> data = ir.receive_ir(timeout_sec=10)
            >>> if data:
            ...     print(f"Received {len(data)} bytes")
        """
        # Switch to receive mode
        if not self._send_cmd_wait(CMD_RECV_MODE):
            if verbose:
                print("Failed to set receive mode")
            return None

        # Cancel any pending receive
        self._send_cmd_wait(CMD_CANCEL)

        # Clear received data
        with self.lock:
            self.received_packets.clear()
            self.packet_event.clear()

        # Start receiving
        self._send_cmd(CMD_OUTPUT)

        if verbose:
            print(f"Waiting for IR signal ({timeout_sec}s)...")
            print("Press a button on your remote, pointed at the receiver.")

        # Wait for IR data
        start = time.time()
        while time.time() - start < timeout_sec:
            if self.packet_event.wait(timeout=0.5):
                with self.lock:
                    for pkt in self.received_packets:
                        if len(pkt) >= 2 and pkt[1] == CMD_DATA:
                            ir_data = pkt[2:]
                            if verbose:
                                print(f"\nReceived {len(ir_data)} bytes of IR data!")
                            if callback:
                                callback(ir_data)
                            return ir_data
                    self.packet_event.clear()

        if verbose:
            print("\nTimeout - no IR signal received")
        return None

    def set_mode(self, mode: str) -> bool:
        """
        Set device operating mode.

        Args:
            mode: One of 'send', 'receive', or 'idle'

        Returns:
            True if mode set successfully
        """
        cmd_map = {
            'send': CMD_SEND_MODE,
            'receive': CMD_RECV_MODE,
            'idle': CMD_IDLE_MODE
        }

        if mode not in cmd_map:
            raise ValueError(f"Invalid mode: {mode}. Use 'send', 'receive', or 'idle'")

        return self._send_cmd_wait(cmd_map[mode])

    # ---------- Internal Methods ----------

    def _get_packet_idx(self) -> int:
        """Get next packet index (1-15, wrapping)."""
        self.packet_idx = (self.packet_idx % 15) + 1
        return self.packet_idx

    def _get_cmd_id(self) -> int:
        """Get next command ID (1-127, wrapping)."""
        self.cmd_id = (self.cmd_id % 0x7F) + 1
        return self.cmd_id

    def _send_report(self, data: bytes):
        """
        Send data with fragmentation via USB Report ID 2.

        Large packets are split into 56-byte fragments.
        """
        packet_idx = self._get_packet_idx()
        frag_count = (len(data) + MAX_FRAG_SIZE - 1) // MAX_FRAG_SIZE

        offset = 0
        frag_idx = 0
        while offset < len(data):
            frag_idx += 1
            chunk = data[offset:offset + MAX_FRAG_SIZE]
            frag_size = len(chunk) + 3

            # Report format: [ReportID, FragSize, PacketIdx, FragCount, FragIdx, Data...]
            report = bytes([0x02, frag_size, packet_idx, frag_count, frag_idx]) + chunk
            report = report.ljust(61, b'\x00')

            for attempt in range(5):
                try:
                    self.dev.write(EP_OUT, report, timeout=2000)
                    break
                except usb.core.USBTimeoutError:
                    if attempt == 4:
                        raise
                    time.sleep(0.1)
                except usb.core.USBError:
                    if attempt == 4:
                        raise
                    time.sleep(0.1)

            offset += MAX_FRAG_SIZE

    def _send_cmd(self, cmd_type: int, cmd_id: Optional[int] = None) -> int:
        """Send a command packet."""
        if cmd_id is None:
            cmd_id = self._get_cmd_id()
        packet = struct.pack('<HBBH', PACK_START, cmd_id, cmd_type, PACK_END)
        self._send_report(packet)
        return cmd_id

    def _send_cmd_wait(self, cmd_type: int, timeout: float = 1.0) -> bool:
        """Send command and wait for reply."""
        cmd_id = self._get_cmd_id()

        with self.lock:
            self.received_packets.clear()
            self.packet_event.clear()

        self._send_cmd(cmd_type, cmd_id)

        start = time.time()
        while time.time() - start < timeout:
            if self.packet_event.wait(timeout=0.1):
                with self.lock:
                    for pkt in self.received_packets:
                        if len(pkt) >= 2 and pkt[0] == cmd_id and pkt[1] == cmd_type:
                            if len(pkt) >= 3:
                                self.device_state = pkt[2]
                            return True
                    self.packet_event.clear()
        return False

    def _read_thread(self):
        """Background thread to read from device."""
        while self.read_active:
            try:
                data = self.dev.read(EP_IN, 64, timeout=100)
                if data:
                    self._process_recv_data(bytes(data))
            except usb.core.USBTimeoutError:
                pass
            except usb.core.USBError:
                if self.read_active:
                    time.sleep(0.1)

    def _process_recv_data(self, data: bytes):
        """Process received USB data and reassemble fragmented packets."""
        if len(data) < 5:
            return

        report_id = data[0]
        frag_size = data[1]
        packet_idx = data[2]
        frag_count = data[3]
        frag_idx = data[4]

        if report_id != 0x01:
            return

        payload_size = frag_size - 3
        if payload_size <= 0 or payload_size > 56:
            return

        payload = data[5:5 + payload_size]

        # Handle fragmentation
        if frag_idx == 1:
            # New packet
            self._recv_buffer = bytearray(payload)
            self._recv_packet_idx = packet_idx
            self._recv_frag_count = frag_count
            self._recv_last_frag = 1
        elif packet_idx == self._recv_packet_idx and frag_idx == self._recv_last_frag + 1:
            # Continue packet
            self._recv_buffer.extend(payload)
            self._recv_last_frag = frag_idx

        # Check if packet complete
        if self._recv_frag_count > 0 and self._recv_last_frag == self._recv_frag_count:
            if len(self._recv_buffer) >= 4:
                start_sig = struct.unpack('<H', self._recv_buffer[0:2])[0]
                end_sig = struct.unpack('<H', self._recv_buffer[-2:])[0]

                if start_sig == PACK_START and end_sig == PACK_END:
                    packet_data = bytes(self._recv_buffer[2:-2])
                    with self.lock:
                        self.received_packets.append(packet_data)
                        self.packet_event.set()

            self._recv_frag_count = 0

    def __enter__(self):
        """Context manager entry."""
        if not self.open():
            raise RuntimeError("Failed to open device")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
