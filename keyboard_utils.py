import json
from collections import defaultdict
from pathlib import Path
from common_data import BASE_PATH
from pathlib import Path
BASE_PATH = Path(BASE_PATH)


DEFAULT_JSON = {
    "data": {
        "id": "root",
        "name": "Root",
        "description": "Welcome to Bot!",
        "type": "folder",
        "created_by": 6150091802,
        "parent_id": None,
        "user_allow": [],
        "items": []
    }
}


def ADMINS(bot_id: str) -> list:
    admin_file = BASE_PATH / "BOT_DATA" / bot_id / "ADMINS.json"

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

def get_root_inline_keyboard(bot_token: str, user_id: int):
    """
    Return Telegram Bot API compatible inline keyboard dict and description text
    """
    bot_id = bot_token.split(":")[0]
    data_file = BASE_PATH / "BOT_DATA" / bot_id / "bot_data.json"

    # Load or initialize JSON
    try:
        if not data_file.exists() or data_file.read_text().strip() == "{}":
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text(json.dumps(DEFAULT_JSON, indent=2))
            root = DEFAULT_JSON["data"]
        else:
            with open(data_file, "r") as f:
                root = json.load(f)["data"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {"inline_keyboard": [[{"text": "❌ No Data", "callback_data": "no_data"}]]}, "No description"

    # Build button layout
    layout = defaultdict(dict)
    for item in root.get("items", []):
        row = item.get("row", 0)
        col = item.get("column", 0)
        button = None

        if item["type"] == "folder":
            button = {"text": item.get("name", "Folder"), "callback_data": f"open:{item['id']}"}
        elif item["type"] == "file":
            button = {"text": item.get("name", "File"), "callback_data": f"file:{item['id']}"}
        elif item["type"] == "url":
            button = {"text": item.get("name", "URL"), "url": item.get("url", "#")}
        elif item["type"] == "webapp":
            button = {"text": item.get("name", "WebApp"), "web_app": {"url": item.get("url", "#")}}

        if button:
            layout[row][col] = button

    # Convert layout to list of rows
    buttons = []
    for row in sorted(layout.keys()):
        cols = layout[row]
        buttons.append([cols[col] for col in sorted(cols.keys())])

    # Add admin/user controls
    if user_id in ADMINS(bot_id):
        buttons.append([
            {"text": "➕ Add File", "callback_data": "add_file:root"},
            {"text": "📁 Add Folder", "callback_data": "add_folder:root"}
        ])
        buttons.append([
            {"text": "🧩 Add WebApp", "callback_data": "add_webapp:root"},
            {"text": "🔗 Add URL", "callback_data": "add_url:root"}
        ])
        buttons.append([{"text": "✏️ Edit Folder Layout", "callback_data": "edit1_item1:root"}])
    else:
        allow = root.get("user_allow", [])
        user_buttons = []
        if "add_file" in allow: user_buttons.append({"text": "➕ Add File", "callback_data": "add_file:root"})
        if "add_folder" in allow: user_buttons.append({"text": "📁 Add Folder", "callback_data": "add_folder:root"})
        if "add_webapp" in allow: user_buttons.append({"text": "🧩 Add WebApp", "callback_data": "add_webapp:root"})
        if "add_url" in allow: user_buttons.append({"text": "🔗 Add URL", "callback_data": "add_url:root"})
        for i in range(0, len(user_buttons), 2):
            buttons.append(user_buttons[i:i+2])

    return {"inline_keyboard": buttons}, root.get("description", "No description")