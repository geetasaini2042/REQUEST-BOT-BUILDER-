import requests, threading, re, os, json, uuid
from flask import jsonify
from pathlib import Path
from common_data import IS_TERMUX, API_URL, BOT_TOKEN, BASE_PATH,BOTS_JSON_PATH
from typing import Optional
# ============================
#   FILTER SYSTEM
# ============================

class Filter:
    def __init__(self, func):
        self.func = func

    def __call__(self, msg):
        try:
            return self.func(msg)
        except Exception:
            return False

    def __and__(self, other):
        return Filter(lambda m: self(m) and other(m))

    def __or__(self, other):
        return Filter(lambda m: self(m) or other(m))

    def __invert__(self):
        return Filter(lambda m: not self(m))

class filters:
    # ---------- MESSAGE FILTERS ----------
    @staticmethod
    def command(cmd: str):
        return Filter(lambda m: isinstance(m.get("text", ""), str)
                      and m.get("text", "").strip().split()[0] == f"/{cmd}")

    @staticmethod
    def regex(pattern: str):
        prog = re.compile(pattern)
        return Filter(lambda m: isinstance(m.get("text", ""), str)
                      and bool(prog.search(m.get("text", ""))))

    @staticmethod
    def text():
        return Filter(lambda m: "text" in m and isinstance(m.get("text"), str))

    @staticmethod
    def private():
        return Filter(lambda m: m.get("chat", {}).get("type") == "private")

    @staticmethod
    def group():
        return Filter(lambda m: m.get("chat", {}).get("type") in ("group", "supergroup"))

    @staticmethod
    def all():
        return Filter(lambda m: True)

    # ---------- MEDIA FILTERS ----------
    @staticmethod
    def document():
        return Filter(lambda m: "document" in m)

    @staticmethod
    def video():
        return Filter(lambda m: "video" in m)

    @staticmethod
    def audio():
        return Filter(lambda m: "audio" in m)

    @staticmethod
    def photo():
        # photo Telegram में list होती है — इसलिए check ऐसा रहेगा
        return Filter(lambda m: "photo" in m and isinstance(m["photo"], list) and len(m["photo"]) > 0)

    # ---------- CALLBACK FILTERS ----------
    @staticmethod
    def callback_data(pattern: str):
        prog = re.compile(pattern)
        return Filter(lambda cq: bool(prog.search(cq.get("data", ""))))
# ============================
#   DECORATOR SYSTEM
# ============================
message_handlers = []
callback_handlers = []



def get_status_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "status_user.json")

def get_temp_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "temp_folder.json")

def get_data_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "bot_data.json")

def get_bot_folder(bot_token: str) -> str:
    #numeric = ''.join(filter(str.isdigit, bot_token))
    numeric = bot_token.split(":")[0]
    print(numeric)
    
    # Build folder path
    base_path = Path(BASE_PATH) / "BOT_DATA"
    folder_path = base_path / numeric
    
    # Create folder if not exists
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Return as string
    return str(folder_path)


# ------------------------------
#   File Utilities
# ------------------------------
def load_json_file(path: str) -> dict:
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f)
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json_file(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

class StatusFilter(Filter):
    def __init__(self, required_status: str):
        self.required_status = required_status
        super().__init__(self.check_status)

    def check_status(self, msg):
        bot_token = msg.get("bot_token")  # webhook update me token pass करना होगा
        user_id = msg.get("from", {}).get("id")
        if not bot_token or not user_id:
            return False
        status_file = get_status_file(bot_token)
        data = load_json_file(status_file)
        user_status = data.get(str(user_id), "")
        return user_status.startswith(self.required_status)
# ============================
#   TELEGRAM UTILS
# ============================
def send_message(bot_token, chat_id, text):
    """Send message asynchronously"""
    def _send():
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": text}
            requests.post(url, json=payload, timeout=2)
        except Exception as e:
            print("⚠️ Send error:", e)

    threading.Thread(target=_send, daemon=True).start()


# ============================
#   MAIN UPDATE PROCESSOR
# ============================

def handle_webhook_request(bot_token, update):
    """Return immediate OK & start background thread"""
    
    # 🔹 bots.json लोड करें
    try:
        with open(BOTS_JSON_PATH, "r", encoding="utf-8") as f:
            bots_data = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "data not found"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "invalid data format"}), 500

    # 🔹 चेक करें कि token bots.json में है या नहीं
    authorized = any(bot_info.get("bot_token") == bot_token for bot_info in bots_data.values())
    if not authorized:
        return jsonify({"error": "unauthorized token"}), 401

    # 🔹 अगर टोकन वैध है तो बैकग्राउंड में प्रोसेस करें
    threading.Thread(target=process_update, args=(bot_token, update), daemon=True).start()
    return jsonify({"status": "ok"}), 200
    
    
