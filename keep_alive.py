"""
Keep-alive web server for Replit
This creates a simple Flask server that UptimeRobot can ping to keep the bot alive.
"""

from flask import Flask
from threading import Thread
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route('/')
def home():
    """Health check endpoint"""
    return "Bot is running! 🤖", 200


@app.route('/health')
def health():
    """Alternative health check endpoint"""
    return {"status": "ok", "bot": "yasno-zrozumilo"}, 200


def run():
    """Run the Flask server"""
    logger.info("Starting keep-alive web server on port 8080")
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)


def keep_alive():
    """Start the web server in a separate thread"""
    t = Thread(target=run)
    t.daemon = True
    t.start()
    logger.info("Keep-alive server started")
