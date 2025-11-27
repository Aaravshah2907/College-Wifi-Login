import requests # type: ignore
from bs4 import BeautifulSoup # type can be removed
import time
import re
import datetime
import creds
import subprocess
import sys
import platform # Added for cross-platform OS detection

# --- Configuration ---
PORTAL_ENTRY = 'http://192.168.1.1'
CHECK_URL = "https://www.google.com/robots.txt" 
wifi_list = ['BITS-STUDENT', 'BITS-STAFF', '<redacted>']
LOG_FILE_PATH = "./history_wifi_connection.txt"

def get_wifi_ssid():
    os_type = platform.system()
    ssid = ""
    cmd = ""

    if os_type == "Darwin":  # macOS
        cmd = "ipconfig getsummary en0 | awk -F ' SSID : ' '/ SSID : / {print $2}'"
    elif os_type == "Windows":
        cmd = "netsh wlan show interfaces"
    elif os_type == "Linux":
        cmd = "iwgetid -r"
    else:
        print(f"Unsupported OS: {os_type}", file=sys.stderr)
        return ""

    if cmd:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            output = result.stdout.strip()

            if os_type == "Windows":
                match = re.search(r'SSID\s+:\s+(.*)', output, re.IGNORECASE)
                if match:
                    ssid = match.group(1).strip()
                else:
                    print("Could not find SSID in Windows output.", file=sys.stderr)
            else:
                ssid = output
                
        except subprocess.CalledProcessError as e:
            print(f"Command failed for {os_type}: {e.stderr.strip()}", file=sys.stderr)
            return ""
        except FileNotFoundError:
            print(f"Required command ('{cmd.split()[0]}') not found for {os_type}.", file=sys.stderr)
            return ""
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            return ""
    return ssid


def extract_redirect_url(js_response):
    # Looks for a pattern like: window.location = "https://<url>"
    match = re.search(r'window\.location\s*=\s*"([^"]+)"', js_response)
    # Return the captured URL or None if no redirect is found
    return match.group(1) if match else None

def extract_keepalive_url(html_response):
    # Finds a URL containing 'keepalive?' or 'logout?' inside the response body
    keepalive_regex = r'(https?://[^"\'\s]*(keepalive|logout)\?[^"\'\s]*)'
    match = re.search(keepalive_regex, html_response)
    return match.group(1) if match else None

def log_connection_status(keepalive_url):
    timestamp = datetime.datetime.now().strftime('%d %b %H:%M:%S')
    log_entry = f"{timestamp} {keepalive_url}"
    # Uses the global LOG_FILE_PATH variable for device independence
    with open(LOG_FILE_PATH, "a") as f:
        f.write(log_entry + "\n")
    print(f"🔗 Keepalive URL captured and logged to {LOG_FILE_PATH}.")
    
def is_connected():
    """
    Checks if we are successfully past the captive portal using a two-step validation:
    1. Check an external HTTPS site (to catch connection/SSL errors).
    2. If external site succeeds (potential false positive), check if the 
       captive portal entry point is still redirecting/active. If it is, 
       we are still trapped.
    """
    # --- Check 1: External HTTPS Site ---
    try:
        response = requests.get(CHECK_URL, timeout=5)
        is_valid_url = response.url == CHECK_URL
        
        if not (response.status_code == 200 and is_valid_url):
            print(f"Connection Check Status: External check failed ({response.status_code}, URL: {response.url}).")
            return False # External check failed, definitely not connected.
        
        # External check succeeded. This is the 'false positive' scenario.
        print("Connection Check Status: External HTTPS succeeded. Verifying against portal entry...")

    except requests.RequestException as e:
        # Catches SSL errors, timeouts, etc. Definitely not connected.
        print(f"Connection Check Status: External check failed (RequestException: {type(e).__name__}).")
        return False
    except Exception as e:
        print(f"Error in external check: {e}", file=sys.stderr)
        return False

    # --- Check 2: Internal Portal Validation (Anti-False-Positive) ---
    try:
        # If we are truly connected, this internal IP should no longer show the login page.
        portal_resp = requests.get(PORTAL_ENTRY, timeout=3)
        
        # If the response text still contains the typical login page setup (like the redirect script), 
        # we are still trapped by the portal, even though the external check succeeded.
        if 'window.location' in portal_resp.text or 'login' in portal_resp.text.lower():
            print("Anti-False-Positive Check: Portal entry is still redirecting/active. Still trapped.")
            return False
        
        # If the portal URL succeeded but didn't show the login page, 
        # assume we've hit the router's home page or it's genuinely free.
        print("Anti-False-Positive Check: Portal entry did not show login page. True connection confirmed.")
        return True
        
    except requests.RequestException:
        # If the portal URL times out or fails (which is ideal when connected, 
        # as the router stops intercepting it), this confirms we are free.
        print("Anti-False-Positive Check: Portal entry failed to respond. True connection confirmed.")
        return True
    except Exception as e:
        print(f"Error in internal validation: {e}", file=sys.stderr)
        return False


