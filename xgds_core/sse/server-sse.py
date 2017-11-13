from flask import Flask
from flask_sse import sse

app = Flask(__name__)
app.config["REDIS_URL"] = "unix:///var/run/redis.sock"
app.register_blueprint(sse, url_prefix='/stream')
