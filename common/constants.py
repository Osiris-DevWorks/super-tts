import datetime
import os
from discord import Colour

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(PROJECT_ROOT, "local")

SRC_ROOT_DIR = os.path.dirname(os.path.abspath(__file__)).replace("constants", "")
temp = SRC_ROOT_DIR.split("/")[0:-2]
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "aqua", "data")
LOG_FILE = f"{LOG_DIR}/{datetime.date.today().strftime('%Y-%m-%d')}.main.log"

DISPOSITION_STYLES = {
    "self": {"color": Colour.blue(), "emoji": "👤"},
    "ally": {"color": Colour.green(), "emoji": "🤝"},
    "friendly": {"color": Colour.teal(), "emoji": "😊"},
    "neutral": {"color": Colour.gold(), "emoji": "😐"},
    "hostile": {"color": Colour.red(), "emoji": "⚔️"},
    "unknown": {"color": Colour.greyple(), "emoji": "❓"}
}