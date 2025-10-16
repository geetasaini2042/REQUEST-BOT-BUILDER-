import json, uuid, threading
from typing import Union
import os, json
from typing import Union
from framework import on_callback_query, filters, edit_message_text, answer_callback_query, on_message, send_with_error_message, send_audio, send_video, send_photo, send_api, send_document, delete_message, edit_message
from framework import (
    on_message, filters,
    send_message, edit_message_text
)
from collections import defaultdict
import time
from pathlib import Path
from common_data import BASE_PATH,BASE_URL
from script import get_bot_folder, get_is_monetized
from status_filters import StatusFilter
from framework import InlineKeyboardButton, InlineKeyboardMarkup, escape_markdown
from folder_utils import generate_folder_keyboard
from save_file_to_alt_github import save_json_to_alt_github


def get_status_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "status_user.json")

def get_temp_folder(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "temp_folder.json")

def get_more_contents_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "FILE_OTHER.json")

def get_file_log_id(bot_token: str) -> int | None:
    # 🔹 FILE_LOG.json का path प्राप्त करें
    file_path = os.path.join(get_bot_folder(bot_token), "FILE_LOG.json")

    # 🔹 अगर फ़ाइल नहीं है तो कुछ भी return न करें
    if not os.path.exists(file_path):
        return None

    try:
        # 🔹 JSON फ़ाइल पढ़ें
        with open(file_path, "r") as f:
            data = json.load(f)

        # 🔹 FILE_LOGS key से वैल्यू निकालें (अगर नहीं है तो None लौटे)
        return data.get("FILE_LOGS")

    except Exception as e:
        print(f"❌ Error reading FILE_LOG.json: {e}")
        return None
def get_pre_files_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "PREMIUM_PDF.json")
def get_temp_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "temp_file.json")
def get_temp_webapp_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "temp_web_url.json")  
    
def get_temp_url_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "temp_url.json")
    
def get_data_file(bot_token: str) -> str:
    return os.path.join(get_bot_folder(bot_token), "bot_data.json")

def get_created_by_from_folder(bot_token,folder_id):
    data_file = get_data_file(bot_token)
    try:
        with open(data_file) as f:
            bot_data = json.load(f)
    except:
        return None

    def find_created_by(folder):
        if folder.get("id") == folder_id and folder.get("type") == "folder":
            return folder.get("created_by")
        for item in folder.get("items", []):
            if item.get("type") == "folder":
                result = find_created_by(item)
                if result is not None:
                    return result
        return None

    root = bot_data.get("data", {})
    return find_created_by(root)

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


def set_user_status(bot_token: str, user_id: int, status: str):
    path = get_status_file(bot_token)
    data = load_json_file(path)
    data[str(user_id)] = status
    save_json_file(path, data)


def save_temp_folder(bot_token: str, user_id: int, folder_data: dict):
    path = get_temp_folder(bot_token)
    data = load_json_file(path)
    data[str(user_id)] = folder_data
    save_json_file(path, data)


def load_bot_data(bot_token: str) -> Union[dict, list, None]:
    path = get_data_file(bot_token)
    return load_json_file(path)

# 🔍 Folder search utility
def find_folder_by_id(current_folder: dict, target_id: str):
    if current_folder.get("id") == target_id and current_folder.get("type") == "folder":
        return current_folder

    for item in current_folder.get("items", []):
        if item.get("type") == "folder":
            result = find_folder_by_id(item, target_id)
            if result:
                return result
    return None


def is_user_action_allowed(folder_id, action, bot_token):
    data_file =  get_data_file(bot_token)
    try:
        with open(data_file) as f:
            data = json.load(f)
    except:
        return False

    def find_folder(folder):
        if folder.get("id") == folder_id and folder.get("type") == "folder":
            return folder
        for item in folder.get("items", []):
            if item.get("type") == "folder":
                result = find_folder(item)
                if result:
                    return result
        return None

    root = data.get("data", {})
    folder = find_folder(root)
    if not folder:
        return False

    return action in folder.get("user_allow", [])
# 🧠 Callback: Add Folder

def ADMINS(bot_id: str) -> list:

    admin_file = Path(BASE_PATH) / "BOT_DATA" / bot_id / "ADMINS.json"

    if not admin_file.exists():
        return []

    try:
        with admin_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            owners = data.get("owner", [])
            admins = data.get("admin", [])
            return owners + admins
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {admin_file}: {e}")
        return []
@on_callback_query(filters.callback_data("^add_folder:"))
def add_folder_callback(bot_token, update, cq):
  #  try:
        bot_id = bot_token.split(":")[0]
        data = cq.get("data", "")
        callback_id = cq.get("id")
        user = cq.get("from", {})
        user_id = user.get("id")
        chat = cq.get("message", {}).get("chat", {})
        chat_id = chat.get("id")
        message_id = cq.get("message", {}).get("message_id")

        parent_id = data.split(":", 1)[1]

        # Load bot data
        full_data = load_bot_data(bot_token)
        if not full_data:
            answer_callback_query(bot_token, callback_id, text="⚠ Data file missing.", show_alert=True)
            return

        root = full_data.get("data", {})
        parent_folder = find_folder_by_id(root, parent_id)

        if not parent_folder:
            answer_callback_query(bot_token, callback_id, text="❌ Parent folder not found.", show_alert=True)
            return

        # Permissions check (placeholder functions)
        if (not is_user_action_allowed(parent_id, "add_folder", bot_token)
            and user_id not in ADMINS(str(bot_id))
            and get_created_by_from_folder(bot_token,parent_id) != user_id):
            answer_callback_query(bot_token, callback_id, text="❌ You are not allowed to add a folder.", show_alert=True)
            return

        # Save temp folder draft
        temp_data = {
            "user_id": user_id,
            "parent_id": parent_id,
            "parent_name": parent_folder["name"],
            "name": "",
            "description": "",
            "user_allow": []
        }

        save_temp_folder(bot_token, user_id, temp_data)
        set_user_status(bot_token, user_id, f"getting_folder_name:{parent_id}")

        # Edit message
        text = f"📁 Adding new folder under: *{parent_folder['name']}*\n\n✍️ Please send the *name* of the new folder."
        edit_message_text(bot_token, chat_id, message_id, text)

        answer_callback_query(bot_token, callback_id)

   # except Exception as e:
     #   print("Error in add_folder_callback:", e)
       # answer_callback_query(bot_token, cq.get("id"), text="⚠ Error occurred.", show_alert=True)
       


@on_message(filters.private() & filters.text()  & StatusFilter("getting_folder_name"))
def receive_folder_name(bot_token, update, msg):
    user_id = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()

    # Load current status
    status_file = get_status_file(bot_token)
    status_data = load_json_file(status_file)
    status = status_data.get(str(user_id), "")
    parent_id = status.split(":", 1)[1]

    # Load temp folder
    temp_file = get_temp_folder(bot_token)
    temp_data = load_json_file(temp_file)
    folder_data = temp_data.get(str(user_id), {})
    folder_data["name"] = text

    # Update temp folder with name
    temp_data[str(user_id)] = folder_data
    save_json_file(temp_file, temp_data)

    # Update status
    status_data[str(user_id)] = f"getting_folder_description:{parent_id}"
    save_json_file(status_file, status_data)

    # Reply
    chat_id = msg.get("chat", {}).get("id")
    from framework import send_message
    send_message(bot_token, chat_id,
                 f"✅ नाम सेव हो गया: {text}\nअब नया folder का विवरण (description) भेजें।")
                 


