import os
from dotenv import load_dotenv

load_dotenv()

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
IS_TERMUX = os.getenv("IS_TERMUX", "false").lower() == "true"
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000") #without last /
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
BOTS_JSON_PATH = os.path.join(BASE_PATH, "bots.json")