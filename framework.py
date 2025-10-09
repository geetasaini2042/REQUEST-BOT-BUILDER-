import requests, threading, re
from flask import jsonify

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
    @staticmethod
    def command(cmd: str):
        return Filter(lambda m: isinstance(m.get("text", ""), str) and m.get("text", "").strip().split()[0] == f"/{cmd}")

    @staticmethod
    def regex(pattern: str):
        prog = re.compile(pattern)
        return Filter(lambda m: isinstance(m.get("text", ""), str) and bool(prog.search(m.get("text", ""))))

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


# ============================
#   DECORATOR SYSTEM
# ============================
message_handlers = []
callback_handlers = []



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
def process_update(bot_token, update):
   # """Handle updates in background"""
    #try:
        if "message" in update:
            msg = update["message"]
            for f, func in message_handlers:
                #try:
                    if f(msg):
                        func(bot_token, update, msg)
                        break  # ✅ match मिलते ही बाकी handlers skip कर दो
                #except Exception as e:
                    #print("❌ Handler error:", e)

        elif "callback_query" in update:
            cq = update["callback_query"]
            for func in callback_handlers:
                func(bot_token, update, cq)
    #except Exception as e:
       # print("❌ Update error:", e)
# ============================
#   WEBHOOK HELPER
# ============================
def handle_webhook_request(bot_token, update):
    """Return immediate OK & start background thread"""
    import threading
    threading.Thread(target=process_update, args=(bot_token, update), daemon=True).start()
    return jsonify({"status": "ok"}), 200
    
    
    
# framework.py

def on_message(filter_obj=None):
    def decorator(func):
        message_handlers.append((filter_obj or filters.all(), func))
        return func
    return decorator

def on_callback_query(filter_obj=None):
    def decorator(func):
        callback_handlers.append((filter_obj or (lambda d: True), func))
        return func
    return decorator


# -------------------------
# Telegram helper (fast)
# -------------------------
def _post(url, json_payload, timeout=3):
    try:
        requests.post(url, json=json_payload, timeout=timeout)
    except Exception as e:
        print("HTTP post error:", e)

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

def answer_callback_query(bot_token: str, callback_query_id: str, text: str = None, show_alert: bool = False):
    """Acknowledge callback to remove loading spinner"""
    def _ans():
        url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            payload["text"] = text
        _post(url, payload, timeout=3)
    threading.Thread(target=_ans, daemon=True).start()


# -------------------------
# Update processing (background)
# -------------------------
def process_update(bot_token: str, update: dict):
    """
    Called in background thread. It will:
    - run message_handlers (first-match wins)
    - or handle callback_query (special handling for 'open:' etc.)
    - or run any callback_handlers registered
    """
    try:
        # MESSAGE handling
        if "message" in update:
            msg = update["message"]
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
            data = cq.get("data", "")
            # first try callback_handlers registry (if user registered)
            handled = False
            for f, func in callback_handlers:
                try:
                    # if f is Filter or callable that accepts data or cq
                    ok = False
                    try:
                        ok = f(cq) if callable(f) else False
                    except TypeError:
                        # fallback: pass data string to f
                        ok = f(data)
                    if ok:
                        func(bot_token, update, cq)
                        handled = True
                        break
                except Exception as e:
                    print("Callback handler error:", e)

            # If not handled by custom handlers, provide built-in handling:
            if not handled:
                # built-in open: handler will be provided by folder_utils via process_open_callback
                # To avoid circular import, import here
                from folder_utils import process_open_callback
                callback_id = cq.get("id")
                chat = cq.get("message", {}).get("chat", {})
                chat_id = chat.get("id")
                message_id = cq.get("message", {}).get("message_id")
                user = cq.get("from", {})
                # If data startswith open:, call folder processor
                if isinstance(data, str) and data.startswith("open:"):
                    try:
                        text, keyboard = process_open_callback(bot_token, data, user, chat_id)
                        # edit message text
                        if text is not None:
                            edit_message_text(bot_token, chat_id, message_id, text, reply_markup=keyboard)
                        # answer callback to remove spinner
                        answer_callback_query(bot_token, callback_id)
                    except Exception as e:
                        print("Error in open: callback processing:", e)
                        answer_callback_query(bot_token, callback_id, text="Error", show_alert=True)
                else:
                    # Unhandled callback -> just acknowledge
                    answer_callback_query(bot_token, callback_id, text=None)
    except Exception as e:
        print("❌ process_update error:", e)


# -------------------------
# Webhook helper to return fast OK
# -------------------------
def handle_webhook_request(bot_token: str, update: dict):
    # respond immediately to Telegram and process update in background
    threading.Thread(target=process_update, args=(bot_token, update), daemon=True).start()
    return jsonify({"status": "ok"}), 200