@on_message(filters.private() & filters.text() & StatusFilter("getting_folder_description"))
def receive_folder_description(bot_token, update, msg):
    user_id = msg["from"]["id"]
    text = msg.get("text", "").strip()

    # If markdown entities exist, keep formatted text; else escape
    if msg.get("entities"):
        formatted = text  # assuming already markdown
    else:
        formatted = escape_markdown(text)

    description = formatted

    # ---------------------------
    # Load status
    # ---------------------------
    status_file = get_status_file(bot_token)
    status_data = load_json_file(status_file)
    status = status_data.get(str(user_id), "")
    parent_id = status.split(":", 1)[1] if ":" in status else "root"

    # ---------------------------
    # Load temp folder data
    # ---------------------------
    temp_file = get_temp_folder(bot_token)
    temp_data = load_json_file(temp_file)
    folder_data = temp_data.get(str(user_id), {})
    folder_data["description"] = description
    temp_data[str(user_id)] = folder_data
    save_json_file(temp_file, temp_data)

    # ---------------------------
    # Update status to permissions
    # ---------------------------
    status_data[str(user_id)] = f"setting_folder_permissions:{parent_id}"
    save_json_file(status_file, status_data)

    # ---------------------------
    # Show toggling buttons
    # ---------------------------
    buttons = [
        [
            InlineKeyboardButton("➕ Add File ❌", callback_data="toggle:add_file"),
            InlineKeyboardButton("📁 Add Folder ❌", callback_data="toggle:add_folder")
        ],
        [
            InlineKeyboardButton("🔗 Add URL ❌", callback_data="toggle:add_url"),
            InlineKeyboardButton("🧩 Add WebApp ❌", callback_data="toggle:add_webapp")
        ],
        [
            InlineKeyboardButton("✅ Confirm & Save", callback_data="confirm_folder")
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    chat_id = msg["chat"]["id"]
    send_message(
        bot_token,
        chat_id,
        "📄 विवरण सेव हो गया!\nअब आप नीचे से जो सुविधाएँ allow करनी हैं उन्हें ✅ पर टॉगल करें:",
        reply_markup=keyboard
    )
    

@on_callback_query(filters.callback_data("^toggle:"))
def toggle_permission_handler(bot_token, update, cq):
    user_id = str(cq["from"]["id"])
    permission = cq.get("data", "").split(":", 1)[1]  # e.g., add_file

    # ---------------------------
    # Load temp folder
    # ---------------------------
    temp_file = get_temp_folder(bot_token)
    temp_data = load_json_file(temp_file)
    folder = temp_data.get(user_id)

    if not folder:
        callback_id = cq.get("id")
        answer_callback_query(bot_token, callback_id, text="❌ कोई फोल्डर डेटा नहीं मिला।", show_alert=True)
        return

    # ---------------------------
    # Toggle permission in user_allow
    # ---------------------------
    current = folder.get("user_allow", [])
    if permission in current:
        current.remove(permission)
    else:
        current.append(permission)
    folder["user_allow"] = current
    temp_data[user_id] = folder
    save_json_file(temp_file, temp_data)

    # ---------------------------
    # Build updated buttons
    # ---------------------------
    def btn(name, perm):
        mark = "✅" if perm in current else "❌"
        return InlineKeyboardButton(f"{name} {mark}", callback_data=f"toggle:{perm}")

    buttons = [
        [btn("➕ Add File", "add_file"), btn("📁 Add Folder", "add_folder")],
        [btn("🔗 Add URL", "add_url"), btn("🧩 Add WebApp", "add_webapp")],
        [InlineKeyboardButton("✅ Confirm & Save", callback_data="confirm_folder")]
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    # ---------------------------
    # Edit message text
    # ---------------------------
    chat_id = cq.get("message", {}).get("chat", {}).get("id")
    message_id = cq.get("message", {}).get("message_id")
    callback_id = cq.get("id")

    edit_message_text(
        bot_token,
        chat_id,
        message_id,
        "✅ चयन अपडेट हो गया!\nनीचे से टॉगल करें और अंत में Confirm करें।",
        reply_markup=keyboard
    )

    # Acknowledge callback to remove spinner
    answer_callback_query(bot_token, callback_id)
    
@on_callback_query(filters.callback_data("^confirm_folder$"))
def confirm_and_save_folder(bot_token, update, cq):
    user_id = str(cq["from"]["id"])
    callback_id = cq.get("id")
    bot_id = bot_token.split(":")[0]
    data_file_path=get_data_file(bot_token)

    # ---------------------------
    # Load temp folder
    # ---------------------------
    temp_file = get_temp_folder(bot_token)
    temp_data = load_json_file(temp_file)
    folder_data = temp_data.get(user_id)

    if not folder_data:
        return answer_callback_query(bot_token, callback_id, "❌ Temp folder missing.", show_alert=True)

    parent_id = folder_data["parent_id"]

    # Permission check
    if (not is_user_action_allowed(parent_id, "add_folder", bot_token) and
        int(user_id) not in ADMINS(bot_id) and
        get_created_by_from_folder(bot_token,parent_id) != int(user_id)):
        return answer_callback_query(bot_token, callback_id, "❌ You are not allowed to add a folder in this folder.", show_alert=True)

    # ---------------------------
    # Load bot_data.json
    # ---------------------------
    bot_data = load_json_file(data_file_path)
    if not bot_data:
        return answer_callback_query(bot_token, callback_id, "❌ bot_data.json missing.", show_alert=True)

    root = bot_data.get("data", {})
    parent = find_folder_by_id(root, parent_id)
    if not parent:
        return answer_callback_query(bot_token, callback_id, "❌ Parent folder not found.", show_alert=True)

    # ---------------------------
    # Prepare new folder item
    # ---------------------------
    existing = parent.get("items", [])
    total = len(existing)
    row = total+1
    col = 0

    new_item = {
        "id": f"item_{uuid.uuid4().hex[:6]}",
        "name": folder_data["name"],
        "description": folder_data["description"],
        "type": "folder",
        "created_by": int(user_id),
        "parent_id": parent_id,
        "user_allow": folder_data.get("user_allow", []),
        "items": [],
        "row": row,
        "column": col
    }

    # Add to parent
    parent.setdefault("items", []).append(new_item)
    save_json_file(data_file_path, bot_data)

    # ---------------------------
    # Clean temp and status
    # ---------------------------
    temp_data.pop(user_id, None)
    save_json_file(temp_file, temp_data)

    status_file = get_status_file(bot_token)
    status_data = load_json_file(status_file)
    status_data.pop(user_id, None)
    save_json_file(status_file, status_data)
    git_data_file= f"BOT_DATA/{bot_id}/bot_data.json"
    save_json_to_alt_github(data_file_path,git_data_file)

    # ---------------------------
    # Generate keyboard
    # ---------------------------
    kb = generate_folder_keyboard(parent, int(user_id), bot_id)

    chat_id = cq.get("message", {}).get("chat", {}).get("id")
    message_id = cq.get("message", {}).get("message_id")

    # Show "Please wait..." first
   # edit_message_text(bot_token, chat_id, message_id, "Please wait...")
    #time.sleep(5)
    # ---------------------------
    # Edit with final message + keyboard
    # ---------------------------
    edit_message_text(
        bot_token,
        chat_id,
        message_id,
        f"📁 Folder '{new_item['name']}' saved successfully!",
        reply_markup=kb
    )

    # Acknowledge callback to remove spinner
    answer_callback_query(bot_token, callback_id)
@on_callback_query(filters.callback_data("^add_url:"))
def add_url_callback(bot_token, update, cq):
    folder_id = cq.get("data", "").split(":")[1]
    user_id = str(cq["from"]["id"])
    callback_id = cq.get("id")
    bot_id = bot_token.split(":")[0]

    # Permission check
    if (not is_user_action_allowed(folder_id, "add_url", bot_token) and
        int(user_id) not in ADMINS(bot_id) and
        get_created_by_from_folder(bot_token,folder_id) != int(user_id)):
        return answer_callback_query(bot_token, callback_id, "❌ You are not allowed to add a URL in this folder.", show_alert=True)

    # ---------------------------
    # Update status
    # ---------------------------
    status_data = load_json_file(get_status_file(bot_token))
    if status_data is None:
        status_data = {}

    status_data[user_id] = f"getting_url_name:{folder_id}"
    save_json_file(get_status_file(bot_token), status_data)

    # ---------------------------
    # Initialize temp URL data
    # ---------------------------
    temp_data = load_json_file(get_temp_url_file(bot_token))
    if temp_data is None:
        temp_data = {}

    temp_data[user_id] = {"folder_id": folder_id}
    save_json_file(get_temp_url_file(bot_token), temp_data)

    # ---------------------------
    # Edit message
    # ---------------------------
    chat_id = cq.get("message", {}).get("chat", {}).get("id")
    message_id = cq.get("message", {}).get("message_id")
    edit_message_text(bot_token, chat_id, message_id, "Please Send a title for your URL (Example: 'Click Here')")

    # Acknowledge callback
    answer_callback_query(bot_token, callback_id)
    
@on_message(filters.private() & filters.text() & StatusFilter("getting_url_name:"))
def receive_url_name(bot_token, update, msg):
    user_id = str(msg["from"]["id"])
    url_name = msg.get("text", "").strip()

    # ---------------------------
    # Load temp URL data
    # ---------------------------
    temp_data = load_json_file(get_temp_url_file(bot_token))
    if temp_data is None:
        temp_data = {}

    if user_id not in temp_data:
        temp_data[user_id] = {}

    temp_data[user_id]["name"] = url_name
    save_json_file(get_temp_url_file(bot_token), temp_data)

    # ---------------------------
    # Update status
    # ---------------------------
    status_data = load_json_file(get_status_file(bot_token))
    folder_id = status_data[user_id].split(":")[1]
    status_data[user_id] = f"getting_url:{folder_id}"
    save_json_file(get_status_file(bot_token), status_data)

    # ---------------------------
    # Send reply
    # ---------------------------
    chat_id = msg["chat"]["id"]
    send_message(bot_token, chat_id, "Now Send a valid URL (Example: https://...)")

def get_owner_id(bot_token: str) -> str:
    bot_id = bot_token.split(":")[0]
    file_path = f"{BASE_PATH}/BOT_DATA/{bot_id}/ADMINS.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            owner_ids = data.get("owner", [])
            if not owner_ids:
                return None  # अगर owner key खाली या missing है
            return owner_ids[0]  # पहला owner ID return करेगा
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None    
@on_message(filters.private() & filters.text() & StatusFilter("getting_url:"))
def receive_url(bot_token, update, msg):
    user_id = str(msg["from"]["id"])
    url = msg.get("text", "").strip()

    # ---------------------------
    # Optional: check URL by sending button to admin
    # ---------------------------
    keyboard = [[{"text": "🌐 Checking url", "url": url}]]
    try:
        send_with_error_message(bot_token, int(get_owner_id(bot_token)), "🧩 Url Button:", reply_markup={"inline_keyboard": keyboard})
    except Exception:
        chat_id = msg["chat"]["id"]
        send_message(bot_token, chat_id, "❌ Please send a valid and reachable URL.")
        return

    # ---------------------------
    # Save URL to temp
    # ---------------------------
    temp_data = load_json_file(get_temp_url_file(bot_token)) or {}
    if user_id not in temp_data:
        temp_data[user_id] = {}
    temp_data[user_id]["url"] = url
    save_json_file(get_temp_url_file(bot_token), temp_data)

    # ---------------------------
    # Update status
    # ---------------------------
    status_data = load_json_file(get_status_file(bot_token)) or {}
    folder_id = status_data[user_id].split(":")[1]
    status_data[user_id] = f"getting_caption_url:{folder_id}"
    save_json_file(get_status_file(bot_token), status_data)

    # ---------------------------
    # Prompt user for caption
    # ---------------------------
    chat_id = msg["chat"]["id"]
    send_message(bot_token, chat_id, f"Now send a caption for your URL :\n{url}\n (Example: This is a demo caption)")
    
@on_message(filters.private() & filters.text() & StatusFilter("getting_caption_url:"))
def receive_url_caption(bot_token, update, msg):
    user_id = str(msg["from"]["id"])
    text = msg.get("text", "").strip()
    caption = escape_markdown(text)  # framework function
    data_file_path=get_data_file(bot_token)
    bot_id= bot_token.split(":")[0]
    # ---------------------------
    # Load temp URL data
    # ---------------------------
    temp_data = load_json_file(get_temp_url_file(bot_token)) or {}
    url_data = temp_data.get(user_id, {})
    url_data["caption"] = caption
    folder_id = url_data.get("folder_id")

    # ---------------------------
    # Load bot_data.json
    # ---------------------------
    bot_data = load_json_file(data_file_path) or {}
    root = bot_data.get("data", {})
    parent = find_folder_by_id(root, folder_id)

    if not parent:
        chat_id = msg["chat"]["id"]
        send_message(bot_token, chat_id, "❌ Parent folder नहीं मिला।")
        return

    # ---------------------------
    # Prepare new URL item
    # ---------------------------
    existing_items = parent.get("items", [])
    max_row = max([item.get("row", 0) for item in existing_items], default=-1)

    new_item = {
        "id": f"url_{uuid.uuid4().hex[:12]}",
        "type": "url",
        "name": url_data["name"],
        "url": url_data["url"],
        "caption": caption,
        "created_by": int(user_id),
        "row": max_row + 1,
        "column": 0
    }

    parent.setdefault("items", []).append(new_item)
    save_json_file(data_file_path, bot_data)

    # ---------------------------
    # Clean temp and status
    # ---------------------------
    temp_data.pop(user_id, None)
    save_json_file(get_temp_url_file(bot_token), temp_data)

    status_data = load_json_file(get_status_file(bot_token)) or {}
    status_data.pop(user_id, None)
    save_json_file(get_status_file(bot_token), status_data)
    git_data_file= f"BOT_DATA/{bot_id}/bot_data.json"
    save_json_to_alt_github(data_file_path,git_data_file)

    # ---------------------------
    # Generate keyboard and reply
    # ---------------------------
    kb = generate_folder_keyboard(parent, int(user_id), bot_token)
    chat_id = msg["chat"]["id"]
    send_message(bot_token, chat_id, "🔗 URL Added Successfully✅️", reply_markup=kb)
    
# =============================
# 📁 Edit Menu Handler
# =============================
@on_callback_query(filters.callback_data(r"^edit_menu:"))
def edit_menu_handler(bot_token, update, callback_query):
    folder_id = callback_query["data"].split(":")[1]
    user_id = callback_query["from"]["id"]
    data_file_path=get_data_file(bot_token)
    data = load_json_file(data_file_path)
    bot_id = bot_token.split(":")[0]
    if not data:
        answer_callback_query(bot_token, callback_query["id"], "❌ Data file missing", show_alert=True)
        return

    # 🔍 Find folder recursively
    def find_folder(folder, fid):
        if folder.get("id") == fid and folder.get("type") == "folder":
            return folder
        for item in folder.get("items", []):
            if item.get("type") == "folder":
                found = find_folder(item, fid)
                if found:
                    return found
        return None

    root = data.get("data", {})
    folder = find_folder(root, folder_id)

    if not folder:
        answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found", show_alert=True)
        return

    # 🔐 Access Check
    if user_id not in ADMINS(bot_id) and folder.get("created_by") != user_id:
        answer_callback_query(bot_token, callback_query["id"], "❌ Not allowed", show_alert=True)
        return

    # 📦 Prepare buttons
    buttons = []
    for item in folder.get("items", []):
        name = item.get("name", "❓")
        item_id = item.get("id")
        buttons.append([{"text": f"✏️ {name}", "callback_data": f"edit_item:{folder_id}:{item_id}"}])

    buttons.append([{"text": "🔙Back", "callback_data": f"edit1_item1:{folder_id}"}])

    edit_message_text(
        bot_token,
        chat_id=callback_query["message"]["chat"]["id"],
        message_id=callback_query["message"]["message_id"],
        text="🛠 Select an item to edit:\n\nPlease send a /update command to save data after you edits.",
        reply_markup={"inline_keyboard": buttons}
    )


# =============================
# 🧩 Edit Item Options
# =============================
@on_callback_query(filters.callback_data("^edit_item:"))
def edit_item_handler(bot_token, update, callback_query):
    _, folder_id, item_id = callback_query["data"].split(":")
    user_id = callback_query["from"]["id"]
    data_file_path=get_data_file(bot_token)
    data = load_json_file(data_file_path)
    bot_id = bot_token.split(":")[0]
    if not data:
        answer_callback_query(bot_token, callback_query["id"], "❌ Data missing", show_alert=True)
        return

    def find_folder(folder, fid):
        if folder.get("id") == fid and folder.get("type") == "folder":
            return folder
        for item in folder.get("items", []):
            if item.get("type") == "folder":
                found = find_folder(item, fid)
                if found:
                    return found
        return None

    folder = find_folder(data.get("data", {}), folder_id)
    if not folder:
        answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found", show_alert=True)
        return

    # 🔎 Find the item
    item = next((i for i in folder.get("items", []) if i["id"] == item_id), None)
    if not item:
        answer_callback_query(bot_token, callback_query["id"], "❌ Item not found", show_alert=True)
        return

    # 🔐 Access Check
    if user_id not in ADMINS(bot_id) and item.get("created_by") != user_id:
        answer_callback_query(bot_token, callback_query["id"], "❌ Not allowed", show_alert=True)
        return

    # 🧰 Options
    buttons = [
        [{"text": "✏️ Rename", "callback_data": f"rename:{folder_id}:{item_id}"}],
        [{"text": "🔀 Move", "callback_data": f"move_menu:{folder_id}:{item_id}"}],
        [{"text": "📄 Copy", "callback_data": f"copy_item:{folder_id}:{item_id}"}],
        [{"text": "🗑 Delete", "callback_data": f"delete:{folder_id}:{item_id}"}],
        [{"text": "🔙Back", "callback_data": f"edit_menu:{folder_id}"}]
    ]

    edit_message_text(
        bot_token,
        chat_id=callback_query["message"]["chat"]["id"],
        message_id=callback_query["message"]["message_id"],
        text=f"🧩 Edit Options for: {item.get('name', 'Unnamed')}\n\nPlease send a /update command to save data after you edits.",
        reply_markup={"inline_keyboard": buttons}
    )


# =============================
# 🔙 Back to Folder Edit Root
# =============================
@on_callback_query(filters.callback_data("^edit1_item1:"))
def edit1_item1_handler(bot_token, update, callback_query):
    folder_id = callback_query["data"].split(":")[1]
    data_file_path=get_data_file(bot_token)
    data = load_json_file(data_file_path)
    if not data:
        answer_callback_query(bot_token, callback_query["id"], "❌ Data missing", show_alert=True)
        return

    def find_folder(folder, fid):
        if folder.get("id") == fid and folder.get("type") == "folder":
            return folder
        for item in folder.get("items", []):
            if item.get("type") == "folder":
                found = find_folder(item, fid)
                if found:
                    return found
        return None

    folder = find_folder(data.get("data", {}), folder_id)
    if not folder:
        answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found", show_alert=True)
        return

    default_item = next(
        (item for item in folder.get("items", []) if item.get("row") == 0 and item.get("column") == 0),
        None
    )

    # ✅ Prepare buttons
    if not default_item:
        buttons = [
            [
                {"text": "✏️ Edit Items", "callback_data": f"edit_menu:{folder_id}"},
                {"text": "📝 Description", "callback_data": f"update_description:{folder_id}"}
            ],
            [{"text": "🔻Edit Allow", "callback_data": f"update_folder_allow:{folder_id}"}],
            [{"text": "👑 Take Ownership", "callback_data": f"update_created_by:{folder_id}"}],
            [{"text": "🔙Back", "callback_data": f"open:{folder_id}"}]
        ]
    else:
        item_id = default_item["id"]
        buttons = [
            [
                {"text": "✏️ Edit Items", "callback_data": f"edit_menu:{folder_id}"},
                {"text": "📝 Description", "callback_data": f"update_description:{folder_id}"}
            ],
            [
                {"text": "🔀 Move", "callback_data": f"move_menu:{folder_id}:{item_id}"},
                {"text": "🔻Edit Allow", "callback_data": f"update_folder_allow:{folder_id}"}
            ],
            [{"text": "👑 Take Ownership", "callback_data": f"update_created_by:{folder_id}"}],
            [{"text": "🔙Back", "callback_data": f"open:{folder_id}"}]
        ]

    edit_message_text(
        bot_token,
        chat_id=callback_query["message"]["chat"]["id"],
        message_id=callback_query["message"]["message_id"],
        text="🛠 What would you like to do?\n\nPlease send a /update command to save data after you edits.",
        reply_markup={"inline_keyboard": buttons}
    )
#@on_callback_query(filters.callback_data("^edit1_item1:"))    
@on_callback_query(filters.callback_data("^update_created_by:"))
def update_created_by_handler(bot_token, update, callback_query):
    # 🔹 Basic extraction
    print(update)
    data = callback_query.get("data", "")
    user = callback_query.get("from", {})
    user_id = user.get("id")
    message = callback_query.get("message", {})
    bot_id = bot_token.split(":")[0]
    # 🔹 Folder ID निकालना
    parts = data.split(":")
    print(parts)
    if len(parts) < 2:
        print("❌ Invalid callback data.")
        answer_callback_query(bot_token, callback_query["id"], "❌ Invalid callback data.", True)
        return

    folder_id = parts[1]
    print(folder_id)

    # ✅ Access Check (Admins only)
    admins = ADMINS(bot_id)
    if user_id not in admins:
        answer_callback_query(bot_token, callback_query["id"], "❌ Only admins can change ownership.", True)
        print("❌ Only admins can change ownership.")
        return

    # 🔄 Load bot_data.json (bot-specific)
    print("I am working")
    data_file = get_data_file(bot_token)
    try:
        with open(data_file, "r") as f:
            data_json = json.load(f)
    except:
        answer_callback_query(bot_token, callback_query["id"], "❌ Failed to load bot_data.json", True)
        return

    # 🔍 Recursive folder finder
    def find_folder(folder):
        if folder.get("id") == folder_id:
            return folder
        for item in folder.get("items", []):
            if item.get("type") == "folder":
                result = find_folder(item)
                if result:
                    return result
        return None

    root = data_json.get("data", {})
    folder = find_folder(root)
    print("I am working")
    if not folder:
        answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found.", True)
        return

    # ✏️ Update created_by
    folder["created_by"] = user_id

    # 💾 Save back
    with open(data_file, "w") as f:
        json.dump(data_json, f, indent=2)

    # ✅ Success message
    answer_callback_query(bot_token, callback_query["id"], "✅ Ownership updated successfully.\n\nPlease send a /update command to save data after you edits.", True)
    print("Transfered")

    # 🔘 Updated folder view
    kb = generate_folder_keyboard(folder, user_id, bot_id)

    # 📝 Edit existing message text
    edit_message_text(
        bot_token,
        chat_id=message["chat"]["id"],
        message_id=message["message_id"],
        text=f"🆕 This folder is now owned by you (User ID: `{user_id}`)",
        reply_markup=kb
    )
@on_callback_query(filters.callback_data("^update_description:"))
def update_description_prompt(bot_token, update, query):
    data = query.get("data", "")
    folder_id = data.split(":")[1] if ":" in data else None
    user_id = str(query.get("from", {}).get("id"))
    data_file =get_data_file(bot_token)
    status_user_file = get_status_file(bot_token)

    if not folder_id or not user_id:
        return send_message(bot_token, 6150091802, "❌ Invalid callback data or user ID.")

    # 🔄 यूज़र का status अपडेट करें
    if os.path.exists(status_user_file):
        with open(status_user_file, "r") as f:
            try:
                status_data = json.load(f)
            except:
                status_data = {}
    else:
        status_data = {}

    status_data[user_id] = f"updating_description:{folder_id}"

    with open(status_user_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # 🔍 मौजूदा विवरण (description) लोड करें
    if not os.path.exists(data_file):
        send_message(bot_token, user_id, "❌ डेटा फ़ाइल नहीं मिली।")
        return

    with open(data_file, "r") as f:
        bot_data = json.load(f)

    # 🔎 Recursive फ़ोल्डर खोज फ़ंक्शन
    def find_folder(folder, fid):
        if folder.get("id") == fid and folder.get("type") == "folder":
            return folder
        for item in folder.get("items", []):
            if item.get("type") == "folder":
                found = find_folder(item, fid)
                if found:
                    return found
        return None

    folder = find_folder(bot_data.get("data", {}), folder_id)
    if not folder:
        answer_callback_query(bot_token, query["id"], "❌ फ़ोल्डर नहीं मिला।", show_alert=True)
        return

    current_description = folder.get("description", "कोई विवरण उपलब्ध नहीं है।")

    edit_message_text(
        bot_token,
        query["message"]["chat"]["id"],
        query["message"]["message_id"],
        f"Please Send a New Description:\n\n"
        f"*Current Description*\n`{current_description}`\n\nPlease send a /update command to save data after you edits."
    )

# ✅ Webhook-based version of updating description

@on_message(filters.private() & filters.text() & StatusFilter("updating_description"))
def receive_new_description(bot_token, update, msg):
    user_id = str(msg["from"]["id"])
    text = msg.get("text", "").strip()
    bot_id = bot_token.split(":")[0]

    # 🔄 Paths based on bot_token
    data_file = get_data_file(bot_token)
    status_user_file = get_status_file(bot_token)

    # 📦 Load status
    try:
        with open(status_user_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}

    status_value = status_data.get(user_id, "")
    if ":" not in status_value:
        send_message(bot_token, user_id, "❌ Invalid folder status.")
        return

    folder_id = status_value.split(":", 1)[1]

    # 📂 Load bot_data
    try:
        with open(data_file, "r") as f:
            bot_data = json.load(f)
    except:
        send_message(bot_token, user_id, "❌ bot_data.json not found.")
        return

    # 🔍 Folder finder
    def find_folder(folder, fid):
        if folder.get("id") == fid and folder.get("type") == "folder":
            return folder
        for item in folder.get("items", []):
            if item.get("type") == "folder":
                found = find_folder(item, fid)
                if found:
                    return found
        return None

    folder = find_folder(bot_data.get("data", {}), folder_id)
    if not folder:
        send_message(bot_token, user_id, "❌ Folder not found.")
        return

    # 📝 Markdown escape
    formatted = escape_markdown(text)

    # 🧩 Update folder description
    folder["description"] = formatted

    # 💾 Save data
    with open(data_file, "w") as f:
        json.dump(bot_data, f, indent=2)

    # 🧹 Clear user status
    status_data.pop(user_id, None)
    with open(status_user_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # ✅ Generate updated keyboard
    
    
    kb = generate_folder_keyboard(folder, int(user_id), bot_id)
    

    # 📩 Reply
    send_message(
        bot_token,
        user_id,
        f"📝 *Description updated successfully!*\n\n{formatted}\n\nPlease send a /update command to save data after you edits.",
        reply_markup=kb
    )

@on_callback_query(filters.callback_data("^rename:"))
def rename_item_callback(bot_token, update, callback_query):
    data = callback_query.get("data", "")
    parts = data.split(":")
    if len(parts) < 3:
        answer_callback_query(bot_token, callback_query["id"], "❌ Invalid callback data.", True)
        return

    folder_id, item_id = parts[1:]
    user = callback_query.get("from", {})
    user_id = str(user.get("id"))
    message = callback_query.get("message", {})

    # 🔄 Save user status
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}

    status_data[user_id] = f"renaming:{folder_id}:{item_id}"
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # 🔍 Find current item
    data_file = get_data_file(bot_token)
    try:
        with open(data_file, "r") as f:
            bot_data = json.load(f)
    except:
        answer_callback_query(bot_token, callback_query["id"], "❌ Failed to load bot data.", True)
        return

    def find_folder(folder, fid):
        if folder.get("id") == fid and folder.get("type") == "folder":
            return folder
        for i in folder.get("items", []):
            if i.get("type") == "folder":
                found = find_folder(i, fid)
                if found:
                    return found
        return None

    folder = find_folder(bot_data.get("data", {}), folder_id)
    if not folder:
        answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found.", True)
        return

    item = next((i for i in folder.get("items", []) if i.get("id") == item_id), None)
    if not item:
        answer_callback_query(bot_token, callback_query["id"], "❌ Item not found.", True)
        return

    current_name = item.get("name", "Unnamed")

    # 🔤 Ask user for new name
    edit_message_text(
        bot_token,
        chat_id=message["chat"]["id"],
        message_id=message["message_id"],
        text=f"📝 Please send the new name for this item.\n\n📄 *Current Name*:\n`{current_name}`\n\nPlease send a /update command to save data after you edits."
    )

@on_message(filters.private() & filters.text() & StatusFilter("renaming:"))
def rename_text_handler(bot_token, update, msg):
    user = msg.get("from", {})
    user_id = str(user.get("id"))
    new_name = msg.get("text", "").strip()
    bot_id = bot_token.split(":")[0]

    # 🔄 Load status
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}

    status = status_data.get(user_id, "")
    parts = status.split(":")
    if len(parts) != 3:
        send_message(bot_token, user_id, "❌ Status error.")
        return

    _, folder_id, item_id = parts

    # 🔍 Load bot data
    data_file = get_data_file(bot_token)
    try:
        with open(data_file, "r") as f:
            bot_data = json.load(f)
    except:
        send_message(bot_token, user_id, "❌ Failed to load bot data.")
        return

    def find_folder(folder, fid):
        if folder.get("id") == fid:
            return folder
        for i in folder.get("items", []):
            if i.get("type") == "folder":
                found = find_folder(i, fid)
                if found:
                    return found
        return None

    folder = find_folder(bot_data.get("data", {}), folder_id)
    if not folder:
        send_message(bot_token, user_id, "❌ Folder not found.")
        return

    item = next((i for i in folder.get("items", []) if i.get("id") == item_id), None)
    if not item:
        send_message(bot_token, user_id, "❌ Item not found.")
        return

    # 🔤 Update name
    item["name"] = new_name

    with open(data_file, "w") as f:
        json.dump(bot_data, f, indent=2)

    # 🧹 Clear status
    status_data.pop(user_id, None)
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)

    kb = generate_folder_keyboard(folder, int(user_id), bot_id)
    send_message(bot_token, user_id, "✅ Name Renamed\n\nPlease send a /update command to save data after you edits.", reply_markup=kb)

@on_callback_query(filters.callback_data("^delete:"))
def delete_item_confirm(bot_token, update, callback_query):
    data = callback_query.get("data", "")
    parts = data.split(":")
    if len(parts) < 3:
        answer_callback_query(bot_token, callback_query["id"], "❌ Invalid callback data.", True)
        return

    folder_id, item_id = parts[1:]
    user = callback_query.get("from", {})
    user_id = str(user.get("id"))
    message = callback_query.get("message", {})

    # 🔄 Save status
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}

    status_data[user_id] = f"deleting:{folder_id}:{item_id}"
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # ⚠️ Ask user to confirm deletion
    edit_message_text(
        bot_token,
        chat_id=message["chat"]["id"],
        message_id=message["message_id"],
        text=(
            f"❗ To delete this item, please send the folder ID:\n\n"
            f"🔐 `{folder_id}`\n\n"
            f"⚠️ Warning: Once deleted, this item **CANNOT be restored**. Proceed with caution."
        )
    )


@on_message(filters.private() & filters.text() & StatusFilter("deleting"))
def delete_item_final(bot_token, update, msg):
    user = msg.get("from", {})
    user_id = str(user.get("id"))
    entered_text = msg.get("text", "").strip()
    bot_id = bot_token.split(":")[0]

    # 🔄 Load status
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}

    status = status_data.get(user_id, "")
    parts = status.split(":")
    if len(parts) != 3:
        send_message(bot_token, user_id, "❌ Invalid status.")
        return

    _, folder_id, item_id = parts

    # ❌ Compare folder ID
    if entered_text != folder_id:
        status_data.pop(user_id, None)
        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)
        send_message(bot_token, user_id, "❌ File deleting canceled due to wrong folder ID!")
        return

    # 🔍 Load main data
    data_file = get_data_file(bot_token)
    try:
        with open(data_file, "r") as f:
            bot_data = json.load(f)
    except:
        send_message(bot_token, user_id, "❌ Failed to load bot data.")
        return

    def find_folder(folder, fid):
        if folder.get("id") == fid:
            return folder
        for i in folder.get("items", []):
            if i.get("type") == "folder":
                found = find_folder(i, fid)
                if found:
                    return found
        return None

    folder = find_folder(bot_data.get("data", {}), folder_id)
    if not folder:
        send_message(bot_token, user_id, "❌ Folder not found.")
        return

    # 🗑 Remove the item
    folder["items"] = [i for i in folder.get("items", []) if i.get("id") != item_id]

    # 💾 Save updated bot data
    with open(data_file, "w") as f:
        json.dump(bot_data, f, indent=2)

    # 🧹 Clear status
    status_data.pop(user_id, None)
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)

    kb = generate_folder_keyboard(folder, int(user_id), bot_id)
    send_message(bot_token, user_id, "✅ Item deleted\n\nPlease send a /update command to save data after you edits.", reply_markup=kb)
    
