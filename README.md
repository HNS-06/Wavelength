<<<<<<< HEAD
# Wavelength
=======
# Wavelength – Professional Wi‑Fi Analyzer

## Overview
**Wavelength** is a Windows‑only command‑line tool that scans nearby Wi‑Fi networks and provides an in‑depth, green‑themed analysis. It builds on the original `wifi_scanner.py` project and adds:

- **Green UI** – major headings and sections are rendered in bright green (inspired by Claude Code). 
- **Distance estimation** – a simple RSSI‑to‑distance conversion gives an approximate range for each AP. 
- **Local IP address** – the IP of the selected Wi‑Fi interface is shown and included in export files. 
- **Bug fixes** – typo corrections and proper hidden‑network detection.
- **Full export** – JSON and CSV reports now contain `estimated_distance_m` and `ip_address` fields.
- **Renamed script** – the runnable entry point is `wavelength.py`; the original `wifi_scanner.py` remains for reference.

## Requirements
- Windows 10/11 (tested on Windows 11 Home).
- Python 3.8+ installed and added to `PATH`.
- Administrator rights are required to read saved Wi‑Fi passwords.

## Installation
```powershell
# Clone or copy the repository
git clone <repo‑url>  # (or copy the folder manually)
cd wifi-scanner
# Install any needed dependencies (none beyond the Python standard library).
```

## Usage
```powershell
# Full scan with green UI and distance column
python wavelength.py

# Show saved Wi‑Fi profiles (including passwords – run as Administrator)
python wavelength.py --profiles

# Show password for a specific profile
python wavelength.py --password "MyNetwork"

# Live monitoring (default 60 s; press Ctrl+C to stop)
python wavelength.py --live

# Show interface details only
python wavelength.py --interfaces

# Export only (no on‑screen display)
python wavelength.py --export

# Compare two previously exported JSON scan files
python wavelength.py --compare
```

## Features in Detail
- **Green‑themed UI** – headings are wrapped with `\033[92m` (bright green) ANSI codes for better readability.
- **Signal → Distance** – signal strength percentage is converted to dBm and then to an approximate distance (meters) using a free‑space path‑loss model.
- **IP address** – the tool fetches the IPv4 address of the active Wi‑Fi adapter and displays it in the banner and export data.
- **Comprehensive export** – `wifi_analysis_report.json` contains all network data, channel analysis, rogue‑AP alerts, and the interface IP. `wifi_networks.csv` provides a spreadsheet‑friendly view.
- **Rogue AP detection** – lists SSIDs with many BSSIDs (potential rogue access points).
- **Channel analysis** – reports congested and recommended channels for 2.4 GHz and 5 GHz bands.
- **Hidden network detection** – correctly counts networks where the SSID line is empty.

## Development
The code is split into clear sections:
- **Helpers** – command execution, distance estimation, IP retrieval.
- **Parsing** – `parse_wifi_networks` extracts fields from `netsh` output.
- **Analysis** – quality scoring, channel interference, rogue‑AP detection.
- **Display** – green‑themed tables and summaries.
- **Export** – JSON and CSV writers.
- **CLI** – argument handling at the bottom of `wavelength.py`.

Feel free to extend the tool (e.g., add a GUI, integrate with a database, or improve the distance model).
>>>>>>> 0de3ce5 (Initial Commit)