# framework.py
def on_message(filter_obj=None):
    """Register message handler"""
    def decorator(func):
        message_handlers.append((filter_obj or filters.all(), func))
        return func
    return decorator


def on_callback_query(filter_obj=None):
    """Register callback query handler"""
    def decorator(func):
        callback_handlers.append((filter_obj or filters.callback_data(".*"), func))
        return func
    return decorator
# -------------------------
# Telegram helper (fast)
# -------------------------

def send_message(bot_token: str, chat_id: int, text: str, reply_markup: dict = None):
    """Send message in background thread to keep webhook fast"""
    def _send():
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        _post(url, payload, timeout=3)
    threading.Thread(target=_send, daemon=True).start()

def edit_message_text(bot_token: str, chat_id: int, message_id: int, text: str, reply_markup: dict = None):
    """Edit message text (background)"""
    def _edit():
        url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        _post(url, payload, timeout=3)
    threading.Thread(target=_edit, daemon=True).start()

class TelegramSendMessageError(Exception):
    """Custom exception for Telegram sendMessage failures"""
    pass
#send_message(bot_token, chat_id, prompt_caption, parse_mode="Markdown")
def send_message(bot_token: str, chat_id: int, text: str,parse_mode=None, reply_markup=None):
    """
    Send message in background thread.
    Raises TelegramSendMessageError if message fails.
    reply_markup should be a dict or InlineKeyboardMarkup object
    """
    def _send():
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        if reply_markup:
            if hasattr(reply_markup, "to_dict"):
                payload["reply_markup"] = reply_markup.to_dict()
            else:
                payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(url, json=payload, timeout=5)
            data = resp.json()
            if not data.get("ok"):
                # Raise error with Telegram description
                raise TelegramSendMessageError(data.get("description", "Unknown error"))
        except requests.RequestException as e:
            raise TelegramSendMessageError(f"HTTP request failed: {e}") from e
        except Exception as e:
            raise TelegramSendMessageError(f"Send failed: {e}") from e

    # Run in background thread
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
    return thread  # Optional: return thread if you want to join/wait
def send_with_error_message(bot_token: str, chat_id: int, text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode" : "Markdown"}

    if reply_markup:
        if hasattr(reply_markup, "to_dict"):
            payload["reply_markup"] = reply_markup.to_dict()
        else:
            payload["reply_markup"] = reply_markup

    try:
        resp = requests.post(url, json=payload, timeout=5)
        data = resp.json()
        if not data.get("ok"):
            raise TelegramSendMessageError(data.get("description", "Unknown error"))
    except requests.RequestException as e:
        raise TelegramSendMessageError(f"HTTP request failed: {e}") from e
#edit_message_text(bot_token, chat_id, message_id, caption, reply_markup=keyboard, is_caption=True)
def edit_message(bot_token: str, chat_id: int, message_id: int, text: str, reply_markup=None, is_caption=False):
    """Auto choose editMessageText or editMessageCaption"""
    def _edit():
        method = "editMessageCaption" if is_caption else "editMessageText"
        url = f"https://api.telegram.org/bot{bot_token}/{method}"

        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "parse_mode": "Markdown"
        }

        if is_caption:
            payload["caption"] = text
        else:
            payload["text"] = text

        if reply_markup:
            if hasattr(reply_markup, "to_dict"):
                payload["reply_markup"] = reply_markup.to_dict()
            elif isinstance(reply_markup, dict):
                payload["reply_markup"] = reply_markup
            else:
                payload["reply_markup"] = {
                    "inline_keyboard": [
                        [
                            (
                                btn.to_dict()
                                if hasattr(btn, "to_dict")
                                else btn
                            )
                            for btn in row
                        ]
                        for row in getattr(reply_markup, "inline_keyboard", [])
                    ]
                }

        try:
            r = requests.post(url, json=payload, timeout=3)
            if not r.ok:
                print(f"{method} error:", r.text)
        except Exception as e:
            print("HTTP post error:", e)

    import threading
    threading.Thread(target=_edit, daemon=True).start()


def answer_callback_query(bot_token: str, callback_query_id: str, text: str = None, show_alert: bool = False):
    def _ans():
        url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            payload["text"] = text
        _post(url, payload, timeout=3)
    threading.Thread(target=_ans, daemon=True).start()