@on_callback_query(filters.callback_data("^move_menu:"))
def move_menu_handler(bot_token, update, callback_query):
    data = callback_query.get("data", "")
    parts = data.split(":")
    if len(parts) < 3:
        answer_callback_query(bot_token, callback_query, "❌ Invalid callback data.", True)
        return

    folder_id, item_id = parts[1:]
    user = callback_query.get("from", {})
    user_id = user.get("id")
    message = callback_query.get("message", {})
    bot_id = bot_token.split(":")[0]

    # 🔐 Access check
    if user_id not in ADMINS(bot_id) and get_created_by_from_folder(bot_token, folder_id) != user_id:
        answer_callback_query(bot_token, callback_query["id"], "❌ You are not allowed to move items in this folder.", True)
        return

    # 🔄 Load bot data
    data_file = get_data_file(bot_token)
    try:
        with open(data_file, "r") as f:
            data = json.load(f)
    except:
        answer_callback_query(bot_token, callback_query["id"], "❌ Failed to load bot data.", True)
        return

    # 🔍 Find folder recursively
    def find_folder(folder, fid):
        if folder.get("id") == fid:
            return folder
        for i in folder.get("items", []):
            if i.get("type") == "folder":
                found = find_folder(i, fid)
                if found:
                    return found
        return None

    folder = find_folder(data.get("data", {}), folder_id)
    if not folder:
        answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found.", True)
        return

    # 🔎 Validate selected item
    item_ids = [i.get("id") for i in folder.get("items", [])]
    if item_id not in item_ids:
        answer_callback_query(bot_token, callback_query["id"], "❌ Item not found.", True)
        return

    # 🧩 Build layout grid
    layout = defaultdict(dict)
    for i in folder.get("items", []):
        r, c = i.get("row", 0), i.get("column", 0)
        icon = "♻️" if i.get("id") == item_id else {"folder": "", "file": "", "url": "", "webapp": ""}.get(i.get("type"), "❓")
        if i.get("id") == item_id:
            btn = InlineKeyboardButton(f"{icon} {i.get('name')}", callback_data="ignore")
        else:
            btn = InlineKeyboardButton(f"{icon} {i.get('name')}", callback_data=f"move_menu:{folder_id}:{i.get('id')}")
        layout[r][c] = btn

    # 🏗 Build grid
    grid = []
    for r in sorted(layout):
        row_buttons = [layout[r][c] for c in sorted(layout[r])]
        grid.append(row_buttons)

    # ⬅️⬆️⬇️➡️ Movement buttons
    move_row = [
        InlineKeyboardButton("⬅️", callback_data=f"move_left:{folder_id}:{item_id}"),
        InlineKeyboardButton("⬆️", callback_data=f"move_up:{folder_id}:{item_id}"),
        InlineKeyboardButton("⬇️", callback_data=f"move_down:{folder_id}:{item_id}"),
        InlineKeyboardButton("➡️", callback_data=f"move_right:{folder_id}:{item_id}"),
    ]
    grid.append(move_row)

    # 🔙 Back/DONE button
    grid.append([InlineKeyboardButton("DONE✔️", callback_data=f"edit1_item1:{folder_id}")])

    # ✏️ Edit message
    edit_message_text(
        bot_token,
        chat_id=message["chat"]["id"],
        message_id=message["message_id"],
        text="🔄 Move the selected item (♻️):\n\nPlease send a /update command to save data after you edits.",
        reply_markup=InlineKeyboardMarkup(grid)
    )
