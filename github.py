import os
import json
import base64
import requests
import logging
from dotenv import load_dotenv
from common_data import BOTS_JSON_PATH, BASE_URL
import base64

# 🔹 Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bots_sync.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 🔹 .env लोड करें
load_dotenv()

def url_to_token(base_url):
    """BASE_URL को safe token में बदलें"""
    # Encode URL bytes to base64 और फिर string बनाएं
    token = base64.urlsafe_b64encode(base_url.encode()).decode()
    return token

def token_to_url(token):
    """Token को वापस BASE_URL में बदलें"""
    base_url = base64.urlsafe_b64decode(token.encode()).decode()
    return base_url

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "geetasaini2042/Database"
GITHUB_PATH = f"{url_to_token(BASE_URL)}/bots.json"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}"

def save_bots_to_github():
    """Upload local bots.json to GitHub using GITHUB_TOKEN"""
    if not GITHUB_TOKEN:
        logging.error("❌ GITHUB_TOKEN not found in .env file")
        return False

    # 🔹 bots.json पढ़ें
    if not os.path.exists(BOTS_JSON_PATH):
        logging.error("❌ bots.json file not found locally")
        return False

    with open("bots.json", "r", encoding="utf-8") as f:
        file_content = f.read()

    # 🔹 GitHub पर पहले की file की SHA प्राप्त करें (overwrite करने के लिए)
    response = requests.get(API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    sha = response.json().get("sha") if response.status_code == 200 else None

    # 🔹 नया कंटेंट Base64 में encode करें
    encoded_content = base64.b64encode(file_content.encode()).decode()

    payload = {
        "message": "Update bots.json",
        "content": encoded_content,
        "sha": sha,
    }
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    res = requests.put(API_URL, headers=headers, json=payload)
    if res.status_code in (200, 201):
        logging.info("✅ bots.json successfully uploaded to GitHub")
        return True
    else:
        logging.error(f"❌ Failed to upload: {res.status_code} — {res.text}")
        return False


def add_new_bot(bot_id: str, bot_details: dict):
    """Add or update bot details in bots.json and push to GitHub"""
    bots_file = "bots.json"

    # 🔹 Existing data लोड करें
    if os.path.exists(bots_file):
        try:
            with open(bots_file, "r", encoding="utf-8") as f:
                bots_data = json.load(f)
        except json.JSONDecodeError:
            logging.warning("⚠️ bots.json corrupted, creating new one.")
            bots_data = {}
    else:
        logging.info("ℹ️ bots.json not found, creating a new one.")
        bots_data = {}

    # 🔹 नया बॉट जोड़ें या अपडेट करें
    bots_data[bot_id] = bot_details
    logging.info(f"🧩 Adding/Updating bot ID: {bot_id}")

    # 🔹 फाइल में सेव करें
    with open(bots_file, "w", encoding="utf-8") as f:
        json.dump(bots_data, f, indent=4, ensure_ascii=False)

    # 🔹 GitHub पर अपलोड करें
    if save_bots_to_github():
        logging.info(f"✅ Bot {bot_id} added/updated successfully.")
    else:
        logging.error(f"❌ Failed to push bot {bot_id} data to GitHub.")



def download_bots_from_github():
    """
    GitHub से bots.json डाउनलोड करे और लोकल में सेव करे।
    """
    if not GITHUB_TOKEN:
        logging.error("❌ GITHUB_TOKEN not found in .env file")
        return False

    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    logging.info(f"⬇️ Downloading {GITHUB_PATH} from GitHub repo: {GITHUB_REPO}")

    res = requests.get(API_URL, headers=headers)
    if res.status_code != 200:
        logging.error(f"❌ Failed to download: {res.status_code} — {res.text}")
        return False

    try:
        content = res.json().get("content")
        if not content:
            logging.error("❌ No content found in GitHub response.")
            return False

        decoded = base64.b64decode(content).decode("utf-8")

        # 🔹 लोकल में सेव करें
        with open(BOTS_JSON_PATH, "w", encoding="utf-8") as f:
            f.write(decoded)

        logging.info(f"✅ Successfully saved to {BOTS_JSON_PATH}")
        return True

    except Exception as e:
        logging.exception(f"❌ Error while decoding/saving bots.json: {e}")
        return False