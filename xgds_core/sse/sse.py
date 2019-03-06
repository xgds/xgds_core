from flask import Flask
from flask_sse import sse

app = Flask(__name__)
app.config["REDIS_URL"] = "redis://redis"
app.register_blueprint(sse, url_prefix='/sse/stream')

@app.route('/sse/status')
def send_message():
    return "SSE is working!"