def load_data(bot_token):
    data_file = get_data_file(bot_token)
    with open(data_file, "r") as f:
        return json.load(f)

def save_data(data, bot_token):
    data_file = get_data_file(bot_token)
    with open(data_file, "w") as f:
        json.dump(data, f, indent=2)
def compact_items(items):
    # Row और column के अनुसार sort
    items = sorted(items, key=lambda x: (x["row"], x["column"]))
    new_items = []
    row_map = {}
    row_counter = 0

    # Unique row नंबर को 0,1,2... में remap करो
    for row in sorted(set(i["row"] for i in items)):
        row_map[row] = row_counter
        row_counter += 1

    for item in items:
        item["row"] = row_map[item["row"]]
        new_items.append(item)

    # Final sorted compact list वापस भेजो
    return sorted(new_items, key=lambda x: (x["row"], x["column"]))

@on_callback_query(filters.callback_data("^move_up:"))
def move_up_handler(bot_token, update, callback_query):
    data_str = callback_query.get("data", "")
    parts = data_str.split(":")
    if len(parts) < 3:
        return answer_callback_query(bot_token, callback_query["id"], "❌ Invalid callback data.", True)

    folder_id, item_id = parts[1:]
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    try:
        # 🔄 Load data
        data_file = get_data_file(bot_token)
        with open(data_file, "r") as f:
            data = json.load(f)

        def find_folder(folder, fid):
            if folder.get("id") == fid:
                return folder
            for i in folder.get("items", []):
                if i.get("type") == "folder":
                    found = find_folder(i, fid)
                    if found:
                        return found
            return None

        folder = find_folder(data.get("data", {}), folder_id)
        if not folder:
            return answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found!", True)

        items = folder.get("items", [])
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            return answer_callback_query(bot_token, callback_query["id"], "❌ Item not found!", True)

        current_row = item.get("row", 0)
        current_col = item.get("column", 0)

        same_row_items = [i for i in items if i.get("row") == current_row and i.get("id") != item_id]

        if same_row_items:
            # बाकियों को push नीचे
            for i in items:
                if i.get("id") != item_id and i.get("row", 0) >= current_row:
                    i["row"] += 1
            item["column"] = 0

            # Column conflict avoid
            by_position = {}
            for i in items:
                key = (i["row"], i["column"])
                while key in by_position:
                    i["column"] += 1
                    key = (i["row"], i["column"])
                by_position[key] = i["id"]

        else:
            if current_row > 0:
                # ऊपर वाली row में shift
                above_items = [i for i in items if i.get("row", 0) == current_row - 1]
                existing_cols = [i.get("column", 0) for i in above_items]
                item["row"] = current_row - 1
                item["column"] = max(existing_cols, default=-1) + 1
            else:
                # row == 0 और अकेला
                max_row = max((i.get("row", 0) for i in items if i.get("id") != item_id), default=0)
                old_row = item.get("row", 0)
                item["row"] = max_row + 1
                item["column"] = 0

                # ऊपर वालों को -1 करो
                for i in items:
                    if i.get("id") != item_id and i.get("row", 0) < old_row:
                        i["row"] -= 1

        # 🔄 Compact final layout
        folder["items"] = compact_items(items)

        # 💾 Save
        save_data(data, bot_token)

        # 🔁 Call move_menu again to refresh
        callback_query["data"] = f"move_menu:{folder_id}:{item_id}"
        move_menu_handler(bot_token, update, callback_query)

    except Exception as e:
        answer_callback_query(bot_token, callback_query["id"], "⚠️ Please Try Again!", True)

@on_callback_query(filters.callback_data("^move_down:"))
def move_down_handler(bot_token, update, callback_query):
    data_str = callback_query.get("data", "")
    parts = data_str.split(":")
    if len(parts) < 3:
        return answer_callback_query(bot_token, callback_query["id"], "❌ Invalid callback data.", True)

    folder_id, item_id = parts[1:]
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    try:
        # 🔄 Load bot data
        data_file = get_data_file(bot_token)
        with open(data_file, "r") as f:
            data = json.load(f)

        def find_folder(folder, fid):
            if folder.get("id") == fid:
                return folder
            for i in folder.get("items", []):
                if i.get("type") == "folder":
                    found = find_folder(i, fid)
                    if found:
                        return found
            return None

        folder = find_folder(data.get("data", {}), folder_id)
        if not folder:
            return answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found!", True)

        items = folder.get("items", [])
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            return answer_callback_query(bot_token, callback_query["id"], "❌ Item not found!", True)

        current_row = item.get("row", 0)
        current_col = item.get("column", 0)

        same_row_others = [i for i in items if i.get("row", 0) == current_row and i.get("id") != item_id]
        max_row = max([i.get("row", 0) for i in items], default=0)

        if same_row_others:
            # ✅ Same row में और items हैं
            for i in items:
                if i.get("row", 0) > current_row:
                    i["row"] += 1  # नीचे की rows shift

            item["row"] = current_row + 1
            item["column"] = 0  # नीचे नई row की col 0

            if current_col == 0:
                for i in items:
                    if i.get("row", 0) == current_row and i.get("column", 0) > 0:
                        i["column"] -= 1
        else:
            # ✅ अकेला row में
            if current_row < max_row:
                below_items = [i for i in items if i.get("row", 0) == current_row + 1]
                cols = [i.get("column", 0) for i in below_items]
                item["row"] = current_row + 1
                item["column"] = max(cols, default=-1) + 1
            else:
                # ✅ already last row
                for i in items:
                    if i.get("id") != item_id:
                        i["row"] += 1
                item["row"] = 0
                item["column"] = 0

        # 🔄 Compact layout
        folder["items"] = compact_items(items)

        # 💾 Save
        save_data(data, bot_token)

        # 🔁 Refresh menu
        callback_query["data"] = f"move_menu:{folder_id}:{item_id}"
        move_menu_handler(bot_token, update, callback_query)

    except Exception as e:
        answer_callback_query(bot_token, callback_query["id"], "⚠️ Please Try Again!", True)
  
@on_callback_query(filters.callback_data("^move_left"))
def move_left_handler(bot_token, update, callback_query):
    data_str = callback_query.get("data", "")
    parts = data_str.split(":")
    if len(parts) < 3:
        return answer_callback_query(bot_token, callback_query["id"], "❌ Invalid callback data.", True)

    folder_id, item_id = parts[1:]
    try:
        # Load bot data
        data_file = get_data_file(bot_token)
        with open(data_file, "r") as f:
            data = json.load(f)

        def find_folder(folder, fid):
            if folder.get("id") == fid:
                return folder
            for i in folder.get("items", []):
                if i.get("type") == "folder":
                    found = find_folder(i, fid)
                    if found:
                        return found
            return None

        folder = find_folder(data.get("data", {}), folder_id)
        if not folder:
            return answer_callback_query(bot_token, callback_query["id"], "❌ Folder Not Found!", True)

        items = folder.get("items", [])
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            return answer_callback_query(bot_token, callback_query["id"], "❌ No Item Found!", True)

        row = item.get("row", 0)
        col = item.get("column", 0)

        if col == 0:
            return answer_callback_query(bot_token, callback_query["id"], "❌ No Space on the left", True)

        left_item = next((i for i in items if i.get("row", 0) == row and i.get("column", 0) == col - 1), None)
        if left_item:
            left_item["column"] += 1
        item["column"] -= 1

        folder["items"] = compact_items(items)
        save_data(data, bot_token)

        callback_query["data"] = f"move_menu:{folder_id}:{item_id}"
        move_menu_handler(bot_token, update, callback_query)

    except Exception:
        answer_callback_query(bot_token, callback_query["id"], "⚠️ Error: Please Try Again!", True)


@on_callback_query(filters.callback_data("^move_right"))
def move_right_handler(bot_token, update, callback_query):
    data_str = callback_query.get("data", "")
    parts = data_str.split(":")
    if len(parts) < 3:
        return answer_callback_query(bot_token, callback_query["id"], "❌ Invalid callback data.", True)

    folder_id, item_id = parts[1:]
    try:
        data_file = get_data_file(bot_token)
        with open(data_file, "r") as f:
            data = json.load(f)

        def find_folder(folder, fid):
            if folder.get("id") == fid:
                return folder
            for i in folder.get("items", []):
                if i.get("type") == "folder":
                    found = find_folder(i, fid)
                    if found:
                        return found
            return None

        folder = find_folder(data.get("data", {}), folder_id)
        if not folder:
            return answer_callback_query(bot_token, callback_query["id"], "❌ Folder not found!", True)

        items = folder.get("items", [])
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            return answer_callback_query(bot_token, callback_query["id"], "❌ Item not found!", True)

        row = item.get("row", 0)
        col = item.get("column", 0)

        row_items = [i for i in items if i.get("row", 0) == row]
        max_col = max([i.get("column", 0) for i in row_items], default=0)

        if col == max_col:
            return answer_callback_query(bot_token, callback_query["id"], "❌ No space on the right", True)

        right_item = next((i for i in row_items if i.get("column", 0) == col + 1), None)
        if right_item:
            right_item["column"] -= 1
        item["column"] += 1

        folder["items"] = compact_items(items)
        save_data(data, bot_token)

        callback_query["data"] = f"move_menu:{folder_id}:{item_id}"
        move_menu_handler(bot_token, update, callback_query)

    except Exception:
        answer_callback_query(bot_token, callback_query["id"], "⚠️ Please Try Again!", True)
        
