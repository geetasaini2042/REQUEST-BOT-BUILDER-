import os
import json
import base64
import requests
from common_data import BASE_URL

# ✅ GitHub config
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "geetasaini2042/Database"
GITHUB_PATH = "all_registered_bot.json"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}"

def save_registered_bot_to_github(owner_id: int, bot_username: str, bot_id: str):
    """
    ✅ Function: save_registered_bot_to_github
    काम: all_registered_bot.json को GitHub से fetch करके अपडेट करता है।
    - अगर फाइल मौजूद नहीं है तो नई बनाता है।
    - हर owner_id के अंदर उसके बॉट्स सेव होते हैं।
    - हर बॉट में username और webhook_base_url दोनों सेव होते हैं।
    """

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 🔹 Step 1: फाइल fetch करें
    response = requests.get(API_URL, headers=headers)
    if response.status_code == 200:
        content = response.json()
        sha = content["sha"]
        file_data = json.loads(base64.b64decode(content["content"]).decode("utf-8"))
    else:
        # अगर file नहीं मिली तो नया dict बनाएं
        file_data = {}
        sha = None

    owner_key = str(owner_id)

    # 🔹 Step 2: owner entry ensure करें
    if owner_key not in file_data:
        file_data[owner_key] = {"bots": {}}

    # 🔹 Step 3: bot data add/update करें
    file_data[owner_key]["bots"][bot_id] = {
        "username": bot_username,
        "webhook_base_url": BASE_URL
    }

    # 🔹 Step 4: updated JSON को encode करें
    updated_content = json.dumps(file_data, indent=4, ensure_ascii=False)
    encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")

    # 🔹 Step 5: GitHub पर upload करें
    payload = {
        "message": f"Update bot {bot_username} ({bot_id}) for owner {owner_id}",
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    upload_response = requests.put(API_URL, headers=headers, json=payload)

    # 🔹 Step 6: Result print करें
    if upload_response.status_code in [200, 201]:
        print(f"✅ Bot '{bot_username}' ({bot_id}) added/updated for owner '{owner_id}' successfully!")
    else:
        print(f"❌ GitHub upload failed: {upload_response.status_code}")
        print(upload_response.text)