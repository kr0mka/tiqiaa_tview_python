"""
Tiqiaa TView USB IR Transceiver - IR Code Storage

This module handles saving and loading IR codes to/from JSON files.
"""

import json
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any

# Default codes directory (relative to this file or CWD)
DEFAULT_CODES_DIR = Path("ir_codes")


def get_codes_dir(codes_dir: Optional[Path] = None) -> Path:
    """
    Get the IR codes directory, creating it if necessary.

    Args:
        codes_dir: Optional custom directory path

    Returns:
        Path to the codes directory
    """
    path = codes_dir or DEFAULT_CODES_DIR
    path.mkdir(exist_ok=True)
    return path


def save_ir_code(
    name: str,
    ir_data: bytes,
    freq: int = 38000,
    codes_dir: Optional[Path] = None,
    learned_from: Optional[str] = None,
    notes: Optional[str] = None,
    tap_data: Optional[bytes] = None
) -> Path:
    """
    Save IR code to a JSON file.

    Args:
        name: Code name (used as filename)
        ir_data: Raw IR signal data
        freq: IR carrier frequency in Hz
        codes_dir: Optional custom directory
        learned_from: Optional source description (e.g., "Samsung TV Remote")
        notes: Optional notes about the code
        tap_data: Optional separate data for tap (short press) behavior

    Returns:
        Path to the saved file

    Example:
        >>> path = save_ir_code("power", b'\\x8f\\x7f...', learned_from="My TV Remote")
    """
    directory = get_codes_dir(codes_dir)
    filepath = directory / f"{name}.ir"

    data: Dict[str, Any] = {
        "name": name,
        "frequency": freq,
        "data": list(ir_data)
    }

    if tap_data is not None:
        data["tap"] = list(tap_data)

    if learned_from:
        data["learned_from"] = learned_from

    if notes:
        data["notes"] = notes

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    return filepath


def load_ir_code(
    name: str,
    codes_dir: Optional[Path] = None
) -> Tuple[Optional[bytes], int]:
    """
    Load IR code from file.

    Args:
        name: Code name (filename without extension)
        codes_dir: Optional custom directory

    Returns:
        Tuple of (ir_data, frequency) or (None, 38000) if not found

    Example:
        >>> data, freq = load_ir_code("power")
        >>> if data:
        ...     print(f"Loaded {len(data)} bytes at {freq}Hz")
    """
    directory = get_codes_dir(codes_dir)
    filepath = directory / f"{name}.ir"

    if not filepath.exists():
        return None, 38000

    with open(filepath, 'r') as f:
        data = json.load(f)

    ir_data = bytes(data["data"])
    freq = data.get("frequency", 38000)

    return ir_data, freq


def load_ir_code_full(
    name: str,
    codes_dir: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Load full IR code data including metadata.

    Args:
        name: Code name
        codes_dir: Optional custom directory

    Returns:
        Dictionary with all code data, or None if not found
    """
    directory = get_codes_dir(codes_dir)
    filepath = directory / f"{name}.ir"

    if not filepath.exists():
        return None

    with open(filepath, 'r') as f:
        data = json.load(f)

    # Convert data arrays to bytes
    data["data"] = bytes(data["data"])
    if "tap" in data:
        data["tap"] = bytes(data["tap"])

    return data


def load_smart_code(
    name: str,
    codes_dir: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Load IR code with tap/full variants for smart sending.

    This supports the tap-and-hold pattern where:
    - Tap (short press): sends tap code (or data if no tap field)
    - Hold: sends full data code repeatedly

    Args:
        name: Code name
        codes_dir: Optional custom directory

    Returns:
        Dictionary with 'tap', 'full', and 'freq' keys, or None
    """
    directory = get_codes_dir(codes_dir)
    filepath = directory / f"{name}.ir"

    if not filepath.exists():
        return None

    with open(filepath, 'r') as f:
        data = json.load(f)

    # Tap code - use 'tap' field or 'data'
    tap_data = data.get('tap', data['data'])
    tap_code = bytes(tap_data)

    # Full code for hold mode
    full_code = None

    # Check if data field is full-length NEC (~80-120 bytes)
    data_field = data.get('data', [])
    if 80 <= len(data_field) <= 120:
        full_code = bytes(data_field)

    # Check for a "_full" variant file
    if full_code is None:
        full_filepath = directory / f"{name}_full.ir"
        if full_filepath.exists():
            with open(full_filepath, 'r') as f:
                full_data = json.load(f)
            full_code = bytes(full_data.get('data', []))

    # Fallback to tap code
    if full_code is None:
        full_code = tap_code

    return {
        'tap': tap_code,
        'full': full_code,
        'freq': data.get('frequency', 38000)
    }


def list_ir_codes(codes_dir: Optional[Path] = None) -> List[str]:
    """
    List all saved IR code names.

    Args:
        codes_dir: Optional custom directory

    Returns:
        List of code names (without .ir extension)

    Example:
        >>> codes = list_ir_codes()
        >>> for name in codes:
        ...     print(f"  - {name}")
    """
    directory = get_codes_dir(codes_dir)

    if not directory.exists():
        return []

    return sorted([f.stem for f in directory.glob("*.ir")])


def delete_ir_code(name: str, codes_dir: Optional[Path] = None) -> bool:
    """
    Delete a saved IR code.

    Args:
        name: Code name to delete
        codes_dir: Optional custom directory

    Returns:
        True if deleted, False if not found
    """
    directory = get_codes_dir(codes_dir)
    filepath = directory / f"{name}.ir"

    if filepath.exists():
        filepath.unlink()
        return True
    return False


def export_codes(
    output_file: Path,
    codes_dir: Optional[Path] = None,
    names: Optional[List[str]] = None
) -> int:
    """
    Export multiple IR codes to a single JSON file.

    Args:
        output_file: Output file path
        codes_dir: Optional codes directory
        names: Optional list of specific codes to export (all if None)

    Returns:
        Number of codes exported
    """
    directory = get_codes_dir(codes_dir)

    if names is None:
        names = list_ir_codes(codes_dir)

    codes = {}
    for name in names:
        filepath = directory / f"{name}.ir"
        if filepath.exists():
            with open(filepath, 'r') as f:
                codes[name] = json.load(f)

    with open(output_file, 'w') as f:
        json.dump({"ir_codes": codes, "version": 1}, f, indent=2)

    return len(codes)


def import_codes(
    input_file: Path,
    codes_dir: Optional[Path] = None,
    overwrite: bool = False
) -> int:
    """
    Import IR codes from an export file.

    Args:
        input_file: Input file path
        codes_dir: Optional codes directory
        overwrite: Whether to overwrite existing codes

    Returns:
        Number of codes imported
    """
    directory = get_codes_dir(codes_dir)

    with open(input_file, 'r') as f:
        data = json.load(f)

    codes = data.get("ir_codes", data)  # Support old format without wrapper
    if not isinstance(codes, dict):
        return 0

    imported = 0
    for name, code_data in codes.items():
        filepath = directory / f"{name}.ir"
        if filepath.exists() and not overwrite:
            continue

        with open(filepath, 'w') as f:
            json.dump(code_data, f, indent=2)
        imported += 1

    return imported