# --- Core Login Function ---

def attempt_login():
    print("\n[*] Starting login attempt...")
    session = requests.Session()

    try:
        # First request to the portal entry point
        resp = session.get(PORTAL_ENTRY, timeout=5)
        redirect_url = extract_redirect_url(resp.text)
        
        if not redirect_url or PORTAL_ENTRY in redirect_url:
            print("[!] Could not find valid JavaScript redirect. Assuming no login page needed or already connected.")
            return False 

        print(f"➡️ Redirected to: {redirect_url}")
    except requests.RequestException as e:
        print(f"[!] Initial request to portal entry failed: {e}")
        return False

    try:
        # Second request to the actual login page
        login_page = session.get(redirect_url, timeout=5)
    except requests.RequestException:
        print("[!] Failed to reach login page.")
        return False

    soup = BeautifulSoup(login_page.text, 'html.parser')

    magic = soup.find('input', {'name': 'magic'})
    magic = magic['value'] if magic else ''

    # Get the query parameters of the redirect URL
    redir = redirect_url.split('?')[1] if '?' in redirect_url else ''

    if not magic or not redir:
        print("[!] Required fields (magic/redir) missing on login page. Aborting.")
        return False

    post_url = login_page.url
    payload = {
        'username': creds.USERNAME,
        'password': creds.PASSWORD,
        'magic': magic,
        '4Tredir': redir
    }

    try:
        # Final POST request to log in
        login_resp = session.post(post_url, data=payload, timeout=5)
    except requests.RequestException as e:
        print("[!] Login POST failed:", e)
        return False

    # Check for success indicators from the portal
    if "keepalive?" in login_resp.text or "success" in login_resp.text.lower():
        print("✅ Logged in successfully! Waiting for network stabilization...")
        
        # --- LOGGING BLOCK (Uncomment the entire block below to enable logging) ---
        '''
        try:
            # 1. Extract the unique session URL from the successful response HTML
            keepalive_url = extract_keepalive_url(login_resp.text)
            
            if keepalive_url:
                # 2. Log the URL and timestamp to the device-independent file
                log_connection_status(keepalive_url)
            else:
                print("⚠️ Login succeeded, but failed to extract Keepalive URL for logging.")
                
        # Check for logupdate flag in creds file (optional if creds is not present/misconfigured)
        except AttributeError:
            print("⚠️ Logging skipped: Missing 'logupdate' flag or creds configuration.")
        # --- END LOGGING BLOCK ---
        '''

        return True
    else:
        print("❌ Login POST was successful, but server response indicates failure.")
        return False

# --- Main Automation Loop ---

def auto_login_until_connected(retry_interval=2):
    print(f"[*] Starting auto-login loop with {retry_interval}s interval.")
    
    # 1. Main loop: Keep trying until is_connected() returns True
    while not is_connected():
        print("\n--- NOT CONNECTED. Attempting login... ---")
        
        if attempt_login():
            print(f"Login attempt succeeded. Pausing for {retry_interval} seconds to confirm connection...")
            time.sleep(retry_interval)
        else:
            print(f"🔁 Login attempt failed or skipped. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

    print("🌐 Internet is UP and connection is confirmed!")

if __name__ == "__main__":
    SSID = get_wifi_ssid()
    if SSID in wifi_list:
        auto_login_until_connected()
    else:
        print(f"⚠️ Current WiFi SSID '{SSID}' is not in the allowed list: {wifi_list}. Skipping auto-login.")