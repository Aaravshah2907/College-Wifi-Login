#!/bin/bash

# 1. Get current SSID on macOS
SSID=$(ipconfig getsummary en0 | awk -F ' SSID : ' '/ SSID : / {print $2}')

# 2. List of known SSIDs
KNOWN_SSIDS=("BITS-STAFF" "BITS-STUDENT" "<redacted>")

# 3. Check for matching SSID
MATCHED=false
for KNOWN in "${KNOWN_SSIDS[@]}"; do
    if [[ "$SSID" == "$KNOWN" ]]; then
        MATCHED=true
        break
    fi
done

# Check for internet using Google's generate_204 endpoint
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://clients3.google.com/generate_204)

# If internet is connected (HTTP 204), exit the script
if [ "$HTTP_STATUS" -eq 204 ]; then
    echo "Internet is already connected. Exiting script."
    exit 0
fi

if [ "$MATCHED" = true ]; then

    # 4. Initial local gateway call
    INITIAL_URL="http://192.168.1.1/"
    RESPONSE1=$(curl -s "$INITIAL_URL")

    # 5. Extract redirect URL from JavaScript
    if [[ "$RESPONSE1" =~ (https://[^\"\'\ >]+fgtauth[^\"\'\ >]+) ]]; then
        REDIRECT_URL="${BASH_REMATCH[1]}"

        # 6. Call redirect URL and get login page
        LOGIN_PAGE=$(curl -s "$REDIRECT_URL")

        # 7. Extract `magic` token from HTML
        if [[ "$LOGIN_PAGE" =~ name=\"magic\"[[:space:]]*value=\"([^\"]+)\" ]]; then
            MAGIC="${BASH_REMATCH[1]}"

            # 8. Send login payload
            USERNAME="username" # Change to your username
            PASSWORD="password" # Change to your password

            FINAL_RESPONSE=$(curl -s -X POST "$REDIRECT_URL" \
                -d "4Tredir=" \
                -d "magic=$MAGIC" \
                -d "username=$USERNAME" \
                -d "password=$PASSWORD")

            echo "Connected to the network successfully."
        else
            echo "Failed to extract magic token."
        fi
    else
        echo "Redirect URL not found."
    fi
else
    echo "SSID '$SSID' is not in the list of known networks."
fi
