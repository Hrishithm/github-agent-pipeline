import logging
import sys

# Safely set Windows console UTF-8 without closing the buffer
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configure logger
logger = logging.getLogger("github_agent_pipeline")
logger.setLevel(logging.INFO)

# Formatter: timestamp [LEVEL] logger_name: message
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Avoid duplicate handlers on re-initialization
if not logger.handlers:
    # Stream Handler (Terminal)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File Handler (Writes to pipeline.log file)
    file_handler = logging.FileHandler("pipeline.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)