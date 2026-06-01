import subprocess
import re
import json
import time
import os
import sys
from datetime import datetime
from collections import defaultdict


def run_command(command):
    """Run a Windows command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=30
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {e}"


def get_wifi_interfaces():
    """Get available WiFi interfaces with detailed info."""
    output = run_command("netsh wlan show interfaces")
    interfaces = []
    
    if "There is no wireless interface on the system" in output:
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
        
        network_type_match = re.search(r'Network type\s+:\s+(.+)', block)
        if network_type_match:
            interface['network_type'] = network_type_match.group(1).strip()
        
        auth_match = re.search(r'Authentication\s+:\s+(.+)', block)
        if auth_match:
            interface['authentication'] = auth_match.group(1).strip()
        
        cipher_match = re.search(r'Cipher\s+:\s+(.+)', block)
        if cipher_match:
            interface['cipher'] = cipher_match.group(1).strip()
        
        connection_mode_match = re.search(r'Connection mode\s+:\s+(.+)', block)
        if connection_mode_match:
            interface['connection_mode'] = connection_mode_match.group(1).strip()
        
        channel_match = re.search(r'Channel\s+:\s+(\d+)', block)
        if channel_match:
            interface['channel'] = int(channel_match.group(1))
        
        signal_match = re.search(r'Signal\s+:\s+(\d+)%', block)
        if signal_match:
            interface['signal'] = int(signal_match.group(1))
        
        radio_type_match = re.search(r'Radio type\s+:\s+(.+)', block)
        if radio_type_match:
            interface['radio_type'] = radio_type_match.group(1).strip()
        
        if interface.get('name'):
            interfaces.append(interface)
    
    return interfaces


def scan_networks(interface_name=None):
    """Scan for available WiFi networks."""
    if interface_name:
        command = f"netsh wlan show networks interface=\"{interface_name}\" mode=Bssid"
    else:
        command = "netsh wlan show networks mode=Bssid"
    
    output = run_command(command)
    return output


def parse_wifi_networks(output):
    """Parse the netsh output to extract WiFi network details."""
    networks = []
    
    network_blocks = re.split(r'(?=SSID \d+ :)', output)
    
    for block in network_blocks:
        if not block.strip() or "There is no wireless interface" in block:
            continue
        
        network = {}
        
        ssid_match = re.search(r'SSID \d+ : (.+)', block)
        if ssid_match:
            network['ssid'] = ssid_match.group(1).strip()
        else:
            continue
        
        network_match = re.search(r'Network type\s+:\s+(.+)', block)
        if network_match:
            network['network_type'] = network_match.group(1).strip()
        
        authentication_match = re.search(r'Authentication\s+:\s+(.+)', block)
        if authentication_match:
            network['authentication'] = authentication_match.group(1).strip()
        
        cipher_match = re.search(r'Cipher\s+:\s+(.+)', block)
        if cipher_match:
            network['cipher'] = cipher_match.group(1).strip()
        
        signal_match = re.search(r'Signal\s+:\s+(\d+)%', block)
        if signal_match:
            network['signal_strength'] = int(signal_match.group(1))
        
        channel_match = re.search(r'Channel\s+:\s+(\d+)', block)
        if channel_match:
            network['channel'] = int(channel_match.group(1))
        
        bssid_matches = re.findall(r'BSSID \d+ : ([0-9A-Fa-f:]+)', block)
        if bssid_matches:
            network['bssids'] = bssids_matches
        
        band_match = re.search(r'Band\s+:\s+(.+)', block)
        if band_match:
            network['band'] = band_match.group(1).strip()
        
        frequency_match = re.search(r'Frequency\s+:\s+(\d+)', block)
        if frequency_match:
            network['frequency_mhz'] = int(frequency_match.group(1))
        
        mac_randomization_match = re.search(r'MAC randomization\s+:\s+(.+)', block)
        if mac_randomization_match:
            network['mac_randomization'] = mac_randomization_match.group(1).strip()
        
        network['saved'] = False
        network['first_seen'] = datetime.now().isoformat()
        
        networks.append(network)
    
    return networks


def get_saved_profiles():
    """Get saved WiFi profiles."""
    output = run_command("netsh wlan show profiles")
    profiles = []
    
    profile_matches = re.findall(r'All User Profile\s+:\s+(.+)', output)
    for profile in profile_matches:
        profiles.append(profile.strip())
    
    return profiles


def get_profile_details(profile_name):
    """Get detailed information about a saved WiFi profile."""
    command = f"netsh wlan show profile name=\"{profile_name}\" key=clear"
    output = run_command(command)
    
    details = {}
    details['profile_name'] = profile_name
    
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


def calculate_network_quality(network):
    """Calculate network quality score (0-100)."""
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


def analyze_channel_interference(networks):
    """Analyze WiFi channel interference and congestion."""
    channel_usage = defaultdict(list)
    
    for network in networks:
        channel = network.get('channel', 0)
        if channel > 0:
            channel_usage[channel].append(network)
    
    analysis = {
        '2.4GHz': {'congested_channels': [], 'best_channels': [], 'total_networks': 0},
        '5GHz': {'congested_channels': [], 'best_channels': [], 'total_networks': 0}
    }
    
    for channel, nets in channel_usage.items():
        band = '2.4GHz' if channel <= 14 else '5GHz'
        analysis[band]['total_networks'] += len(nets)
        
        if len(nets) >= 5:
            analysis[band]['congested_channels'].append(channel)
        elif len(nets) <= 2:
            analysis[band]['best_channels'].append(channel)
    
    recommended_24 = [ch for ch in [1, 6, 11] if ch not in analysis['2.4GHz']['congested_channels']]
    recommended_5 = [ch for ch in range(36, 166, 4) if ch not in analysis['5GHz']['congested_channels']][:5]
    
    analysis['2.4GHz']['recommended'] = recommended_24[:3]
    analysis['5GHz']['recommended'] = recommended_5
    
    return analysis


def detect_rogue_access_points(networks):
    """Detect potential rogue access points (same SSID, different BSSID)."""
    ssid_groups = defaultdict(list)
    
    for network in networks:
        ssid = network.get('ssid', '')
        bssids = network.get('bssids', [])
        if ssid and bssids:
            ssid_groups[ssid].extend(bssids)
    
    rogue_alerts = []
    for ssid, bssids in ssid_groups.items():
        unique_bssids = list(set(bssids))
        if len(unique_bssids) > 3:
            rogue_alerts.append({
                'ssid': ssid,
                'bssid_count': len(unique_bssids),
                'bssids': unique_bssids,
                'risk': 'high' if len(unique_bssids) > 5 else 'medium'
            })
    
    return rogue_alerts


def detect_hidden_networks(output):
    """Detect hidden networks in scan output."""
    hidden = re.findall(r'SSID \d+ :', output)
    return len(hidden)


def generate_signal_bars(signal):
    """Generate ASCII signal strength bars."""
    bars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    index = min(int(signal / 12.5), len(bars) - 1)
    return bars[index]


def display_networks_detailed(networks, interface_info=None):
    """Display WiFi networks with professional analysis."""
    print("\n" + "=" * 100)
    print(f"{'PROFESSIONAL WiFi ANALYZER - ALL NEARBY NETWORKS':^100}")
    print(f"{'Scan Time: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^100}")
    print("=" * 100 + "\n")
    
    if interface_info:
        print(f"Interface: {interface_info.get('name', 'N/A')}")
        print(f"Status: {interface_info.get('state', 'N/A')}")
        if interface_info.get('connected_ssid'):
            print(f"Connected to: {interface_info['connected_ssid']}")
        print()
    
    if not networks:
        print("⚠ No WiFi networks detected")
        print("\nTroubleshooting:")
        print("  • Ensure WiFi adapter is enabled")
        print("  • Run as Administrator for full access")
        print("  • Check if airplane mode is off")
        return
    
    open_networks = [n for n in networks if n.get('authentication') == 'Open']
    wpa3_networks = [n for n in networks if 'WPA3' in n.get('authentication', '')]
    wpa2_networks = [n for n in networks if 'WPA2' in n.get('authentication', '')]
    
    print(f"📊 Network Summary:")
    print(f"   Total Networks: {len(networks)}")
    print(f"   Open (No Password): {len(open_networks)}")
    print(f"   WPA3 Secured: {len(wpa3_networks)}")
    print(f"   WPA2 Secured: {len(wpa2_networks)}")
    print(f"   Hidden Networks: {detect_hidden_networks('')}")
    print()
    
    sorted_networks = sorted(networks, key=lambda x: x.get('signal_strength', 0), reverse=True)
    
    print(f"{'#':<3} {'SSID':<30} {'Signal':<12} {'Security':<20} {'Band':<8} {'Ch':<4} {'Quality':<8} {'Status':<10}")
    print("-" * 100)
    
    for i, network in enumerate(sorted_networks, 1):
        ssid = network.get('ssid', 'Hidden')[:28]
        signal = network.get('signal_strength', 0)
        signal_bar = generate_signal_bars(signal)
        signal_str = f"{signal_bar} {signal}%"
        security = network.get('authentication', 'Unknown')[:18]
        band = network.get('band', 'N/A')[:6]
        channel = str(network.get('channel', 'N/A'))
        quality = calculate_network_quality(network)
        quality_str = f"{quality}/100"
        status = "SAVED" if network.get('saved', False) else "-"
        
        print(f"{i:<3} {ssid:<30} {signal_str:<12} {security:<20} {band:<8} {channel:<4} {quality_str:<8} {status:<10}")
    
    print("-" * 100)
    
    channel_analysis = analyze_channel_interference(networks)
    print(f"\n📡 Channel Analysis:")
    print(f"   2.4GHz Networks: {channel_analysis['2.4GHz']['total_networks']}")
    if channel_analysis['2.4GHz']['congested_channels']:
        print(f"   Congested Channels: {channel_analysis['2.4GHz']['congested_channels']}")
    if channel_analysis['2.4GHz']['recommended']:
        print(f"   Recommended (2.4GHz): {channel_analysis['2.4GHz']['recommended']}")
    
    print(f"   5GHz Networks: {channel_analysis['5GHz']['total_networks']}")
    if channel_analysis['5GHz']['congested_channels']:
        print(f"   Congested Channels: {channel_analysis['5GHz']['congested_channels']}")
    if channel_analysis['5GHz']['recommended']:
        print(f"   Recommended (5GHz): {channel_analysis['5GHz']['recommended']}")
    
    rogue_aps = detect_rogue_access_points(networks)
    if rogue_aps:
        print(f"\n⚠️  Rogue AP Detection:")
        for alert in rogue_aps:
            risk_icon = "🔴" if alert['risk'] == 'high' else "🟡"
            print(f"   {risk_icon} {alert['ssid']}: {alert['bssid_count']} different BSSIDs detected")
    
    print("\n" + "=" * 100)


def display_network_details(network):
    """Display detailed information for a single network."""
    print("\n" + "=" * 80)
    print(f"Network: {network.get('ssid', 'Unknown')}")
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
    if 'bssids' in network:
        print(f"  BSSID(s):")
        for bssid in network['bssids']:
            print(f"    - {bssid}")
    if 'mac_randomization' in network:
        print(f"  MAC Randomization: {network['mac_randomization']}")
    
    print(f"  Saved:            {'Yes' if network.get('saved', False) else 'No'}")
    print(f"  First Detected:   {network.get('first_seen', 'N/A')}")
    print("=" * 80 + "\n")


def display_saved_profiles(profiles):
    """Display saved WiFi profiles with passwords."""
    print("\n" + "=" * 80)
    print(f"{'SAVED WIFI PROFILES WITH PASSWORDS':^80}")
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
            print(f"    🔑 Password:     {details['password']}")
        else:
            print(f"    Password:       Requires Administrator privileges")
        
        if 'cost' in details:
            print(f"    Cost Profile:   {details['cost']}")
        print()
    
    print("=" * 80)


def live_monitor(interface_name=None, duration=60):
    """Live monitoring mode with real-time signal tracking."""
    print("\n" + "=" * 80)
    print("LIVE WiFi MONITOR")
    print("=" * 80)
    print(f"Duration: {duration} seconds (Ctrl+C to stop)")
    print()
    
    start_time = time.time()
    scan_count = 0
    signal_history = defaultdict(list)
    
    try:
        while time.time() - start_time < duration:
            scan_count += 1
            elapsed = int(time.time() - start_time)
            
            raw_output = scan_networks(interface_name)
            networks = parse_wifi_networks(raw_output)
            
            print(f"\n{'='*60}")
            print(f"Scan #{scan_count} | {elapsed}s elapsed | {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")
            
            if networks:
                top_networks = sorted(networks, key=lambda x: x.get('signal_strength', 0), reverse=True)[:8]
                
                for net in top_networks:
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
        for ssid, signals in signal_history.items():
            if len(signals) > 1:
                avg = sum(signals) / len(signals)
                min_sig = min(signals)
                max_sig = max(signals)
                print(f"  {ssid[:25]}: Avg={avg:.0f}% Min={min_sig}% Max={max_sig}%")


def export_comprehensive_report(networks, profiles, interface_info, filename="wifi_analysis_report.json"):
    """Export comprehensive analysis report."""
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
            'saved_profiles': len(profiles)
        },
        'channel_analysis': channel_analysis,
        'rogue_ap_alerts': rogue_aps,
        'networks': networks,
        'saved_profiles': profiles
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Comprehensive report exported to: {filename}")
    return filename


def export_csv(networks, filename="wifi_networks.csv"):
    """Export network data to CSV format."""
    import csv
    
    if not networks:
        print("No networks to export")
        return
    
    fieldnames = [
        'ssid', 'network_type', 'authentication', 'cipher',
        'signal_strength', 'channel', 'band', 'frequency_mhz',
        'bssids', 'saved', 'quality_score', 'first_seen'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for network in networks:
            row = network.copy()
            row['bssids'] = ';'.join(network.get('bssids', []))
            row['quality_score'] = calculate_network_quality(network)
            writer.writerow(row)
    
    print(f"✅ CSV exported to: {filename}")


def show_interface_details():
    """Show detailed WiFi interface information."""
    interfaces = get_wifi_interfaces()
    
    print("\n" + "=" * 80)
    print(f"{'WIFI INTERFACE DETAILS':^80}")
    print("=" * 80 + "\n")
    
    if not interfaces:
        print("No WiFi interfaces found.")
        return
    
    for iface in interfaces:
        print(f"Interface: {iface.get('name', 'N/A')}")
        print("-" * 80)
        for key, value in iface.items():
            if key != 'name':
                print(f"  {key.replace('_', ' ').title()}: {value}")
        print()
    
    print("=" * 80)


def compare_scans():
    """Compare two scan results."""
    print("\nCompare two scan files:")
    file1 = input("  First scan file: ").strip()
    file2 = input("  Second scan file: ").strip()
    
    try:
        with open(file1, 'r') as f:
            scan1 = json.load(f)
        with open(file2, 'r') as f:
            scan2 = json.load(f)
        
        print(f"\n📊 Scan Comparison:")
        print(f"  Scan 1: {scan1.get('scan_time', 'Unknown')} - {scan1.get('total_networks', 0)} networks")
        print(f"  Scan 2: {scan2.get('scan_time', 'Unknown')} - {scan2.get('total_networks', 0)} networks")
        
        ssids1 = {n['ssid'] for n in scan1.get('networks', [])}
        ssids2 = {n['ssid'] for n in scan2.get('networks', [])}
        
        new_networks = ssids2 - ssids1
        lost_networks = ssids1 - ssids2
        
        if new_networks:
            print(f"\n  New networks: {len(new_networks)}")
            for ssid in list(new_networks)[:5]:
                print(f"    + {ssid}")
        
        if lost_networks:
            print(f"\n  Lost networks: {len(lost_networks)}")
            for ssid in list(lost_networks)[:5]:
                print(f"    - {ssid}")
    
    except Exception as e:
        print(f"Error comparing scans: {e}")


def main():
    """Main function to run the WiFi scanner."""
    print("\n" + "=" * 100)
    print(f"{'🔍 PROFESSIONAL WiFi ANALYZER':^100}")
    print(f"{'Advanced Network Discovery & Analysis Tool':^100}")
    print("=" * 100)
    
    interfaces = get_wifi_interfaces()
    
    if not interfaces:
        print("\n❌ No WiFi interfaces found on this system.")
        print("\nTroubleshooting:")
        print("  1. Ensure WiFi adapter is installed and enabled")
        print("  2. Check Device Manager for adapter status")
        print("  3. Disable Airplane Mode")
        print("  4. Run as Administrator")
        return
    
    interface_info = interfaces[0]
    
    print(f"\n✅ WiFi Interface: {interface_info.get('name', 'N/A')}")
    print(f"   Status: {interface_info.get('state', 'N/A')}")
    
    if interface_info.get('connected_ssid'):
        print(f"   Connected: {interface_info['connected_ssid']}")
    
    print("\n🔎 Scanning for ALL nearby networks...")
    print("   (Detects every WiFi signal in range)\n")
    
    interface_name = interface_info.get('name')
    raw_output = scan_networks(interface_name)
    networks = parse_wifi_networks(raw_output)
    
    saved_profiles = get_saved_profiles()
    for network in networks:
        if network.get('ssid') in saved_profiles:
            network['saved'] = True
    
    display_networks_detailed(networks, interface_info)
    
    print("\n💾 Export Options:")
    print("  • JSON Report: Comprehensive analysis")
    print("  • CSV: Spreadsheet-compatible data")
    
    if networks:
        export_comprehensive_report(networks, saved_profiles, interface_info)
        export_csv(networks)
    
    print("\n" + "=" * 100)
    print("COMMAND REFERENCE:")
    print("=" * 100)
    print("  python wifi_scanner.py              - Full scan with analysis")
    print("  python wifi_scanner.py --profiles   - Show saved networks with passwords")
    print('  python wifi_scanner.py --password "Name" - Show specific profile password')
    print("  python wifi_scanner.py --live       - Live monitoring (60s)")
    print("  python wifi_scanner.py --interfaces - Show interface details")
    print("  python wifi_scanner.py --export     - Export only (no display)")
    print("  python wifi_scanner.py --compare    - Compare two scan files")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--password" and len(sys.argv) > 2:
            profile_name = " ".join(sys.argv[2:])
            details = get_profile_details(profile_name)
            print(f"\nProfile: {profile_name}")
            print(f"  Password: {details.get('password', 'Not available')}")
        elif sys.argv[1] == "--profiles":
            profiles = get_saved_profiles()
            display_saved_profiles(profiles)
        elif sys.argv[1] == "--live":
            duration = 60
            if len(sys.argv) > 2:
                try:
                    duration = int(sys.argv[2])
                except:
                    pass
            interfaces = get_wifi_interfaces()
            iface_name = interfaces[0]['name'] if interfaces else None
            live_monitor(iface_name, duration)
        elif sys.argv[1] == "--interfaces":
            show_interface_details()
        elif sys.argv[1] == "--export":
            interfaces = get_wifi_interfaces()
            interface_info = interfaces[0] if interfaces else None
            interface_name = interface_info.get('name') if interface_info else None
            raw_output = scan_networks(interface_name)
            networks = parse_wifi_networks(raw_output)
            profiles = get_saved_profiles()
            export_comprehensive_report(networks, profiles, interface_info)
            export_csv(networks)
        elif sys.argv[1] == "--compare":
            compare_scans()
        else:
            main()
    else:
        main()