#answer_callback_query(bot_token, callback_id, "❌ File not found in temp.", True)
def answer_callback_query(bot_token: str, callback_query_id: str, text: str = None, show_alert: bool = False):
    """Acknowledge callback to remove loading spinner"""
    def _ans():
        url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            payload["text"] = text
        _post(url, payload, timeout=3)
    threading.Thread(target=_ans, daemon=True).start()


def process_update(bot_token: str, update: dict):
    try:
        # MESSAGE handling
        if "message" in update:
            msg = update["message"]
            msg["bot_token"] = bot_token   # 🟢 Inject bot_token

            for f, func in message_handlers:
                try:
                    if f(msg):
                        func(bot_token, update, msg)
                        break
                except Exception as e:
                    print("Handler error:", e)

        # CALLBACK_QUERY handling
        elif "callback_query" in update:
            cq = update["callback_query"]
            cq["bot_token"] = bot_token   # 🟢 Inject bot_token

            data = cq.get("data", "")
            for f, func in callback_handlers:
                try:
                    ok = f(cq) if callable(f) else False
                    if ok:
                        func(bot_token, update, cq)
                        break
                except Exception as e:
                    print("Callback handler error:", e)

    except Exception as e:
        print("❌ process_update error:", e)
# ============================
#   WEBHOOK ENTRY POINT
# ============================


# framework.py या अलग helpers.py में रखें

class InlineKeyboardButton:
    def __init__(self, text: str, callback_data: str = None, url: str = None, web_app: dict = None):
        self.text = text
        self.callback_data = callback_data
        self.url = url
        self.web_app = web_app

    def to_dict(self):
        data = {"text": self.text}
        if self.callback_data:
            data["callback_data"] = self.callback_data
        if self.url:
            data["url"] = self.url
        if self.web_app:
            data["web_app"] = self.web_app
        return data


class InlineKeyboardMarkup:
    def __init__(self, buttons: list[list[InlineKeyboardButton]]):
        self.inline_keyboard = [
            [btn.to_dict() for btn in row] for row in buttons
        ]

    def to_dict(self):
        return {"inline_keyboard": self.inline_keyboard}
        
import re

def escape_markdown(text: str) -> str:
    """
    Escape characters for Telegram Markdown V2 formatting
    """
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)
    
# ---------------------------
# Telegram API helpers
# ---------------------------
def _post(url, json_payload=None, files=None, timeout=10):
    try:
        resp = requests.post(url, json=json_payload, files=files, timeout=timeout)
        try:
            print(resp.json())
            return resp.json()
        except Exception:
            print(f"""{"ok": False, "error": "invalid_json_resp", "status_code": resp.status_code, "text": resp.text}""")
            return {"ok": False, "error": "invalid_json_resp", "status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send_api(bot_token: str, method: str, payload: dict):
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    return _post(url, json_payload=payload)

# send_message runs in background (fast webhook)

# synchronous sends — we need the returned message object to extract new file_id
def send_document(bot_token: str, chat_id: int, document: str, caption: Optional[str] = None, reply_markup=None):
    payload = {"chat_id": chat_id, "document": document}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup.to_dict() if hasattr(reply_markup, "to_dict") else reply_markup
    return send_api(bot_token, "sendDocument", payload)

def send_photo(bot_token: str, chat_id: int, photo: str, caption: Optional[str] = None, reply_markup=None):
    payload = {"chat_id": chat_id, "photo": photo}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup.to_dict() if hasattr(reply_markup, "to_dict") else reply_markup
    return send_api(bot_token, "sendPhoto", payload)

def send_video(bot_token: str, chat_id: int, video: str, caption: Optional[str] = None, reply_markup=None):
    payload = {"chat_id": chat_id, "video": video}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup.to_dict() if hasattr(reply_markup, "to_dict") else reply_markup
    return send_api(bot_token, "sendVideo", payload)

def send_audio(bot_token: str, chat_id: int, audio: str, caption: Optional[str] = None, reply_markup=None):
    payload = {"chat_id": chat_id, "audio": audio}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup.to_dict() if hasattr(reply_markup, "to_dict") else reply_markup
    return send_api(bot_token, "sendAudio", payload)

def delete_message(bot_token: str, chat_id: int, message_id: int):
    try:
        send_api(bot_token, "deleteMessage", {"chat_id": chat_id, "message_id": message_id})
    except Exception as e:
        # best-effort, ignore
        print("delete_message error:", e)