@on_callback_query(filters.callback_data("^add_webapp"))
def add_webapp_callback(bot_token, update, callback_query):
    data_str = callback_query.get("data", "")
    bot_id = bot_token.split(":")[0]
    parts = data_str.split(":")
    if len(parts) < 2:
        return answer_callback_query(bot_token, callback_query["id"], "❌ Invalid callback data.", True)

    folder_id = parts[1]
    user_id = str(callback_query["from"]["id"])

    if (not is_user_action_allowed(folder_id, "add_webapp", bot_token)
        and int(user_id) not in ADMINS(bot_id)
        and get_created_by_from_folder(bot_token, folder_id) != int(user_id)):
        return answer_callback_query(bot_token, callback_query["id"], "❌ You are not allowed to add a web app in this folder.", True)

    # 🔄 Status Set
    status_user_file = get_status_file(bot_token)
    try:
        with open(status_user_file, "r") as f:
            content = f.read().strip()
            status_data = json.loads(content) if content else {}
    except:
        status_data = {}

    status_data[user_id] = f"getting_webapp_name:{folder_id}"
    with open(status_user_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # 🔧 Temp init
    temp_webapp_file = get_temp_webapp_file(bot_token)
    try:
        with open(temp_webapp_file, "r") as f:
            content = f.read().strip()
            temp_data = json.loads(content) if content else {}
    except:
        temp_data = {}

    temp_data[user_id] = {"folder_id": folder_id}
    with open(temp_webapp_file, "w") as f:
        json.dump(temp_data, f, indent=2)

    edit_message_text(bot_token, callback_query["message"]["chat"]["id"],
                      callback_query["message"]["message_id"],
                      "Please send a title for your web app (Example : 'OPEN APP')")


@on_message(filters.private()  & filters.text()  & StatusFilter("getting_webapp_name"))
def receive_webapp_name(bot_token, update, message):
    user_id = str(message["from"]["id"])
    webapp_name = message["text"].strip()

    temp_webapp_file = get_temp_webapp_file(bot_token)
    try:
        with open(temp_webapp_file, "r") as f:
            content = f.read().strip()
            temp_data = json.loads(content) if content else {}
    except:
        temp_data = {}

    if user_id not in temp_data:
        temp_data[user_id] = {}
    temp_data[user_id]["name"] = webapp_name
    with open(temp_webapp_file, "w") as f:
        json.dump(temp_data, f, indent=2)

    status_user_file = get_status_file(bot_token)
    with open(status_user_file, "r") as f:
        status_data = json.load(f)

    folder_id = status_data[user_id].split(":")[1]
    status_data[user_id] = f"getting_webapp:{folder_id}"
    with open(status_user_file, "w") as f:
        json.dump(status_data, f)

    send_message(bot_token, message["chat"]["id"], "Now send a url of your webapp (Example : https://...)")
    
@on_message(filters.private()  & filters.text()  & StatusFilter("getting_webapp"))
def receive_webapp(bot_token, update, message):
    user_id = str(message["from"]["id"])
    webapp = message["text"].strip()

    # WebApp button preview (sent to admin or test user)
    keyboard = {
        "inline_keyboard": [[{"text": "🌐 Open WebApp", "web_app": {"url": webapp}}]]
    }

    try:
        send_with_error_message(bot_token, int(get_owner_id(bot_token)), "🧩 WebApp Button:", reply_markup=keyboard)
    except Exception:
        return send_message(bot_token, message["chat"]["id"], "❌ Please send a valid and reachable URL.")

    # Temp storage
    temp_webapp_file = get_temp_webapp_file(bot_token)
    try:
        with open(temp_webapp_file, "r") as f:
            temp_data = json.load(f)
    except:
        temp_data = {}

    if user_id not in temp_data:
        temp_data[user_id] = {}
    temp_data[user_id]["webapp"] = webapp

    with open(temp_webapp_file, "w") as f:
        json.dump(temp_data, f, indent=2)

    # Update status
    status_user_file = get_status_file(bot_token)
    with open(status_user_file, "r") as f:
        status_data = json.load(f)
    folder_id = status_data[user_id].split(":")[1]
    status_data[user_id] = f"getting_caption_webapp:{folder_id}"
    with open(status_user_file, "w") as f:
        json.dump(status_data, f)

    send_message(bot_token, message["chat"]["id"], "Now send a caption for your Webapp.")


@on_message(filters.private()  & filters.text()  & StatusFilter("getting_caption_webapp"))
def receive_webapp_caption(bot_token, update, message):
    user_id = str(message["from"]["id"])
    caption = message["text"].strip()
    data_file = get_data_file(bot_token)
    bot_id = bot_token.split(":")[0]

    temp_webapp_file = get_temp_webapp_file(bot_token)
    try:
        with open(temp_webapp_file, "r") as f:
            temp_data = json.load(f)
    except:
        temp_data = {}

    webapp_data = temp_data.get(user_id, {})
    webapp_data["caption"] = caption
    folder_id = webapp_data.get("folder_id")

    # Load main bot data
    with open(data_file, "r") as f:
        bot_data = json.load(f)

    root = bot_data.get("data", {})
    parent = find_folder_by_id(root, folder_id)
    if not parent:
        return send_message(bot_token, message["chat"]["id"], "❌ Parent folder नहीं मिला।")

    # Calculate max row
    existing_items = parent.get("items", [])
    max_row = max([item.get("row", 0) for item in existing_items], default=-1)

    # New webapp item
    new_item = {
        "id": f"webapp_{uuid.uuid4().hex[:12]}",
        "type": "webapp",
        "name": webapp_data["name"],
        "url": webapp_data["webapp"],
        "caption": caption,
        "created_by": int(user_id),
        "row": max_row + 1,
        "column": 0
    }
    parent.setdefault("items", []).append(new_item)

    with open(data_file, "w") as f:
        json.dump(bot_data, f, indent=2)

    # Cleanup temp & status
    temp_data.pop(user_id, None)
    with open(temp_webapp_file, "w") as f:
        json.dump(temp_data, f)

    status_user_file = get_status_file(bot_token)
    with open(status_user_file, "r") as f:
        status_data = json.load(f)
    status_data.pop(user_id, None)
    with open(status_user_file, "w") as f:
        json.dump(status_data, f)

    # Send confirmation
    chat_id = message["chat"]["id"]
    git_data_file= f"BOT_DATA/{bot_id}/bot_data.json"
    save_json_to_alt_github(data_file,git_data_file)
    #send_message(bot_token, chat_id, "🧩 WebApp सफलतापूर्वक जोड़ा गया ✅")
    kb = generate_folder_keyboard(parent, int(user_id), bot_id)
    send_message(bot_token, chat_id, "🧩 WebApp सफलतापूर्वक जोड़ा गया ✅", reply_markup=kb)

@on_callback_query(filters.callback_data("^add_file"))
def add_file_callback(bot_token,update, callback_query):
    data = callback_query["data"]
    folder_id = data.split(":")[1]
    bot_id = bot_token.split(":")[0]
    user_id = str(callback_query["from"]["id"])

    # 🟢 Optional startup message
    #send_startup_message_once()

    # 🔒 Access Check
    if (
        not is_user_action_allowed(folder_id, "add_file", bot_token)
        and int(user_id) not in ADMINS(bot_id)
        and get_created_by_from_folder(bot_token, folder_id) != int(user_id)
    ):
        return answer_callback_query(
            bot_token,
            callback_query["id"],
            "❌ You are not allowed to add a file in this folder.",
            True,
        )

    # 🧩 Load or Initialize Status File
    status_user_file = get_status_file(bot_token)
    try:
        with open(status_user_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}

    status_data[user_id] = f"waiting_file_doc:{folder_id}"
    with open(status_user_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # 📂 Load or Initialize Temp File JSON
    temp_file_json = get_temp_file(bot_token)
    try:
        with open(temp_file_json, "r") as f:
            temp_data = json.load(f)
    except:
        temp_data = {}

    if user_id not in temp_data:
        temp_data[user_id] = {"folder_id": folder_id, "files": {}}
    else:
        temp_data[user_id]["folder_id"] = folder_id
        temp_data[user_id].setdefault("files", {})

    with open(temp_file_json, "w") as f:
        json.dump(temp_data, f, indent=2)

    # 📨 Edit message to ask user
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    edit_message_text(bot_token, chat_id, message_id, "Please Send Document(s)..")
def get_new_file_id_from_resp(resp: dict):
    # resp is Telegram API JSON response: {"ok": True, "result": { ... message ...}}
    if not resp or not resp.get("ok"):
        return None
    result = resp.get("result", {})
    # try common keys
    for key in ("document", "photo", "video", "audio", "voice"):
        if key in result:
            if key == "photo":
                # photo is list
                photos = result["photo"]
                if isinstance(photos, list) and photos:
                    return photos[-1].get("file_id")
            else:
                return result[key].get("file_id")
    # sometimes message may have 'document' nested under result.message (rare) - fallback scan
    def scan_for_file_id(obj):
        if isinstance(obj, dict):
            if "file_id" in obj:
                return obj["file_id"]
            for v in obj.values():
                found = scan_for_file_id(v)
                if found:
                    return found
        if isinstance(obj, list):
            for el in obj:
                found = scan_for_file_id(el)
                if found:
                    return found
        return None
    return scan_for_file_id(result)



def get_file_channel_id(bot_token: str) -> str:
    bot_id = bot_token.split(":")[0]
    file_path = f"{BASE_PATH}/BOT_DATA/{bot_id}/ADDITIONAL_DATA.json"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            file_channel_id = data.get("FILE_CHANNEL_ID", None)
            if file_channel_id:
              print(file_channel_id)
              return file_channel_id  # अगर key missing है तो None return होगा
            print("NON")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
        
@on_message(filters.private() & StatusFilter("waiting_file_doc") & (filters.document() | filters.photo() | filters.video() | filters.audio()))
def receive_any_media(bot_token, update, msg):
    """
    msg is the message dict from Telegram webhook.
    bot_token is injected by process_update before handlers are called.
    """
    bot_id = bot_token.split(":")[0]
    try:
        user_id = str(msg.get("from", {}).get("id"))
        if not user_id:
            return

        # status file and folder_id
        status_file = get_status_file(bot_token)
        try:
            with open(status_file, "r") as f:
                status_data = json.load(f)
        except:
            status_data = {}
        status_val = status_data.get(user_id, "")
        if ":" not in status_val:
            send_message(bot_token, msg["chat"]["id"], "❌ Invalid status.")
            return
        folder_id = status_val.split(":", 1)[1]

        # permission check
        if (not is_user_action_allowed(folder_id, "add_file", bot_token)
            and int(user_id) not in ADMINS(bot_id)
            and get_created_by_from_folder(bot_token, folder_id) != int(user_id)):
            send_message(bot_token, msg["chat"]["id"], "❌ You are not allowed to add a file in this folder.")
            return

        # detect media
        media_type = None
        file_name = "Unnamed"
        original_file_id = None

        if "document" in msg:
            media_type = "document"
            original_file_id = msg["document"].get("file_id")
            file_name = msg["document"].get("file_name") or "Document"
        elif "video" in msg:
            media_type = "video"
            original_file_id = msg["video"].get("file_id")
            file_name = msg["video"].get("file_name") or "Video"
        elif "audio" in msg:
            media_type = "audio"
            original_file_id = msg["audio"].get("file_id")
            file_name = msg["audio"].get("file_name") or "Audio"
        elif "photo" in msg:
            media_type = "photo"
            # highest quality photo is last
            original_file_id = msg["photo"][-1].get("file_id")
            file_name = "Image"

        if not original_file_id:
            send_message(bot_token, msg["chat"]["id"], "❌ Supported media not found.")
            return
        FILE_LOGS = get_file_channel_id(bot_token)
        if not FILE_LOGS:
          send_message(bot_token, msg["chat"]["id"], "You haven't added a database channel yet. Please add a database channel first.\nTo add a database channel please visit the bot @BotixHubBot")
          return
        # forward/save to FILE_LOGS chat to get persistent file_id
        # FILE_LOGS should be defined (chat id)
        print(original_file_id)
        if media_type == "photo":
            resp = send_photo(bot_token, FILE_LOGS, photo=original_file_id)
        elif media_type == "video":
            resp = send_video(bot_token, FILE_LOGS, video=original_file_id)
        elif media_type == "audio":
            resp = send_audio(bot_token, FILE_LOGS, audio=original_file_id)
        else:
            resp = send_document(bot_token, FILE_LOGS, document=original_file_id)

        new_file_id = get_new_file_id_from_resp(resp)
        print(new_file_id)
        if not new_file_id:
            send_message(bot_token, msg["chat"]["id"], f"You haven't added me in database channel as admin. Please add me as a admin in database channel\n\nCHANNEL ID: {FILE_LOGS}\n\nIf you Want to change this database channel please visit bot @BotixHubBot")
            return

        caption = msg.get("caption") or file_name
        sub_type = media_type
        file_id = new_file_id

        # load temp file for this bot
        temp_file = get_temp_file(bot_token)
        try:
            with open(temp_file, "r") as f:
                temp_data = json.load(f)
        except:
            temp_data = {}

        if user_id not in temp_data:
            temp_data[user_id] = {"folder_id": folder_id, "files": {}}

        file_uuid = uuid.uuid4().hex[:12]
        temp_data[user_id]["files"][file_uuid] = {
            "id": file_uuid,
            "type": "file",
            "sub_type": sub_type,
            "name": file_name,
            "file_id": file_id,
            "caption": caption,
            "visibility": "private",
            "row": 0,
            "column": 0
        }

        with open(temp_file, "w") as f:
            json.dump(temp_data, f, indent=2)

        # prepare buttons as InlineKeyboardMarkup
        buttons = [
            [InlineKeyboardButton("✏️ Rename", callback_data=f"rename_file:{file_uuid}")],
            [InlineKeyboardButton("📝 Edit Caption", callback_data=f"edit_file_caption:{file_uuid}")],
            [InlineKeyboardButton("👁 Visibility: Public", callback_data=f"toggle_visibility:{file_uuid}")],
            [InlineKeyboardButton("FILE IS UNDER A USER", callback_data=f"add_premium_owner:{file_uuid}")],
            [
                InlineKeyboardButton("✅ Confirm Upload", callback_data=f"confirm_file:{file_uuid}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_file:{file_uuid}")
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        # reply to user with correct send_* call (background or immediate)
        if sub_type == "document":
            # send_document returns response dict; we'll call it in background to not block user too long
            threading.Thread(target=send_document, args=(bot_token, msg["chat"]["id"], file_id, caption, keyboard), daemon=True).start()
        elif sub_type == "photo":
            threading.Thread(target=send_photo, args=(bot_token, msg["chat"]["id"], file_id, caption, keyboard), daemon=True).start()
        elif sub_type == "video":
            threading.Thread(target=send_video, args=(bot_token, msg["chat"]["id"], file_id, caption, keyboard), daemon=True).start()
        elif sub_type == "audio":
            threading.Thread(target=send_audio, args=(bot_token, msg["chat"]["id"], file_id, caption, keyboard), daemon=True).start()
        else:
            send_message(bot_token, msg["chat"]["id"], "❌ Unknown media type.")

    except Exception as e:
        # safe fallback
        print("Error in receive_any_media:", e)
        send_message(bot_token, msg.get("chat", {}).get("id"), "⚠️ Server error, try again.")
        
# helper: delete message (webhook style)

# -------------------------
# rename_file prompt (callback)
# -------------------------
@on_callback_query(filters.callback_data("^rename_file:"))
def rename_file_prompt(bot_token, update, callback_query):
    """
    callback_query is dict from webhook.
    """
    data = callback_query.get("data", "")
    parts = data.split(":", 1)
    if len(parts) < 2:
        return answer_callback_query(bot_token, callback_query.get("id"), "❌ Invalid callback data.", True)

    file_uuid = parts[1]
    user_id = str(callback_query.get("from", {}).get("id"))

    temp_file = get_temp_file(bot_token)
    try:
        with open(temp_file, "r") as f:
            temp_data = json.load(f)
    except:
        temp_data = {}

    file_entry = temp_data.get(user_id, {}).get("files", {}).get(file_uuid)
    if not file_entry:
        return answer_callback_query(bot_token, callback_query.get("id"), "❌ File not found.", True)

    current_name = file_entry.get("name", "Unnamed")
    file_id = file_entry.get("file_id")
    sub_type = file_entry.get("sub_type", "document")

    # Update status -> file_renaming:<uuid>
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}
    status_data[user_id] = f"file_renaming:{file_uuid}"
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # Delete original message (best-effort)
    msg = callback_query.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    if chat_id and message_id:
        try:
            delete_message(bot_token, chat_id, message_id)
        except Exception:
            pass

    # Send the media back to user with prompt asking for new name
    prompt_caption = f"📄 Current File Name:\n`{current_name}`\n\n✏️ Please send the *new name* for this file."
    keyboard = None  # no buttons while asking for name

    if sub_type == "document":
        send_document(bot_token, chat_id, document=file_id, caption=prompt_caption)
    elif sub_type == "photo":
        send_photo(bot_token, chat_id, photo=file_id, caption=prompt_caption)
    elif sub_type == "video":
        send_video(bot_token, chat_id, video=file_id, caption=prompt_caption)
    elif sub_type == "audio":
        send_audio(bot_token, chat_id, audio=file_id, caption=prompt_caption)
    else:
        # fallback: just send text prompt
        send_message(bot_token, chat_id, prompt_caption, parse_mode="Markdown")


# -------------------------
# rename_file receive (user sends new name)
# -------------------------
@on_message(filters.private() & filters.text() & StatusFilter("file_renaming:"))
def rename_file_receive(bot_token, update, msg):
    """
    msg is message dict from webhook.
    """
    user_id = str(msg.get("from", {}).get("id"))
    new_name = msg.get("text", "").strip()
    chat_id = msg.get("chat", {}).get("id")

    # Load status to get file_uuid
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}

    status_val = status_data.get(user_id, "")
    if ":" not in status_val:
        return send_message(bot_token, chat_id, "❌ Status error or expired.")

    _, file_uuid = status_val.split(":", 1)

    # Load temp file
    temp_file = get_temp_file(bot_token)
    try:
        with open(temp_file, "r") as f:
            temp_data = json.load(f)
    except:
        temp_data = {}

    file_entry = temp_data.get(user_id, {}).get("files", {}).get(file_uuid)
    if not file_entry:
        return send_message(bot_token, chat_id, "❌ File not found in your temp data.")

    # Update the in-temp name
    file_entry["name"] = new_name

    # Save temp file
    temp_data[user_id]["files"][file_uuid] = file_entry
    with open(temp_file, "w") as f:
        json.dump(temp_data, f, indent=2)

    # Clear status
    status_data.pop(user_id, None)
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # Prepare caption and buttons
    file_id = file_entry.get("file_id")
    caption = (
        f"File Renamed Successfully\n\n"
        f"**New Name** : `{new_name}`\n"
        f"**Caption** : `{file_entry.get('caption') or new_name}`\n"
        f"**File ID** : `{file_id}`\n"
    )

    visibility = file_entry.get("visibility", "private")
    sub_type = file_entry.get("sub_type", "document")

    buttons = [
        [InlineKeyboardButton("✏️ Rename", callback_data=f"rename_file:{file_uuid}")],
        [InlineKeyboardButton("📝 Edit Caption", callback_data=f"edit_file_caption:{file_uuid}")],
        [InlineKeyboardButton(f"👁 Visibility: {visibility}", callback_data=f"toggle_visibility:{file_uuid}")],
        [InlineKeyboardButton("FILE IS UNDER A USER", callback_data=f"add_premium_owner:{file_uuid}")],
        [
            InlineKeyboardButton("✅ Confirm Upload", callback_data=f"confirm_file:{file_uuid}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_file:{file_uuid}")
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # Send updated media back to user with buttons
    if sub_type == "document":
        send_document(bot_token, chat_id, document=file_id, caption=caption, reply_markup=keyboard)
    elif sub_type == "photo":
        send_photo(bot_token, chat_id, photo=file_id, caption=caption, reply_markup=keyboard)
    elif sub_type == "video":
        send_video(bot_token, chat_id, video=file_id, caption=caption, reply_markup=keyboard)
    elif sub_type == "audio":
        send_audio(bot_token, chat_id, audio=file_id, caption=caption, reply_markup=keyboard)
    else:
        send_message(bot_token, chat_id, "❌ Unknown file type.", reply_markup=keyboard)
        
# -------------------------
# edit_file_caption -> webhook version
# -------------------------
@on_callback_query(filters.callback_data("^edit_file_caption:"))
def edit_file_caption_prompt(bot_token, update, callback_query):
    """
    callback_query: dict from webhook
    """
    data = callback_query.get("data", "")
    parts = data.split(":", 1)
    if len(parts) < 2:
        return answer_callback_query(bot_token, callback_query.get("id"), "❌ Invalid callback data.", True)

    file_uuid = parts[1]
    user_id = str(callback_query.get("from", {}).get("id"))

    # Load temp file
    temp_file = get_temp_file(bot_token)
    try:
        with open(temp_file, "r") as f:
            temp_data = json.load(f)
    except:
        temp_data = {}

    file_entry = temp_data.get(user_id, {}).get("files", {}).get(file_uuid)
    if not file_entry:
        return answer_callback_query(bot_token, callback_query.get("id"), "❌ File not found.", True)

    current_caption = file_entry.get("caption", file_entry.get("name", "No caption"))
    file_id = file_entry.get("file_id")
    sub_type = file_entry.get("sub_type", "document")

    # Update status to file_captioning:<uuid>
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}
    status_data[user_id] = f"file_captioning:{file_uuid}"
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # Acknowledge callback (remove spinner)
    answer_callback_query(bot_token, callback_query.get("id"))

    # Delete original message (best-effort)
    msg = callback_query.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    if chat_id and message_id:
        try:
            delete_message(bot_token, chat_id, message_id)
        except Exception:
            pass

    # Send the media back to user with prompt asking for new caption
    prompt_caption = f"📝 Current Caption:\n`{escape_markdown(str(current_caption))}`\n\nNow, please send the *new caption* for this file."

    # Use background thread for reply to avoid blocking webhook
    if sub_type == "document":
        threading.Thread(target=send_document, args=(bot_token, chat_id, file_id, prompt_caption), kwargs={"reply_markup": None}, daemon=True).start()
    elif sub_type == "photo":
        threading.Thread(target=send_photo, args=(bot_token, chat_id, file_id, prompt_caption), kwargs={"reply_markup": None}, daemon=True).start()
    elif sub_type == "video":
        threading.Thread(target=send_video, args=(bot_token, chat_id, file_id, prompt_caption), kwargs={"reply_markup": None}, daemon=True).start()
    elif sub_type == "audio":
        threading.Thread(target=send_audio, args=(bot_token, chat_id, file_id, prompt_caption), kwargs={"reply_markup": None}, daemon=True).start()
    else:
        send_message(bot_token, chat_id, "📝 Please send the new caption for the file.")


# -------------------------
# edit_caption_receive -> webhook version
# -------------------------
@on_message(filters.private() & filters.text() & StatusFilter("file_captioning:"))
def edit_caption_receive(bot_token, update, msg):
    """
    msg is the message dict from webhook.
    """
    user_id = str(msg.get("from", {}).get("id"))
    chat_id = msg.get("chat", {}).get("id")
    raw_text = msg.get("text", "").strip()

    # format/escape caption for safety
    if raw_text:
        # preserve markdown-like formatting but escape problematic chars
        new_caption = escape_markdown(raw_text)
    else:
        new_caption = ""

    # Load status to get file_uuid
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}

    status_val = status_data.get(user_id, "")
    if ":" not in status_val:
        send_message(bot_token, chat_id, "❌ Status error or expired.")
        return

    _, file_uuid = status_val.split(":", 1)

    # Load temp data
    temp_file = get_temp_file(bot_token)
    try:
        with open(temp_file, "r") as f:
            temp_data = json.load(f)
    except:
        temp_data = {}

    file_entry = temp_data.get(user_id, {}).get("files", {}).get(file_uuid)
    if not file_entry:
        send_message(bot_token, chat_id, "❌ File not found.")
        return

    # Update caption
    file_entry["caption"] = new_caption

    # Save tempfile
    temp_data[user_id]["files"][file_uuid] = file_entry
    with open(temp_file, "w") as f:
        json.dump(temp_data, f, indent=2)

    # Clear status
    status_data.pop(user_id, None)
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)

    # Prepare response caption and buttons
    file_id = file_entry.get("file_id")
    name = file_entry.get("name")
    visibility = file_entry.get("visibility", "private")
    sub_type = file_entry.get("sub_type", "document")

    caption_text = (
        f"Caption Updated Successfully\n\n"
        f"Name : `{escape_markdown(str(name))}`\n"
        f"New Caption : `{escape_markdown(str(new_caption))}`\n"
        f"File ID : `{file_id}`"
    )

    buttons = [
        [InlineKeyboardButton("✏️ Rename", callback_data=f"rename_file:{file_uuid}")],
        [InlineKeyboardButton("📝 Edit Caption", callback_data=f"edit_file_caption:{file_uuid}")],
        [InlineKeyboardButton(f"👁 Visibility: {visibility}", callback_data=f"toggle_visibility:{file_uuid}")],
        [InlineKeyboardButton("FILE IS UNDER A USER", callback_data=f"add_premium_owner:{file_uuid}")],
        [
            InlineKeyboardButton("✅ Confirm Upload", callback_data=f"confirm_file:{file_uuid}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_file:{file_uuid}")
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # Send updated media back to user with buttons (background)
    if sub_type == "document":
        threading.Thread(target=send_document, args=(bot_token, chat_id, file_id, caption_text, keyboard), daemon=True).start()
    elif sub_type == "photo":
        threading.Thread(target=send_photo, args=(bot_token, chat_id, file_id, caption_text, keyboard), daemon=True).start()
    elif sub_type == "video":
        threading.Thread(target=send_video, args=(bot_token, chat_id, file_id, caption_text, keyboard), daemon=True).start()
    elif sub_type == "audio":
        threading.Thread(target=send_audio, args=(bot_token, chat_id, file_id, caption_text, keyboard), daemon=True).start()
    else:
        send_message(bot_token, chat_id, caption_text, reply_markup=keyboard)
        
@on_callback_query(filters.callback_data("^toggle_visibility:"))
def toggle_visibility_callback(bot_token, update, callback_query):
    """
    Webhook-style handler.
    callback_query is a dict (from Telegram webhook).
    """
    callback_id = callback_query.get("id")
    user = callback_query.get("from", {})
    user_id = str(user.get("id", ""))
    data = callback_query.get("data", "")
    parts = data.split(":", 1)
    if len(parts) < 2:
        return answer_callback_query(bot_token, callback_id, "❌ Invalid callback data.", True)

    file_uuid = parts[1]

    # load temp file for this bot
    temp_file = get_temp_file(bot_token)
    try:
        with open(temp_file, "r") as f:
            temp_data = json.load(f)
    except:
        temp_data = {}

    file_entry = temp_data.get(user_id, {}).get("files", {}).get(file_uuid)
    if not file_entry:
        return answer_callback_query(bot_token, callback_id, "❌ फ़ाइल नहीं मिली।", True)

    # cycle visibility
    visibility_cycle = ["public", "private", "vip"]
    current_visibility = file_entry.get("visibility", "public")
    try:
        idx = visibility_cycle.index(current_visibility)
    except ValueError:
        idx = 0
    new_visibility = visibility_cycle[(idx + 1) % len(visibility_cycle)]
    file_entry["visibility"] = new_visibility

    # save temp file
    try:
        temp_data[user_id]["files"][file_uuid] = file_entry
        with open(temp_file, "w") as f:
            json.dump(temp_data, f, indent=2)
    except Exception as e:
        # best-effort save error
        print("toggle_visibility save error:", e)
        return answer_callback_query(bot_token, callback_id, "⚠️ Unable to update visibility.", True)

    # prepare caption and buttons
    file_id = file_entry.get("file_id")
    name = file_entry.get("name", "Unnamed")
    caption_text = file_entry.get("caption", name)

    safe_name = escape_markdown(str(name))
    safe_caption = escape_markdown(str(caption_text))

    caption = (
        f"📄 **Visibility Updated**\n"
        f"**Name** : `{safe_name}`\n"
        f"**Caption** : `{safe_caption}`\n"
        f"**File ID** : `{file_id}`\n"
        f"**Visibility** : `{new_visibility}`"
    )

    buttons = [
        [InlineKeyboardButton("✏️ Rename", callback_data=f"rename_file:{file_uuid}")],
        [InlineKeyboardButton("📝 Edit Caption", callback_data=f"edit_file_caption:{file_uuid}")],
        [InlineKeyboardButton(f"👁 Visibility: {new_visibility}", callback_data=f"toggle_visibility:{file_uuid}")],
        [InlineKeyboardButton("FILE IS UNDER A USER", callback_data=f"add_premium_owner:{file_uuid}")],
        [
            InlineKeyboardButton("✅ Confirm Upload", callback_data=f"confirm_file:{file_uuid}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_file:{file_uuid}")
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # acknowledge callback to remove spinner
    answer_callback_query(bot_token, callback_id)

    # edit original message
    msg = callback_query.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")

    if chat_id and message_id:
        edit_message(bot_token, chat_id, message_id, caption, reply_markup=keyboard, is_caption=True)
    else:
        # fallback: send as new message to user
        send_message(bot_token, user_id, caption, reply_markup=keyboard)

@on_callback_query(filters.callback_data("^add_premium_owner:"))
def cancel_file_handler(bot_token, update, callback_query):
    """
    Webhook-style cancel_file handler.
    callback_query is a dict from Telegram webhook.
    """
    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    return answer_callback_query(bot_token, callback_id, "This Feature is comming Soon...", True)
        
@on_callback_query(filters.callback_data("^cancel_file:"))
def cancel_file_handler(bot_token, update, callback_query):
    """
    Webhook-style cancel_file handler.
    callback_query is a dict from Telegram webhook.
    """
    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    parts = data.split(":", 1)
    if len(parts) < 2:
        return answer_callback_query(bot_token, callback_id, "❌ Invalid callback data.", True)

    file_uuid = parts[1]
    user_id = str(callback_query.get("from", {}).get("id", ""))
    msg = callback_query.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")

    # load tempfile for this bot
    temp_file = get_temp_file(bot_token)
    try:
        with open(temp_file, "r") as f:
            temp_data = json.load(f)
    except Exception as e:
        print("cancel_file: failed to load temp file:", e)
        return answer_callback_query(bot_token, callback_id, "❌ tempfile.json not found", True)

    user_files = temp_data.get(user_id, {}).get("files", {})

    if file_uuid in user_files:
        # remove the file entry
        del user_files[file_uuid]

        # if no files left for user, remove the user entry entirely
        if not user_files:
            temp_data.pop(user_id, None)
        else:
            # update the nested dict back
            temp_data[user_id]["files"] = user_files

        # save back
        try:
            with open(temp_file, "w") as f:
                json.dump(temp_data, f, indent=2)
        except Exception as e:
            print("cancel_file: failed to save temp file:", e)
            return answer_callback_query(bot_token, callback_id, "⚠️ Unable to update temp storage.", True)

        # acknowledge callback (remove spinner)
        answer_callback_query(bot_token, callback_id)

        # Try to edit the message caption (media message). Use edit_message helper with is_caption=True
        if chat_id and message_id:
            try:
                edit_message(bot_token, chat_id, message_id, "❌ File upload cancelled successfully.", reply_markup=None, is_caption=True)
            except Exception as e:
                print("cancel_file: edit_message failed:", e)
                # fallback: send a new message to user
                send_message(bot_token, chat_id, "❌ File upload cancelled successfully.")
        else:
            # fallback: send a new message to user id
            send_message(bot_token, user_id, "❌ File upload cancelled successfully.")
    else:
        return answer_callback_query(bot_token, callback_id, "❌ File not found or already cancelled.", True)

def find_folder_id_of_item(folder, target_id):
    for item in folder.get("items", []):
        if item.get("id") == target_id:
            return folder.get("id")
        elif item.get("type") == "folder":
            found = find_folder_id_of_item(item, target_id)
            if found:
                return found
    return None
def find_item_by_id(folder, target_id):
    for item in folder.get("items", []):
        if item["id"] == target_id:
            return item
        if item.get("type") == "folder":
            found = find_item_by_id(item, target_id)
            if found:
                return found
    return None        
@on_callback_query(filters.callback_data("^confirm_file:"))
def confirm_file_callback(bot_token, update, callback_query):
    """
    Webhook-style handler for confirming a temp file and moving it into bot_data.
    """
    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    parts = data.split(":", 1)
    bot_id = bot_token.split(":")[0]
    #print("hek pankaj")
    #print(bot_id)
    #print(f"parts □ {parts} □")
  
    if len(parts) < 2:
        print("INVALID")
        return answer_callback_query(bot_token, callback_id, "❌ Invalid callback data.", True)

    file_uuid = parts[1]  # this is the temp file's uuid
    user = callback_query.get("from", {})
    user_id = str(user.get("id", ""))

    # acknowledge callback quickly
    answer_callback_query(bot_token, callback_id)

    # load temp file for this bot
    temp_file = get_temp_file(bot_token)
    #print(f"hi □ {temp_file} □")
    try:
        with open(temp_file, "r") as f:
            temp_data = json.load(f)
    except Exception as e:
        #print("confirm_file: could not open temp file:", e)
        return answer_callback_query(bot_token, callback_id, "❌ Temp file data not found.", True)
    #print(f"temp_data □ {temp_data} □")
    user_files = temp_data.get(user_id, {}).get("files", {})
    file_data = user_files.get(file_uuid)
    if not file_data:
        #print("File not found in tem")
        return answer_callback_query(bot_token, callback_id, "❌ File not found in temp.", True)

    # determine target folder
    folder_id = temp_data.get(user_id, {}).get("folder_id")
    if not folder_id:
        return answer_callback_query(bot_token, callback_id, "❌ Folder info missing.", True)

    # permission check
    if (not is_user_action_allowed(folder_id, "add_file", bot_token)
            and int(user_id) not in ADMINS(bot_id)
            and get_created_by_from_folder(bot_token, folder_id) != int(user_id)):
        return answer_callback_query(bot_token, callback_id, "❌ You are not allowed to add a file in this folder.", True)

    # load bot data file (bot-specific)
    data_file = get_data_file(bot_token)
    try:
        with open(data_file, "r") as f:
            bot_data = json.load(f)
    except Exception as e:
        print("confirm_file: could not open data file:", e)
        return answer_callback_query(bot_token, callback_id, "❌ bot_data.json not found.", True)

    root = bot_data.get("data", {})
    parent = find_folder_by_id(root, folder_id)
    if not parent:
        return answer_callback_query(bot_token, callback_id, "❌ Parent folder not found.", True)

    # compute next row
    existing_rows = [item.get("row", 0) for item in parent.get("items", [])]
    next_row = max(existing_rows, default=-1) + 1

    # determine created_by (premium owner override)
    if file_data.get("premium_owner"):
        try:
            created_by_val = int(file_data["premium_owner"])
        except Exception:
            created_by_val = int(user_id)
    else:
        created_by_val = int(user_id)

    # prepare final item
    final_file = {
        "id": file_data["id"],
        "type": "file",
        "sub_type": file_data.get("sub_type", "document"),
        "name": file_data.get("name"),
        "file_id": file_data.get("file_id"),
        "caption": file_data.get("caption"),
        "visibility": file_data.get("visibility", "private"),
        "row": next_row,
        "column": 0,
        "created_by": created_by_val,
    }

    if file_data.get("premium_owner"):
        try:
            final_file["premium_owner"] = int(file_data["premium_owner"])
        except Exception:
            pass

    parent.setdefault("items", []).append(final_file)

    # save bot_data
    try:
        with open(data_file, "w") as f:
            json.dump(bot_data, f, indent=2)
    except Exception as e:
        print("confirm_file: failed to save data file:", e)
        return answer_callback_query(bot_token, callback_id, "⚠️ Failed to save bot data.", True)

    # if premium_owner present, save to pre_files map
    try:
        pre_file_path = get_pre_files_file(bot_token)  # implement this helper or replace with your pre_file path var
    except Exception:
        pre_file_path = None

    if file_data.get("premium_owner") and pre_file_path:
        try:
            try:
                with open(pre_file_path, "r") as f:
                    pre_files_data = json.load(f)
            except FileNotFoundError:
                pre_files_data = {}

            owner_key = str(file_data.get("premium_owner"))
            pre_files_data.setdefault(owner_key, [])
            if file_uuid not in pre_files_data[owner_key]:
                pre_files_data[owner_key].append(file_uuid)

            with open(pre_file_path, "w") as f:
                json.dump(pre_files_data, f, indent=2)
        except Exception as e:
            print("confirm_file: failed to update pre_files:", e)

    # remove file entry from temp_data
    try:
        user_entry = temp_data.get(user_id, {})
        user_files_map = user_entry.get("files", {})
        if file_uuid in user_files_map:
            del user_files_map[file_uuid]
        # if no files left, remove user entry
        if not user_files_map:
            temp_data.pop(user_id, None)
        else:
            temp_data[user_id]["files"] = user_files_map
        with open(temp_file, "w") as f:
            json.dump(temp_data, f, indent=2)
    except Exception as e:
        print("confirm_file: failed to cleanup temp_data:", e)

    # clear status
    status_file = get_status_file(bot_token)
    try:
        with open(status_file, "r") as f:
            status_data = json.load(f)
    except:
        status_data = {}
    status_data.pop(user_id, None)
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)
    git_data_file= f"BOT_DATA/{bot_id}/bot_data.json"
    save_json_to_alt_github(data_file,git_data_file)

    # refresh UI: edit caption to wait then success
    msg = callback_query.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")

    # set "Please wait..." first (media message -> edit caption)
    #if chat_id and message_id:
        #edit_message(bot_token, chat_id, message_id, "Please wait...", reply_markup=None, is_caption=True)

    # generate keyboard and final success caption
    kb = generate_folder_keyboard(parent, int(user_id),bot_id)
    success_caption = f"FILE SAVED SUCCESSFULLY \n**File uuid**: {file_data.get('id')}"

    # optional: call save_data_file_to_mongo if your project still needs it
    # final edit
    if chat_id and message_id:
        edit_message(bot_token, chat_id, message_id, success_caption, reply_markup=kb, is_caption=True)
    else:
        # fallback: send message to user
        send_message(bot_token, user_id, success_caption, reply_markup=kb)
        
@on_callback_query(filters.callback_data("^file:"))
def send_file_from_json(bot_token, update, callback_query):
    try:
        callback_id = callback_query.get("id")
        data = callback_query.get("data", "") or ""
        data_parts = data.split(":")
        bot_id = bot_token.split(":")[0]
        if len(data_parts) < 2:
            return answer_callback_query(bot_token, callback_id, "❌ Invalid callback.", True)

        file_uuid = data_parts[1]
        user = callback_query.get("from", {}) or {}
        user_id = int(user.get("id", 0))
        msg = callback_query.get("message", {}) or {}
        chat = msg.get("chat", {}) or {}
        chat_id = chat.get("id")
        chat_type = chat.get("type", "")

        # helper: detect group
        is_group = chat_type in ("group", "supergroup")

        # If group - enforce original user check and redirect to @bot?start=
        if is_group:
            if len(data_parts) < 3:
                return answer_callback_query(bot_token, callback_id, "❌ Invalid file request.", True)
            try:
                original_user_id = int(data_parts[2])
            except Exception:
                return answer_callback_query(bot_token, callback_id, "❌ Invalid original user id.", True)

            if original_user_id != user_id:
                return answer_callback_query(
                    bot_token,
                    callback_id,
                    "⚠️ This button belongs to another user.\nPlease send /start to get your own menu.",
                    True
                )

            # get bot username via getMe
            me_resp = send_api(bot_token, "getMe", {})
            bot_username = None
            if me_resp and me_resp.get("ok"):
                bot_username = me_resp.get("result", {}).get("username")
            if bot_username:
                start_url = f"https://t.me/{bot_username}?start={file_uuid}"
                # answer with url (opens private chat)
                return answer_callback_query(bot_token, callback_id, None) or send_message(bot_token, chat_id, f"Open in private: {start_url}")
            else:
                return answer_callback_query(bot_token, callback_id, "❌ Unable to get bot username.", True)

        # Non-group (private) handling: load data file
        data_file = get_data_file(bot_token)
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                bot_data = json.load(f)
        except Exception as e:
            print("send_file_from_json: failed to load data_file:", e)
            return answer_callback_query(bot_token, callback_id, f"❌ Data file not found: {e}", True)

        root = bot_data.get("data", {})
        file_data = find_item_by_id(root, file_uuid)  # must return the item dict or None

        if not file_data or file_data.get("type") != "file":
            return answer_callback_query(bot_token, callback_id, "❌ File not found.", True)

        file_id = file_data.get("file_id")
        name = file_data.get("name", "Unnamed")
        caption = file_data.get("caption") or name
        sub_type = file_data.get("sub_type", "document")
        visibility = file_data.get("visibility", "public")
        created_by = file_data.get("created_by")
        protect = visibility == "private"
        premium_owner = file_data.get("premium_owner")  # may be None or int
        owner_id = int(get_owner_id(bot_token))

        # Unlock base url (used by unlock flow)
        deploy = BASE_URL.rstrip("/") if globals().get("BASE_URL") else ""
        unlock_base_url = deploy + f"/{bot_id}/unlock_file"

        # Helper to send media via send_api for arbitrary sub_type with protect_content support
        def send_media_api(bot_token_, chat_id_, sub_type_, file_id_, caption_, reply_markup=None, protect_content=False):
            method = {
                "photo": "sendPhoto",
                "video": "sendVideo",
                "audio": "sendAudio",
                "document": "sendDocument",
            }.get(sub_type_, "sendDocument")
            payload = {"chat_id": chat_id_}
            # choose correct field name
            if method == "sendPhoto":
                payload["photo"] = file_id_
            elif method == "sendVideo":
                payload["video"] = file_id_
            elif method == "sendAudio":
                payload["audio"] = file_id_
            else:
                payload["document"] = file_id_
            if caption_ is not None:
                payload["caption"] = caption_
            if protect_content:
                payload["protect_content"] = True
            if reply_markup:
                if hasattr(reply_markup, "to_dict"):
                    payload["reply_markup"] = reply_markup.to_dict()
                elif isinstance(reply_markup, dict):
                    payload["reply_markup"] = reply_markup
            return send_api(bot_token_, method, payload)

        # ----------------------
        # VIP handling
        # ----------------------
        if visibility == "vip":
            try:
                # Send a copy to PREMIUM_CHECK_LOG to get file_size etc.
                #premium_chat = PREMIUM_CHECK_LOG
              if get_is_monetized(bot_id):
                premium_chat = get_file_channel_id(bot_token)
                resp = send_media_api(bot_token, premium_chat, sub_type, file_id, caption, reply_markup=None, protect_content=False)
                # extract file size
                file_size = None
                if resp and resp.get("ok"):
                    result = resp.get("result", {})
                    if sub_type == "document" and result.get("document"):
                        file_size = result["document"].get("file_size")
                    elif sub_type == "video" and result.get("video"):
                        file_size = result["video"].get("file_size")
                    elif sub_type == "audio" and result.get("audio"):
                        file_size = result["audio"].get("file_size")
                    elif sub_type == "photo" and result.get("photo"):
                        # photo is list
                        photos = result.get("photo", [])
                        if photos:
                            file_size = photos[-1].get("file_size")
                readable_size = f"{round(file_size / (1024 * 1024), 2)} MB" if file_size else "Unknown"

                import urllib.parse
                base_unlock = "https://reward.edumate.life/Premium/unlock.html?"
                # if premium_owner, use different unlock endpoint
                if premium_owner:
                    unlock_base_url = deploy + f"/{bot_id}/unlock_users_file"

                unlock_params = (
                    f"uuid={urllib.parse.quote_plus(file_uuid)}"
                    f"&file_name={urllib.parse.quote_plus(name)}"
                    f"&file_des={urllib.parse.quote_plus(str(caption))}"
                    f"&file_size={urllib.parse.quote_plus(readable_size)}"
                    f"&url={urllib.parse.quote_plus(unlock_base_url)}"
                )
                unlock_url = base_unlock + unlock_params
                # Build unlock message
                if premium_owner and int(user_id) == int(premium_owner):
                    unlock_msg = (
                        f"**Hello Partner**,\nYou are Making Money by this file.\n\n"
                        f"**📁 Name:** `{escape_markdown(str(name))}`  \n"
                        f"**📝 Description:** `{escape_markdown(str(caption))}`  \n"
                        f"**📦 Size:** `{readable_size}`  \n"
                        f"**🆔 File UUID:** `{file_uuid}`\n\n"
                        f"Manage this file with command `/my_pdf {file_uuid}`"
                    )
                else:
                    unlock_msg = (
                        f"🔐 **Exclusive Premium File**\n\n"
                        f"**📁 Name:** `{escape_markdown(str(name))}`  \n"
                        f"**📝 Description:** `{escape_markdown(str(caption))}`  \n"
                        f"**📦 Size:** `{readable_size}`\n\n"
                        "To unlock this file, tap **Unlock Now** below and view a short ad. 🙏\n👇"
                    )

                # build buttons (web_app)
                buttons = [[InlineKeyboardButton("🔓 Unlock this file", web_app={"url": unlock_url})]]

                # add admin/edit button if allowed
                try:
                    allowed_user = (user_id in ADMINS(bot_id)) or (user_id == created_by) or (premium_owner and int(user_id) == int(premium_owner))
                except Exception:
                    allowed_user = (user_id == created_by) or (premium_owner and int(user_id) == int(premium_owner))
                if allowed_user:
                    folder_of_item = find_folder_id_of_item(root, file_uuid)
                    if folder_of_item:
                        buttons.append([InlineKeyboardButton("✏️ Edit Item", callback_data=f"edit_item_file:{folder_of_item}:{file_uuid}")])

                kb = InlineKeyboardMarkup(buttons)
                # reply with unlock message
                send_media_api(bot_token, chat_id, sub_type, file_id, unlock_msg, reply_markup=kb, protect_content=False)
                answer_callback_query(bot_token, callback_id)
                return
              else: 
                premium_chat = get_file_channel_id(bot_token)
                resp = send_media_api(bot_token, owner_id, sub_type, file_id, "Someone Accessed your VIP file.\n\nBut your bot is not Monetized yet.\nPlease Monetize your bot to enable ad and earn money.\n\nTo Monetize your bot visit bot @BotixHubBot", reply_markup=None, protect_content=False)
                resp = send_media_api(bot_token, premium_chat, sub_type, file_id, "This file is a vip file. But your bot is not Monetized yet.\nPlease Monetize your bot to enable ad and earn money.\n\nTo Monetize your bot visit bot @BotixHubBot", reply_markup=None, protect_content=False)
                
            except Exception as e:
                print("send_file_from_json VIP error:", e)
                answer_callback_query(bot_token, callback_id)
                send_message(bot_token, chat_id, f"❌ Failed to prepare VIP file: {e}")
                return

        # ----------------------
        # Non-VIP: send file directly (with optional edit button)
        # ----------------------
        buttons = []
        try:
            allowed_user = (user_id in ADMINS(bot_id)) or (user_id == created_by) or (premium_owner and int(user_id) == int(premium_owner))
        except Exception:
            allowed_user = (user_id == created_by) or (premium_owner and int(user_id) == int(premium_owner))

        if allowed_user:
            folder_of_item = find_folder_id_of_item(root, file_uuid)
            if folder_of_item:
                buttons.append([InlineKeyboardButton("✏️ Edit Item", callback_data=f"edit_item_file:{folder_of_item}:{file_uuid}")])

        kb = InlineKeyboardMarkup(buttons) if buttons else None

        # send file to same chat (chat_id)
        try:
            send_resp = send_media_api(bot_token, chat_id, sub_type, file_id, caption, reply_markup=kb, protect_content=protect)
            # ignore send_resp details; it's fine
            answer_callback_query(bot_token, callback_id)
            return
        except Exception as e:
            print("send_file_from_json send error:", e)
            answer_callback_query(bot_token, callback_id)
            send_message(bot_token, chat_id, f"❌ Error sending file: {e}")
            return

    except Exception as e:
        print("⚠️ send_file_from_json callback error:", e)
        try:
            answer_callback_query(bot_token, callback_query.get("id"), f"❌ Unexpected error: {e}", True)
        except Exception:
            pass
          
@on_callback_query(filters.callback_data("^edit_item_file:"))
def edit_item_file_handler(bot_token, update, callback_query):
    """
    Webhook-style handler to show edit options for a file item inside a folder.
    callback_query: dict from Telegram webhook
    """
    callback_id = callback_query.get("id")
    #print(callback_query)
    data = callback_query.get("data", "") or ""
    parts = data.split(":")
    bot_id = bot_token.split(":")[0]
    if len(parts) < 3:
        return answer_callback_query(bot_token, callback_id, "❌ Invalid callback data.", True)

    folder_id = parts[1]
    file_uuid = parts[2]

    user = callback_query.get("from", {}) or {}
    user_id = int(user.get("id", 0))

    # load bot_data (bot-specific)
    data_file = get_data_file(bot_token)
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data_json = json.load(f)
    except Exception as e:
        print("edit_item_file: failed to open data file:", e)
        return answer_callback_query(bot_token, callback_id, "❌ Unable to load data.", True)

    # recursive folder finder
    def find_folder(folder, fid):
        if folder.get("id") == fid and folder.get("type") == "folder":
            return folder
        for item in folder.get("items", []) or []:
            if item.get("type") == "folder":
                found = find_folder(item, fid)
                if found:
                    return found
        return None

    root = data_json.get("data", {})
    folder = find_folder(root, folder_id)
    if not folder:
        return answer_callback_query(bot_token, callback_id, "❌ Folder not found.", True)

    # find file item inside folder
    file_data = next((i for i in folder.get("items", []) if i.get("id") == file_uuid), None)
    #print(f"F8ledgyd: {file_data}")
    if not file_data:
        return answer_callback_query(bot_token, callback_id, "❌ File not found.", True)

    # permission check: admins or creator
    try:
        admins = ADMINS(bot_id)
    except Exception:
        admins = ADMINS(bot_id) if callable(ADMINS) else []
    if (user_id not in admins) and (file_data.get("created_by") != user_id):
        return answer_callback_query(bot_token, callback_id, "❌ You don't have access.", True)

    # get current visibility
    visibility = file_data.get("visibility", "private")

    # build buttons
    buttons = [
        [InlineKeyboardButton(f"👁 Visibility: {visibility}", callback_data=f"toggle_file_visibility:{file_uuid}")],
        [InlineKeyboardButton("📝 Edit Caption", callback_data=f"file_caption_editing:{file_uuid}")],
    ]
    kb = InlineKeyboardMarkup(buttons)

    # edit the message text (use edit_message_text helper)
    msg = callback_query.get("message", {}) or {}
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")

    text = f"🛠 Edit options for file: {file_data.get('name', 'Unnamed')}"
    # acknowledge callback (remove spinner) then edit
    answer_callback_query(bot_token, callback_id)
    if chat_id and message_id:
        a= edit_message(bot_token, chat_id, message_id, text, reply_markup=kb, is_caption=True)
        print("edit")
        print(a)
    else:
        # fallback: send new message to user
        a= send_message(bot_token, user_id, text, reply_markup=kb)
        print("here")
        print(a)

@on_callback_query()
def edit_item_file_handler(bot_token, update, callback_query):
  callback_id = callback_query.get("id")
  return answer_callback_query(bot_token, callback_id, "This Feature is Comming Soon...", True)