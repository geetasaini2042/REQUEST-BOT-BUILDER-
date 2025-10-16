import os, json
from common_data import BASE_PATH
def ensure_bot_dir(bot_token):
    bot_id = bot_token.split(":")[0]
    path = os.path.join(f"{BASE_PATH}/BOTS_DATA", bot_id)
    os.makedirs(path, exist_ok=True)
    return path



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


import os, json
from common_data import BASE_PATH


def get_status_file(bot_token: str):
    bot_id = bot_token.split(":")[0]
    folder = os.path.join(BASE_PATH, "BOT_DATA", bot_id)
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, "status_user.json")

    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump({}, f)

    return file_path


def load_json_file(path: str):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        #print(f"⚠ JSON लोड error ({path}):", e)
        return {}


class StatusFilter(Filter):
    def __init__(self, required_status: str):
        self.required_status = required_status
        super().__init__(self.check_status)

    def check_status(self, msg: dict):
        bot_token = msg.get("bot_token")
        user = msg.get("from", {})
        user_id = user.get("id")

        if not bot_token or not user_id:
            #print("⚠ bot_token या user_id नहीं मिला:", msg)
            return False

        status_file = get_status_file(bot_token)
        data = load_json_file(status_file)

        user_status = str(data.get(str(user_id), "")).strip()
        required = str(self.required_status).strip()

        # 🟢 Debug prints
        """
        print("───────────── DEBUG: StatusFilter ─────────────")
        print(f"📁 Status File: {status_file}")
        print(f"📄 File Data: {json.dumps(data, indent=2)}")
        print(f"👤 User ID: {user_id}")
        print(f"🎯 Required: '{required}'")
        print(f"💾 Current: '{user_status}'")
        print("─────────────────────────────────────────────")
        """
        # Compare logic
        if user_status.startswith(required):
            #print("✅ Status match हो गया!")
            return True
        else:
            #print("❌ Status match नहीं हुआ.")
            return False