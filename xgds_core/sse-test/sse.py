from flask import Flask, render_template
from flask_sse import sse
from flask import request

app = Flask(__name__)
app.config["REDIS_URL"] = "redis://localhost"
app.register_blueprint(sse, url_prefix='/stream')

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/hello')
def publish_hello():
    argString = request.args.get("argString", "")
    sse.publish({"message": "Hello %s!" % argString}, type='greeting')
    return "Message sent!"


