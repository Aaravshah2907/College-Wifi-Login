import requests
from bs4 import BeautifulSoup
import time
import re
import creds
# import subprocess

PORTAL_ENTRY = 'http://192.168.1.1'
CHECK_URL = "http://clients3.google.com/generate_204"

def add_page(page):
    with open('history_wifi_connection.txt', 'a') as f:
        f.write(page + '\n')

def is_connected():
    try:
        response = requests.get(CHECK_URL, timeout=3)
        return response.status_code == 204
    except requests.RequestException:
        return False

def extract_redirect_url(js_response):
    match = re.search(r'window\.location\s*=\s*"([^"]+)"', js_response)
    return match.group(1) if match else None

def attempt_login():
    # print("[*] Starting login attempt...")
    session = requests.Session()

    try:
        resp = session.get(PORTAL_ENTRY, timeout=5)
        redirect_url = extract_redirect_url(resp.text)
        if not redirect_url:
            # print("[!] Could not find JavaScript redirect.")
            return is_connected()

        # print(f"➡️ Redirected to: {redirect_url}")
    except requests.RequestException as e:
        # print(f"[!] Initial request failed: {e}")
        return False

    try:
        login_page = session.get(redirect_url, timeout=5)
    except requests.RequestException as e:
        #print(f"[!] Failed to reach login page: {e}")
        return False

    soup = BeautifulSoup(login_page.text, 'html.parser')

    magic = soup.find('input', {'name': 'magic'})
    magic = magic['value'] if magic else ''

    if '?' in redirect_url:
        redir = redirect_url.split('?')[1]
    else:
        redir = ''

    if not magic or not redir:
        #print("[!] Required fields missing. Aborting.")
        return False

    post_url = login_page.url
    payload = {
        'username': creds.USERNAME,
        'password': creds.PASSWORD,
        'magic': magic,
        '4Tredir': redir
    }

    try:
        login_resp = session.post(post_url, data=payload, timeout=5)
    except requests.RequestException as e:
        # print("[!] Login POST failed:", e)
        return False

    if "keepalive?" in login_resp.text or "success" in login_resp.text.lower():
        # print("✅ Logged in successfully!")
        keepalivepage = extract_redirect_url(login_resp.text)
        add_page(keepalivepage)
        '''
        subprocess.run("pbcopy", text=True, input=keepalivepage)
        # print("✅ Keep alive page added to clipboard")
        '''
        return True
    else:
        # print("❌ Login may have failed. Retrying...")
        return is_connected()

def auto_login_until_connected(retry_interval=0.5):
    # print("[*] Checking for internet connection...")
    while not is_connected():
        if attempt_login():
            break
        # print(f"🔁 Retrying in {retry_interval} seconds...\n")
        time.sleep(retry_interval)
    # print("🌐 Internet is up!")


if __name__ == "__main__":
    auto_login_until_connected()
