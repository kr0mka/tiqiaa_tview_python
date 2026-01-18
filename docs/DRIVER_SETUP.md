# Driver Setup Guide

This guide explains how to install the WinUSB driver for the Tview USB IR dongle on Windows.

## Why is This Needed?

Windows automatically installs a generic HID driver for this device, which doesn't work with Python/libusb. We need to replace it with the WinUSB driver.

## Requirements

- Windows 10/11
- Administrator privileges
- [Zadig](https://zadig.akeo.ie/) - Driver installation tool

## Step-by-Step Instructions

### 1. Download Zadig

1. Go to [https://zadig.akeo.ie/](https://zadig.akeo.ie/)
2. Download the latest version (zadig-X.X.exe)
3. No installation needed - it's a portable tool

### 2. Connect the Dongle

1. Plug in your Tview USB IR dongle
2. Windows might try to install drivers - let it finish
3. Wait a few seconds for the device to be recognized

### 3. Run Zadig

1. Right-click zadig.exe → **Run as administrator**
2. Click **Yes** if prompted by UAC

### 4. Configure Zadig

1. Go to **Options** menu
2. Check **List All Devices**
3. This shows all USB devices, not just driverless ones

### 5. Select the Device

From the dropdown, find your device:

- Look for **"Tview"**
- Or look for USB ID: **10C4:8468**

**Warning:** Make sure you select the correct device! Selecting the wrong device could make other hardware stop working.

### 6. Select WinUSB Driver

1. In the **Driver** row, you should see:
   - Current driver on the left (probably HidUsb or something similar)
   - Target driver on the right
2. Use the arrows to select **WinUSB** as the target

### 7. Replace Driver

1. Click **Replace Driver**
2. Wait for the process to complete
3. You should see **"Driver Installation Successful"**

### 8. Verify Installation

Open a command prompt or PowerShell and run:

```powershell
python -c "from tiqiaa import TiqiaaIR; ir = TiqiaaIR(); print('Success!' if ir.open() else 'Failed')"
```

If you see "Success!", the driver is working correctly.

## Reverting to Original Driver

If you need to use the original Windows application:

### Method 1: Device Manager

1. Open Device Manager (Win+X → Device Manager)
2. Find "Tview" under "Universal Serial Bus devices"
3. Right-click → **Update driver**
4. Click **Search automatically for drivers**
5. Windows should restore the original driver

### Method 2: Complete Removal

1. Open Device Manager
2. Right-click the device → **Uninstall device**
3. Check **"Delete the driver software for this device"**
4. Unplug and replug the dongle
5. Windows will reinstall the original driver

## Linux Setup

On Linux, you don't need Zadig. Instead, add a udev rule:

```bash
# Create udev rule
sudo tee /etc/udev/rules.d/99-tview.rules << EOF
SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", ATTR{idProduct}=="8468", MODE="0666", GROUP="plugdev"
EOF

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Add yourself to plugdev group (if needed)
sudo usermod -aG plugdev $USER
```

Log out and back in for group changes to take effect.

## macOS Setup

On macOS, no special driver setup is needed. Just install libusb:

```bash
brew install libusb
```

## Device Information

| Property | Value |
|----------|-------|
| Vendor ID (VID) | 0x10C4 (Silicon Labs) |
| Product ID (PID) | 0x8468 |
| Device Name | Tview |
| USB Class | HID (originally) |
