import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "log"
LOG_FILE = LOG_DIR / "log.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.touch(exist_ok=True)

logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)

handler_ecs = logging.FileHandler(LOG_FILE)
logger.addHandler(handler_ecs)

# handler_stream = logging.StreamHandler()
# logger.addHandler(handler_stream)
