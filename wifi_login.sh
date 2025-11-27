#!/bin/bash

# --- 0. Start Timer ---
START_TIME=$(date +%s)

# --- Configuration and Credentials (UPDATE THESE) ---
PORTAL_ENTRY="http://192.168.1.1/"
CHECK_URL="https://www.google.com/robots.txt"
HISTORY_FILE="./history_wifi_connection.txt"
COOKIE_FILE="/tmp/bits_wifi_cookies.txt"

# !!! UPDATE THESE CREDENTIALS !!!
USERNAME="USERNAME_HERE" 
PASSWORD="PASSWORD_HERE" 
KNOWN_SSIDS=("BITS-STAFF" "BITS-STUDENT" "<redacted>")

# --- Function to check for true internet connectivity ---
is_connected() {
    echo -n "Checking external connection to $CHECK_URL... "
    # Check 1: External HTTPS connection. Optimized with -m 0.5
    HTTP_STATUS=$(curl -m 0.5 -k -s -o /dev/null -w "%{http_code}" "$CHECK_URL")
    
    if [ "$HTTP_STATUS" -ne 200 ]; then
        echo "FAIL (Status: $HTTP_STATUS). Definitely disconnected."
        return 1
    fi
    
    echo "SUCCESS (Status: 200). Verifying against captive portal..."
    # Check 2: Internal Portal Validation (Anti-False-Positive). Optimized with -m 0.5
    PORTAL_RESPONSE=$(curl -s -m 0.5 "$PORTAL_ENTRY")
    
    if echo "$PORTAL_RESPONSE" | grep -E -q "window\.location|fgtauth|login"; then
        echo "Anti-False-Positive Check: FAIL. Portal is still active. Still trapped."
        return 1
    else
        echo "Anti-False-Positive Check: PASS. Portal is inactive. Internet is UP."
        return 0
    fi
}

# --- Main Script Logic ---

# 1. Get current SSID on macOS
SSID=$(ipconfig getsummary en0 | awk -F ' SSID : ' '/ SSID : / {print $2}')
echo "Current SSID detected: '$SSID'"

# 2. Check for matching SSID
MATCHED=false
for KNOWN in "${KNOWN_SSIDS[@]}"; do
    if [[ "$SSID" == "$KNOWN" ]]; then
        MATCHED=true
        break
    fi
done

if [ "$MATCHED" = false ]; then
    echo "SSID '$SSID' is not in the list of known networks. Exiting."
    # --- 12. Final Execution Time ---
    END_TIME=$(date +%s)
    echo "⏱️ Script execution time: $((END_TIME - START_TIME)) seconds."
    exit 0
fi

# 3. Check for actual internet connection
if is_connected; then
    echo "Internet is already connected. Exiting script."
    rm -f "$COOKIE_FILE" # Clean up if it exists
    # --- 12. Final Execution Time ---
    END_TIME=$(date +%s)
    echo "⏱️ Script execution time: $((END_TIME - START_TIME)) seconds."
    exit 0
fi

# 4. If not connected, proceed with login attempt
echo "Internet is down. Proceeding with login attempt..."

# Initial local gateway call (CRITICAL: Save session cookies with -c)
RESPONSE1=$(curl -s -c "$COOKIE_FILE" "$PORTAL_ENTRY")

# 5. Extract redirect URL from JavaScript
if [[ "$RESPONSE1" =~ (https://[^\"\'\ >]+fgtauth[^\"\'\ >]+) ]]; then
    REDIRECT_URL="${BASH_REMATCH[1]}"
    echo "➡️ Redirected to: $REDIRECT_URL"

    # 6. Call redirect URL and get login page (CRITICAL: Use cookies with -b)
    LOGIN_PAGE=$(curl -s -b "$COOKIE_FILE" "$REDIRECT_URL")

    # 7. Extract `magic` token from HTML
    if [[ "$LOGIN_PAGE" =~ name=\"magic\"[[:space:]]*value=\"([^\"]+)\" ]]; then
        MAGIC="${BASH_REMATCH[1]}"
        echo "Token 'magic' extracted: $MAGIC"

        # 8. Extract the 4Tredir value (if present, often empty)
        if [[ "$REDIRECT_URL" =~ \?([^&]+) ]]; then
            REDIR_STRING="${BASH_REMATCH[1]}"
        else
            REDIR_STRING=""
        fi

        # 9. Send login payload (CRITICAL: Use cookies -b and follow redirects -L)
        FINAL_RESPONSE=$(curl -s -L -X POST "$REDIRECT_URL" \
            -b "$COOKIE_FILE" \
            -d "4Tredir=$REDIR_STRING" \
            -d "magic=$MAGIC" \
            -d "username=$USERNAME" \
            -d "password=$PASSWORD")

        # 10. Check the response for success indicators
        if echo "$FINAL_RESPONSE" | grep -E -q "keepalive\?|success"; then
            echo "✅ Login SUCCESSFUL."
            
            KEEPALIVE_URL=""
            KEEPALIVE_REGEX='(https?://[^"'\''<>]*(keepalive|logout)\?[^"'\''<>]*)'

            if [[ "$FINAL_RESPONSE" =~ $KEEPALIVE_REGEX ]]; then
                KEEPALIVE_URL="${BASH_REMATCH[1]}"
            fi

            if [ -n "$KEEPALIVE_URL" ]; then
                TIMESTAMP=$(date +"%d %b %H:%M:%S")
                LOG_ENTRY="$TIMESTAMP $KEEPALIVE_URL"
                echo "🔗 Keepalive URL captured: $KEEPALIVE_URL"
                echo "📝 Logging to $HISTORY_FILE..."
                echo "$LOG_ENTRY" >> "$HISTORY_FILE"
            else
                echo "⚠️ Login succeeded, but failed to extract Keepalive URL for logging."
            fi

            # Final check to confirm connection is genuinely up after a brief wait 
            if is_connected; then
                echo "🌐 Internet connection confirmed and stable."
            else
                echo "⚠️ Login succeeded, but connection confirmation failed. Might need a moment."
            fi
        else
            echo "❌ Login failed. Server response did not contain success indicators."
        fi
    else
        echo "❌ Failed to extract magic token from login page."
    fi
else
    echo "❌ Redirect URL not found on portal entry ($PORTAL_ENTRY)."
fi

# 11. Clean up temporary cookie file
rm -f "$COOKIE_FILE"

# --- 12. Final Execution Time ---
END_TIME=$(date +%s)
echo "⏱️ Script execution time: $((END_TIME - START_TIME)) seconds."
# Ensure script ends with a clean newline to avoid EOF errors
echo ""