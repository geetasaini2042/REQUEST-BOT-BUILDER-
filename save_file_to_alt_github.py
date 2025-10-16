import os
import json
import base64
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

# 📜 Logger सेटअप
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AltGitHubSaver")

# ⚙️ पर्यावरण से GitHub Token
ALT_GITHUB_TOKEN = os.getenv("ALT_GITHUB_TOKEN")  # <--- .env में define करें

# ⚙️ Repository और Owner Details
ALT_REPO = "sainipankaj2007ps/Database-for-Telegram-builder"
GITHUB_API = "https://api.github.com"


def save_json_to_alt_github(local_json_path: str, github_path: str):
    """
    📦 Local JSON फ़ाइल को दूसरे GitHub Repo में अपलोड या अपडेट करता है।
    Args:
        local_json_path (str): लोकल JSON फ़ाइल का path।
        github_path (str): GitHub में Repo के अंदर path (उदा: 'data/bots.json')
    """

    try:
        if not ALT_GITHUB_TOKEN:
            raise ValueError("⚠️ ALT_GITHUB_TOKEN environment variable सेट नहीं है")

        if not os.path.exists(local_json_path):
            raise FileNotFoundError(f"⚠️ फ़ाइल नहीं मिली: {local_json_path}")

        with open(local_json_path, "r", encoding="utf-8") as f:
            json_content = f.read()

        # GitHub API URL
        url = f"{GITHUB_API}/repos/{ALT_REPO}/contents/{github_path}"

        # पहले Check करें कि फ़ाइल मौजूद है या नहीं
        headers = {"Authorization": f"token {ALT_GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)

        sha = None
        if response.status_code == 200:
            sha = response.json()["sha"]  # फ़ाइल पहले से मौजूद है
            logger.info("🌀 Existing file मिला, update किया जाएगा")
        elif response.status_code == 404:
            logger.info("🆕 नई फ़ाइल बनाई जाएगी")
        else:
            response.raise_for_status()

        # अब फ़ाइल upload/update करें
        data = {
            "message": f"Update JSON file {github_path}",
            "content": base64.b64encode(json_content.encode()).decode(),
            "branch": "main",
        }

        if sha:
            data["sha"] = sha  # Update के लिए SHA देना जरूरी

        upload = requests.put(url, headers=headers, data=json.dumps(data))
        upload.raise_for_status()

        logger.info(f"✅ फ़ाइल सफलतापूर्वक सेव की गई: {github_path}")
        return {"status": "success", "path": github_path}

    except Exception as e:
        logger.error(f"❌ Error saving to alternate GitHub: {e}")
        return {"status": "error", "message": str(e)}