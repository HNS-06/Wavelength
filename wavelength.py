import subprocess
import re
import json
import time
import os
import sys
import math
from datetime import datetime
from collections import defaultdict

# ANSI colour constants for green theme
GREEN = "\033[92m"
RESET = "\033[0m"

def green(text: str) -> str:
    return f"{GREEN}{text}{RESET}"

def run_command(command: str) -> str:
    """Run a Windows command and return its output (as string)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=30,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {e}"

# ---------------------------------------------------------------------------
# Wi‑Fi interface helpers
# ---------------------------------------------------------------------------

def get_wifi_interfaces() -> list:
    """Retrieve Wi‑Fi adapter details using `netsh wlan show interfaces`."""
    output = run_command("netsh wlan show interfaces")
    interfaces = []
    if "There is no wireless interface" in output:
        return interfaces
    interface_blocks = output.split('\r\n\r\n')
    for block in interface_blocks:
        if not block.strip():
            continue
        interface = {}
        name_match = re.search(r'Name\s+:\s+(.+)', block)
        if name_match:
            interface['name'] = name_match.group(1).strip()
        state_match = re.search(r'State\s+:\s+(.+)', block)
        if state_match:
            interface['state'] = state_match.group(1).strip()
        ssid_match = re.search(r'SSID\s+:\s+(.+)', block)
        if ssid_match:
            interface['connected_ssid'] = ssid_match.group(1).strip()
        bssid_match = re.search(r'BSSID\s+:\s+(.+)', block)
        if bssid_match:
            interface['connected_bssid'] = bssid_match.group(1).strip()
        net_type_match = re.search(r'Network type\s+:\s+(.+)', block)
        if net_type_match:
            interface['network_type'] = net_type_match.group(1).strip()
        auth_match = re.search(r'Authentication\s+:\s+(.+)', block)
        if auth_match:
            interface['authentication'] = auth_match.group(1).strip()
        cipher_match = re.search(r'Cipher\s+:\s+(.+)', block)
        if cipher_match:
            interface['cipher'] = cipher_match.group(1).strip()
        mode_match = re.search(r'Connection mode\s+:\s+(.+)', block)
        if mode_match:
            interface['connection_mode'] = mode_match.group(1).strip()
        channel_match = re.search(r'Channel\s+:\s+(\d+)', block)
        if channel_match:
            interface['channel'] = int(channel_match.group(1))
        signal_match = re.search(r'Signal\s+:\s+(\d+)%', block)
        if signal_match:
            interface['signal'] = int(signal_match.group(1))
        radio_match = re.search(r'Radio type\s+:\s+(.+)', block)
        if radio_match:
            interface['radio_type'] = radio_match.group(1).strip()
        if interface.get('name'):
            interfaces.append(interface)
    return interfaces

def get_interface_ip(interface_name: str) -> str:
    """Return the IPv4 address of the given Wi‑Fi interface (or None)."""
    if not interface_name:
        return None
    output = run_command(f'netsh interface ip show addresses name="{interface_name}"')
    ip_match = re.search(r'IP Address\s*:([^\r\n]+)', output)
    if ip_match:
        return ip_match.group(1).strip()
    return None

# ---------------------------------------------------------------------------
# Scanning utilities
# ---------------------------------------------------------------------------

def scan_networks(interface_name: str = None) -> str:
    """Run `netsh wlan show networks` (optionally limited to a specific interface)."""
    if interface_name:
        command = f"netsh wlan show networks interface=\"{interface_name}\" mode=Bssid"
    else:
        command = "netsh wlan show networks mode=Bssid"
    return run_command(command)

def parse_wifi_networks(output: str) -> list:
    """Parse raw `netsh` output into a list of dictionaries."""
    networks = []
    # Split at each SSID block
    network_blocks = re.split(r'(?=SSID \d+ :)', output)
    for block in network_blocks:
        if not block.strip() or "There is no wireless interface" in block:
            continue
        network = {}
        ssid_match = re.search(r'SSID \d+ : (.+)', block)
        if ssid_match:
            network['ssid'] = ssid_match.group(1).strip()
        else:
            # hidden network – SSID line exists but empty after colon
            hidden_match = re.search(r'SSID \d+ :\s*$', block, re.MULTILINE)
            if hidden_match:
                network['ssid'] = '<hidden>'
            else:
                continue
        net_type_match = re.search(r'Network type\s+:\s+(.+)', block)
        if net_type_match:
            network['network_type'] = net_type_match.group(1).strip()
        auth_match = re.search(r'Authentication\s+:\s+(.+)', block)
        if auth_match:
            network['authentication'] = auth_match.group(1).strip()
        cipher_match = re.search(r'Cipher\s+:\s+(.+)', block)
        if cipher_match:
            network['cipher'] = cipher_match.group(1).strip()
        signal_match = re.search(r'Signal\s+:\s+(\d+)%', block)
        if signal_match:
            signal = int(signal_match.group(1))
            network['signal_strength'] = signal
            # distance estimation (simple RSSI → distance)
            freq = network.get('frequency_mhz')
            if freq:
                network['estimated_distance_m'] = estimate_distance(signal, freq)
            else:
                network['estimated_distance_m'] = None
        channel_match = re.search(r'Channel\s+:\s+(\d+)', block)
        if channel_match:
            network['channel'] = int(channel_match.group(1))
        band_match = re.search(r'Band\s+:\s+(.+)', block)
        if band_match:
            network['band'] = band_match.group(1).strip()
        freq_match = re.search(r'Frequency\s+:\s+(\d+)', block)
        if freq_match:
            network['frequency_mhz'] = int(freq_match.group(1))
        bssid_matches = re.findall(r'BSSID \d+ : ([0-9A-Fa-f:]+)', block)
        if bssid_matches:
            network['bssids'] = bssid_matches
        mac_rand_match = re.search(r'MAC randomization\s+:\s+(.+)', block)
        if mac_rand_match:
            network['mac_randomization'] = mac_rand_match.group(1).strip()
        network['saved'] = False
        network['first_seen'] = datetime.now().isoformat()
        networks.append(network)
    return networks

def estimate_distance(signal_percent: int, freq_mhz: int) -> float:
    """Simple RSSI‑to‑distance conversion.
    Assumes Tx power ≈ ‑30 dBm at 1 m. Converts percent → dBm then
    applies free‑space path loss formula.
    Returns distance in meters, rounded to two decimals.
    """
    # Approximate dBm from signal percent (linear approx)
    dBm = -100 + 0.7 * signal_percent  # -100 dBm at 0 %, -30 dBm at 100 %
    # Free‑space path loss distance calculation (simplified)
    # distance = 10 ** ((TxPower - dBm) / (20))
    try:
        distance = 10 ** ((-30 - dBm) / 20)
        return round(distance, 2)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Hidden network detection
# ---------------------------------------------------------------------------

def detect_hidden_networks(output: str) -> int:
    """Count hidden networks (SSID line present but no name)."""
    count = 0
    for line in output.splitlines():
        if re.match(r'SSID \d+ :\s*$', line):
            count += 1
    return count

# ---------------------------------------------------------------------------
# Quality and analysis helpers
# ---------------------------------------------------------------------------

def calculate_network_quality(network: dict) -> int:
    """Calculate a 0‑100 quality score for a network."""
    score = 0
    signal = network.get('signal_strength', 0)
    if signal >= 80:
        score += 40
    elif signal >= 60:
        score += 30
    elif signal >= 40:
        score += 20
    elif signal >= 20:
        score += 10
    auth = network.get('authentication', '')
    if 'WPA3' in auth:
        score += 30
    elif 'WPA2' in auth:
        score += 25
    elif 'WPA' in auth:
        score += 15
    elif auth == 'Open':
        score += 5
    cipher = network.get('cipher', '')
    if 'CCMP' in cipher or 'AES' in cipher:
        score += 20
    elif 'TKIP' in cipher:
        score += 10
    band = network.get('band', '')
    if '5' in str(band):
        score += 10
    return min(score, 100)

def analyze_channel_interference(networks: list) -> dict:
    """Analyse channel congestion for 2.4 GHz and 5 GHz bands."""
    channel_usage = defaultdict(list)
    for net in networks:
        ch = net.get('channel', 0)
        if ch > 0:
            channel_usage[ch].append(net)
    analysis = {
        '2.4GHz': {'congested_channels': [], 'best_channels': [], 'total_networks': 0},
        '5GHz': {'congested_channels': [], 'best_channels': [], 'total_networks': 0},
    }
    for ch, nets in channel_usage.items():
        band = '2.4GHz' if ch <= 14 else '5GHz'
        analysis[band]['total_networks'] += len(nets)
        if len(nets) >= 5:
            analysis[band]['congested_channels'].append(ch)
        elif len(nets) <= 2:
            analysis[band]['best_channels'].append(ch)
    # Recommended channels (standard non‑overlapping sets)
    analysis['2.4GHz']['recommended'] = [c for c in [1, 6, 11] if c not in analysis['2.4GHz']['congested_channels']][:3]
    analysis['5GHz']['recommended'] = [c for c in range(36, 166, 4) if c not in analysis['5GHz']['congested_channels']][:5]
    return analysis

def detect_rogue_access_points(networks: list) -> list:
    """Identify potential rogue APs (same SSID, many BSSIDs)."""
    ssid_groups = defaultdict(list)
    for net in networks:
        ssid = net.get('ssid', '')
        bssids = net.get('bssids', [])
        if ssid and bssids:
            ssid_groups[ssid].extend(bssids)
    alerts = []
    for ssid, bssids in ssid_groups.items():
        uniq = list(set(bssids))
        if len(uniq) > 3:
            alerts.append({
                'ssid': ssid,
                'bssid_count': len(uniq),
                'bssids': uniq,
                'risk': 'high' if len(uniq) > 5 else 'medium',
            })
    return alerts

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_networks_detailed(networks: list, interface_info: dict = None, show_distance: bool = True) -> None:
    print("\n" + "=" * 100)
    print(green(f"{'PROFESSIONAL WiFi ANALYZER - ALL NEARBY NETWORKS':^100}"))
    print(green(f"{'Scan Time: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^100}"))
    print("=" * 100 + "\n")
    if interface_info:
        ip_addr = interface_info.get('ip_address')
        print(green("Interface:") + f" {interface_info.get('name', 'N/A')}")
        print(green("Status:" ) + f" {interface_info.get('state', 'N/A')}")
        if interface_info.get('connected_ssid'):
            print(green("Connected:" ) + f" {interface_info['connected_ssid']}")
        print(green("IP Address:" ) + f" {ip_addr or 'N/A'}")
        print()
    if not networks:
        print("⚠ No WiFi networks detected")
        print("\nTroubleshooting:")
        print("  • Ensure WiFi adapter is enabled")
        print("  • Run as Administrator for full data")
        print("  • Check airplane mode")
        return
    # Summary
    open_nets = [n for n in networks if n.get('authentication') == 'Open']
    wpa3_nets = [n for n in networks if 'WPA3' in n.get('authentication', '')]
    wpa2_nets = [n for n in networks if 'WPA2' in n.get('authentication', '')]
    hidden_cnt = detect_hidden_networks('')  # placeholder – will be updated later
    print(green("Network Summary:"))
    print(f"   Total Networks: {len(networks)}")
    print(f"   Open (No Password): {len(open_nets)}")
    print(f"   WPA3 Secured: {len(wpa3_nets)}")
    print(f"   WPA2 Secured: {len(wpa2_nets)}")
    # Header line – add distance column if enabled
    header_cols = ["#", "SSID", "Signal", "Security", "Band", "Ch"]
    if show_distance:
        header_cols.append("Dist (m)")
    header_cols.extend(["Quality", "Status"])
    fmt = "{:<3} {:<30} {:<12} {:<20} {:<8} {:<4}"
    if show_distance:
        fmt += " {:<10}"
    fmt += " {:<8} {:<10}"
    print(green("-" * 100))
    print(fmt.format(*header_cols))
    print(green("-" * 100))
    sorted_nets = sorted(networks, key=lambda x: x.get('signal_strength', 0), reverse=True)
    for i, net in enumerate(sorted_nets, 1):
        ssid = net.get('ssid', 'Hidden')[:28]
        signal = net.get('signal_strength', 0)
        signal_bar = "█" * (signal // 10)
        signal_str = f"{signal_bar} {signal}%"
        security = net.get('authentication', 'Unknown')[:18]
        band = net.get('band', 'N/A')[:6]
        channel = str(net.get('channel', 'N/A'))
        quality = f"{calculate_network_quality(net)}/100"
        status = "SAVED" if net.get('saved') else "-"
        row = [i, ssid, signal_str, security, band, channel]
        if show_distance:
            dist = net.get('estimated_distance_m')
            dist_str = f"{dist:.2f}m" if isinstance(dist, (int, float)) else "N/A"
            row.append(dist_str)
        row.extend([quality, status])
        print(fmt.format(*row))
    print(green("-" * 100))
    # Channel analysis
    analysis = analyze_channel_interference(networks)
    print(green("\nChannel Analysis:"))
    print(f"   2.4GHz Networks: {analysis['2.4GHz']['total_networks']}")
    if analysis['2.4GHz']['congested_channels']:
        print(f"   Congested Channels: {analysis['2.4GHz']['congested_channels']}")
    if analysis['2.4GHz']['recommended']:
        print(f"   Recommended (2.4GHz): {analysis['2.4GHz']['recommended']}")
    print(f"   5GHz Networks: {analysis['5GHz']['total_networks']}")
    if analysis['5GHz']['congested_channels']:
        print(f"   Congested Channels: {analysis['5GHz']['congested_channels']}")
    if analysis['5GHz']['recommended']:
        print(f"   Recommended (5GHz): {analysis['5GHz']['recommended']}")
    # Rogue AP alerts
    rogue_alerts = detect_rogue_access_points(networks)
    if rogue_alerts:
        print(green("\n⚠️  Rogue AP Detection:"))
        for alert in rogue_alerts:
            icon = "🔴" if alert['risk'] == 'high' else "🟠"
            print(f"   {icon} {alert['ssid']}: {alert['bssid_count']} BSSIDs ({alert['risk']} risk)")
    print("\n" + "=" * 100)

def display_network_details(network: dict) -> None:
    print("\n" + "=" * 80)
    print(green(f"Network: {network.get('ssid', 'Unknown')}") )
    print("=" * 80)
    print(f"  SSID:             {network.get('ssid', 'Hidden')}")
    print(f"  Network Type:     {network.get('network_type', 'Infrastructure')}")
    print(f"  Authentication:   {network.get('authentication', 'Unknown')}")
    print(f"  Cipher:           {network.get('cipher', 'Unknown')}")
    print(f"  Signal Strength:  {network.get('signal_strength', 'N/A')}%")
    print(f"  Quality Score:    {calculate_network_quality(network)}/100")
    if 'band' in network:
        print(f"  Band:             {network['band']}")
    if 'channel' in network:
        print(f"  Channel:          {network['channel']}")
    if 'frequency_mhz' in network:
        print(f"  Frequency:        {network['frequency_mhz']} MHz")
    if 'estimated_distance_m' in network:
        print(f"  Estimated Dist:   {network['estimated_distance_m']} m")
    if 'bssids' in network:
        print("  BSSID(s):")
        for b in network['bssids']:
            print(f"    - {b}")
    if 'mac_randomization' in network:
        print(f"  MAC Randomization:{network['mac_randomization']}")
    print(f"  Saved:            {'Yes' if network.get('saved') else 'No'}")
    print(f"  First Detected:   {network.get('first_seen', 'N/A')}")
    print("=" * 80 + "\n")

def display_saved_profiles(profiles: list) -> None:
    print("\n" + "=" * 80)
    print(green(f"{'SAVED WIFI PROFILES WITH PASSWORDS':^80}"))
    print("=" * 80 + "\n")
    if not profiles:
        print("No saved WiFi profiles found.")
        return
    for i, profile in enumerate(profiles, 1):
        details = get_profile_details(profile)
        print(f"[{i}] {profile}")
        print("-" * 80)
        print(f"    SSID:           {details.get('ssid', 'N/A')}")
        print(f"    Authentication: {details.get('authentication', 'N/A')}")
        print(f"    Cipher:         {details.get('cipher', 'N/A')}")
        if 'password' in details:
            print(f"    🔑 Password:    {details['password']}")
        else:
            print("    Password:       Requires Administrator privileges")
        if 'cost' in details:
            print(f"    Cost Profile:   {details['cost']}")
        print()
    print("=" * 80)

# ---------------------------------------------------------------------------
# Live monitor
# ---------------------------------------------------------------------------

def live_monitor(interface_name: str = None, duration: int = 60) -> None:
    print("\n" + "=" * 80)
    print(green("LIVE WiFi MONITOR"))
    print("=" * 80)
    print(f"Duration: {duration} seconds (Ctrl+C to stop)\n")
    start = time.time()
    scan_count = 0
    signal_history = defaultdict(list)
    try:
        while time.time() - start < duration:
            scan_count += 1
            elapsed = int(time.time() - start)
            raw = scan_networks(interface_name)
            nets = parse_wifi_networks(raw)
            print(f"\n{'='*60}\nScan #{scan_count} | {elapsed}s elapsed | {datetime.now().strftime('%H:%M:%S')}\n{'='*60}")
            if nets:
                top = sorted(nets, key=lambda x: x.get('signal_strength', 0), reverse=True)[:8]
                for net in top:
                    ssid = net.get('ssid', 'Hidden')[:25]
                    signal = net.get('signal_strength', 0)
                    bar = "█" * (signal // 10)
                    signal_history[ssid].append(signal)
                    print(f"  {ssid:<26} {bar} {signal}%")
            else:
                print("  No networks detected")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    if signal_history:
        print("\n📈 Signal Trend Summary:")
        for ssid, sigs in signal_history.items():
            if len(sigs) > 1:
                avg = sum(sigs) / len(sigs)
                print(f"  {ssid[:25]:<25} Avg={avg:.0f}% Min={min(sigs)}% Max={max(sigs)}%")

# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def export_comprehensive_report(networks: list, profiles: list, interface_info: dict, filename: str = "wifi_analysis_report.json") -> str:
    channel_analysis = analyze_channel_interference(networks)
    rogue_aps = detect_rogue_access_points(networks)
    report = {
        'report_generated': datetime.now().isoformat(),
        'interface': interface_info,
        'summary': {
            'total_networks': len(networks),
            'open_networks': len([n for n in networks if n.get('authentication') == 'Open']),
            'wpa2_networks': len([n for n in networks if 'WPA2' in n.get('authentication', '')]),
            'wpa3_networks': len([n for n in networks if 'WPA3' in n.get('authentication', '')]),
            'saved_profiles': len(profiles),
        },
        'channel_analysis': channel_analysis,
        'rogue_ap_alerts': rogue_aps,
        'networks': networks,
        'saved_profiles': profiles,
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(green(f"✅ Comprehensive report exported to: {filename}"))
    return filename

def export_csv(networks: list, filename: str = "wifi_networks.csv") -> None:
    import csv
    if not networks:
        print("No networks to export")
        return
    fieldnames = [
        'ssid', 'network_type', 'authentication', 'cipher',
        'signal_strength', 'channel', 'band', 'frequency_mhz',
        'bssids', 'saved', 'quality_score', 'first_seen', 'estimated_distance_m'
    ]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for net in networks:
            row = net.copy()
            row['bssids'] = ';'.join(net.get('bssids', []))
            row['quality_score'] = calculate_network_quality(net)
            writer.writerow(row)
    print(green(f"✅ CSV exported to: {filename}"))

# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

def get_saved_profiles() -> list:
    output = run_command("netsh wlan show profiles")
    profiles = []
    matches = re.findall(r'All User Profile\s+:\s+(.+)', output)
    for p in matches:
        profiles.append(p.strip())
    return profiles

def get_profile_details(profile_name: str) -> dict:
    cmd = f'netsh wlan show profile name="{profile_name}" key=clear'
    output = run_command(cmd)
    details = {'profile_name': profile_name}
    ssid_match = re.search(r'SSID name\s+:\s+(.+)', output)
    if ssid_match:
        details['ssid'] = ssid_match.group(1).strip()
    auth_match = re.search(r'Authentication\s+:\s+(.+)', output)
    if auth_match:
        details['authentication'] = auth_match.group(1).strip()
    cipher_match = re.search(r'Cipher\s+:\s+(.+)', output)
    if cipher_match:
        details['cipher'] = cipher_match.group(1).strip()
    key_match = re.search(r'Key Content\s+:\s+(.+)', output)
    if key_match:
        details['password'] = key_match.group(1).strip()
    cost_match = re.search(r'Cost\s+:\s+(.+)', output)
    if cost_match:
        details['cost'] = cost_match.group(1).strip()
    return details

# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 100)
    print(green(f"{'🔍 WAVELENGTH – PROFESSIONAL WIFI ANALYZER':^100}"))
    print(green(f"{'Advanced Network Discovery & Analysis Tool':^100}"))
    print("=" * 100)
    interfaces = get_wifi_interfaces()
    if not interfaces:
        print(green("\n❌ No WiFi interfaces found on this system."))
        print("\nTroubleshooting:")
        print("  1. Ensure WiFi adapter is installed and enabled")
        print("  2. Check Device Manager for adapter status")
        print("  3. Disable Airplane Mode")
        print("  4. Run as Administrator")
        return
    interface_info = interfaces[0]
    # Grab the IP address for the selected interface
    interface_info['ip_address'] = get_interface_ip(interface_info.get('name'))
    print(green(f"\n✅ WiFi Interface: {interface_info.get('name', 'N/A')}"))
    print(green(f"   Status: {interface_info.get('state', 'N/A')}"))
    if interface_info.get('connected_ssid'):
        print(green(f"   Connected: {interface_info['connected_ssid']}"))
    print(green(f"   IP Address: {interface_info.get('ip_address') or 'N/A'}"))
    print("\n🔎 Scanning for ALL nearby networks...\n")
    raw_output = scan_networks(interface_info.get('name'))
    networks = parse_wifi_networks(raw_output)
    saved_profiles = get_saved_profiles()
    for net in networks:
        if net.get('ssid') in saved_profiles:
            net['saved'] = True
    # Show detailed view with distance column (user requested it)
    display_networks_detailed(networks, interface_info, show_distance=True)
    print(green("\n💾 Export Options:"))
    print("  • JSON report: Comprehensive analysis")
    print("  • CSV: Spreadsheet‑compatible data")
    if networks:
        export_comprehensive_report(networks, saved_profiles, interface_info)
        export_csv(networks)
    print("\n" + "=" * 100)
    print(green("COMMAND REFERENCE:"))
    print("=" * 100)
    print(green("  python wavelength.py               - Full scan with analysis"))
    print(green("  python wavelength.py --profiles    - Show saved networks with passwords"))
    print(green("  python wavelength.py --password \"Name\" - Show specific profile password"))
    print(green("  python wavelength.py --live        - Live monitoring (60s)"))
    print(green("  python wavelength.py --interfaces - Show interface details"))
    print(green("  python wavelength.py --export     - Export only (no display)"))
    print(green("  python wavelength.py --compare    - Compare two scan files"))
    print("=" * 100 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--password" and len(sys.argv) > 2:
            profile = " ".join(sys.argv[2:])
            details = get_profile_details(profile)
            print(green(f"\nProfile: {profile}"))
            print(green(f"  Password: {details.get('password', 'Not available')}"))
        elif arg == "--profiles":
            profiles = get_saved_profiles()
            display_saved_profiles(profiles)
        elif arg == "--live":
            duration = 60
            if len(sys.argv) > 2:
                try:
                    duration = int(sys.argv[2])
                except:
                    pass
            iface = interface_info.get('name') if 'interface_info' in locals() else None
            live_monitor(iface, duration)
        elif arg == "--interfaces":
            show_interface_details()
        elif arg == "--export":
            iface = interface_info.get('name') if 'interface_info' in locals() else None
            raw = scan_networks(iface)
            nets = parse_wifi_networks(raw)
            profs = get_saved_profiles()
            export_comprehensive_report(nets, profs, interface_info)
            export_csv(nets)
        elif arg == "--compare":
            compare_scans()
        else:
            main()
    else:
        main()
