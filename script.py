from flask import Flask, request
from framework import (
    filters, on_message, on_callback_query,
    send_message, handle_webhook_request
)

app = Flask(__name__)
"""
@app.route('/webhook/<bot_token>', methods=['POST'])
def webhook1(bot_token):
    update = request.get_json()
    return handle_webhook_request(bot_token, update)
"""