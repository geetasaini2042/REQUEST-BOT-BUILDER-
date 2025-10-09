from flask import Flask, request
from framework import (
    filters, on_message, on_callback_query,
    send_message, handle_webhook_request
)
from script import app
import handlers
# ============================
#   HANDLERS
# ============================
@app.route('/webhook/<bot_token>', methods=['POST'])
def webhook(bot_token):
    update = request.get_json()
    #send_message(bot_token, 6150091802, " नमस्! यह Flask ultra-fast webhook bot है 🚀")
    #return jsonify({"status": "ok"}), 200
    return handle_webhook_request(bot_token, update)



@on_message(filters.regex("hello|hi") & filters.private())
def hello_handler(bot_token, update, message):
    chat_id = message["chat"]["id"]
    send_message(bot_token, chat_id, "🙋‍♂️ हेलो! कैसे हैं आप?")


@on_message(filters.text() & filters.group())
def group_handler(bot_token, update, message):
    chat_id = message["chat"]["id"]
    send_message(bot_token, chat_id, "👥 Group में message मिला!")


@on_message(filters.text() & filters.private() & ~filters.command("start"))
def echo_handler(bot_token, update, message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    send_message(bot_token, chat_id, f"आपने कहा: {text}")

"""
@on_callback_query
def callback_handler(bot_token, update, callback):
    chat_id = callback["message"]["chat"]["id"]
    data = callback["data"]
    send_message(bot_token, chat_id, f"आपने callback चुना: {data}")

"""
# ============================
#   RUN APP
# ============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)