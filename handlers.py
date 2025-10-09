from flask import Flask, request, jsonify
from framework import on_message, filters, send_message, handle_webhook_request
from keyboard_utils import get_root_inline_keyboard
import requests

# ============================
# /start HANDLER
# ============================

@on_message(filters.command("start") & filters.private())
def start_handler(bot_token, update, message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]

    keyboard_dict, description = get_root_inline_keyboard(bot_token, user_id)

    # Send description text

    # Send inline keyboard
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": description,
        "reply_markup": keyboard_dict
    }
    requests.post(url, json=payload, timeout=2)