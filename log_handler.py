import logging
from pathlib import Path

logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)

handler_ecs = logging.FileHandler(Path("log", "log.log"))
logger.addHandler(handler_ecs)

# handler_stream = logging.StreamHandler()
# logger.addHandler(handler_stream)
