from flask import Flask

from utils.db import test_db_connection
from utils.cache import init_cache
from config import Config

import logging
import socket

# Import blueprints
from routes.home import home_bp
from routes.settings import settings_bp
from routes.overall import overall_bp
from routes.user import user_bp
from routes.minigame import minigame_bp

app = Flask(__name__)
app.config["AI-TYPE"] = "API"  # Default to API model
app.config["AI-MODEL"] = ""  # Default to no model

app.config["CACHE_TYPE"] = "FileSystemCache"
app.config["CACHE_DIR"] = "llm_cache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 3600  # 1 hour
app.config["CACHE_THRESHOLD"] = 20  # Max number of items before old ones are removed

app.config.from_object(Config)

logging.basicConfig(
    level=logging.INFO,  # or DEBUG for more detail
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Register blueprints
app.register_blueprint(home_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(overall_bp)
app.register_blueprint(user_bp)
app.register_blueprint(minigame_bp)

init_cache(app)

# Route to test round robin of nginx load balancing
@app.route("/whoami")
def whoami():
    return f"Served by container: {socket.gethostname()}"

if __name__ == "__main__":
    test_db_connection()
    app.run(debug=True)
