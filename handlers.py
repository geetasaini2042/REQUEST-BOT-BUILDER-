from flask import Flask, request, jsonify
from keyboard_utils import get_root_inline_keyboard
import requests
from framework import on_callback_query, filters, edit_message_text, answer_callback_query, on_message, send_message, handle_webhook_request
from folder_utils import process_open_callback
from script import get_bot_folder
from common_data import BASE_PATH
# ============================
# /start HANDLER
# ============================
import os
import json
import requests
from pathlib import Path
from save_file_to_alt_github import save_json_to_alt_github

def get_users_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "users.json")

def ADMINS(bot_id: str) -> dict:
    admin_file = Path(BASE_PATH) / "BOT_DATA" / bot_id / "ADMINS.json"
    if not admin_file.exists():
        return {"owners": [], "admins": []}
    try:
        with admin_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            #print(data)
            owners = data.get("owner", [])
            admins = data.get("admin", [])
            return {"owners": owners, "admins": admins}
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {admin_file}: {e}")
        return {"owners": [], "admins": []}

def save_new_user(bot_token: str, user_data: dict):
    users_file = get_users_file(bot_token)
    bot_id = bot_token.split(":")[0]
    git_user_file= f"BOT_DATA/{bot_id}/users.json"
    # Load existing user IDs
    if os.path.exists(users_file):
        with open(users_file, "r", encoding="utf-8") as f:
            try:
                users = json.load(f)
            except json.JSONDecodeError:
                users = []
    else:
        users = []

    # Check if user_id already exists
    if user_data["user_id"] in users:
        print(f"User {user_data['user_id']} already exists")
        return

    # Save only user_id
    users.append(user_data["user_id"])
    with open(users_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)
    print(f"Saved new user ID: {user_data['user_id']}")

    # Notify owners/admins
    admins_dict = ADMINS(bot_id)
    owners = admins_dict["owners"]
    #print(owners)
    admins = admins_dict["admins"]
    #print(admins)

    # Owner message (clickable name)
    owner_full_name_mention = f'<a href="tg://user?id={user_data["user_id"]}">{user_data["full_name"]}</a>'
    owner_message_text = (
        f"🆕 <b>New User Joined!</b>\n"
        f"👤 Full Name: {owner_full_name_mention}\n"
        f"🔗 Username: @{user_data.get('username')}\n"
        f"🆔 User ID: {user_data.get('user_id')}"
    )

    # Admin message (plain text)
    admin_message_text = (
        f"🆕 New User Joined!\n"
        f"👤 Full Name: {user_data.get('full_name')}\n"
        f"🔗 Username: @{user_data.get('username')}\n"
        f"🆔 User ID: {user_data.get('user_id')}"
    )

    for owner_id in owners:
        send_telegram_message123(bot_token, owner_id, owner_message_text, parse_mode="HTML")
    for admin_id in admins:
        send_telegram_message123(bot_token, admin_id, admin_message_text)
    result = save_json_to_alt_github(local_json_path=users_file,github_path=git_user_file)
        
def send_telegram_message123(bot_token: str, chat_id: int, text: str, parse_mode: str = None):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        requests.post(url, json=payload, timeout=2)
    except requests.RequestException as e:
        print(f"Failed to send message to {chat_id}: {e}")

@on_message(filters.command("start") & filters.private())
def start_handler(bot_token, update, message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]

    keyboard_dict, description = get_root_inline_keyboard(bot_token, user_id)
    full_name = message["from"].get("first_name", "") + " " + message["from"].get("last_name", "")
    username = message["from"].get("username", "")

    user_data = {
        "user_id": user_id,
        "chat_id": chat_id,
        "full_name": full_name.strip(),
        "username": username
    }

    # Send description text

    # Send inline keyboard
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": description,
        "reply_markup": keyboard_dict
    }
    requests.post(url, json=payload, timeout=2)
    save_new_user(bot_token, user_data)

@on_callback_query(filters.callback_data("^open:"))
def handle_open_callback(bot_token, update, cq):
    try:
        data = cq.get("data", "")
        callback_id = cq.get("id")
        chat = cq.get("message", {}).get("chat", {})
        chat_id = chat.get("id")
        message_id = cq.get("message", {}).get("message_id")
        user = cq.get("from", {})

        # अब हम folder_utils से फ़ंक्शन कॉल करेंगे
        text, keyboard = process_open_callback(bot_token, data, user, chat_id)

        if text is not None:
            edit_message_text(bot_token, chat_id, message_id, text, reply_markup=keyboard)

        # callback को acknowledge करना ज़रूरी है
        answer_callback_query(bot_token, callback_id)
        
    except Exception as e:
        print("Error in open: callback processing:", e)
        answer_callback_query(bot_token, cq.get("id"), text="Error", show_alert=True)