WiFi Scanner - Windows
======================

A command-line tool to capture complete WiFi network details on Windows.

Features
--------
- Scan all nearby WiFi networks
- Display complete network information:
  - SSID (network name)
  - Signal strength
  - Authentication type
  - Cipher type
  - Channel & Frequency
  - Band (2.4GHz/5GHz)
  - BSSID (MAC addresses)
- View saved WiFi profiles
- Extract saved WiFi passwords (requires admin)
- Export results to JSON

Requirements
------------
- Windows OS
- Python 3.6+
- WiFi adapter
- Administrator privileges (for viewing passwords)

Usage
-----

1. Basic scan (show all nearby networks):
   python wifi_scanner.py

2. View saved profiles:
   python wifi_scanner.py --profiles

3. View password for a specific saved profile:
   python wifi_scanner.py --password "YourWiFiName"

4. Export scan results to JSON:
   python wifi_scanner.py --export

Running as Administrator
------------------------
To view saved WiFi passwords, you must run as Administrator:
- Right-click Command Prompt/PowerShell
- Select "Run as Administrator"
- Navigate to the wifi-scanner folder
- Run: python wifi_scanner.py --profiles

Output
------
The scanner displays:
- All detected WiFi networks with full details
- Signal strength percentage
- Security type (WPA2, WPA3, etc.)
- Network channel and frequency
- Saved network profiles
- Optional: saved passwords

JSON Export
-----------
Results are automatically saved to wifi_scan.json containing:
- Scan timestamp
- All detected networks with BSSIDs
- Saved profile names
