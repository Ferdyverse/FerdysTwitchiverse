import logging
import json
import os
import datetime
import traceback
from logging.handlers import RotatingFileHandler
import config

# Ensure log directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Custom mapping: Python modules/files → Log names
LOG_MODULE_MAP = {
    "apscheduler": "APPScheduler",
    "database": "Database",
    "event_queue_processor": "EventQueue",
    "function_registry": "FunctionRegistry",
    "heat_api": "HeatmapAPI",
    "lifespan": "Lifespan",
    "printer_manager": "Printer",
    "queue_manager": "QueueManager",
    "scheduled_jobs": "ScheduledJobs",
    "scheduled_messages": "Scheduler",
    "sequence_runner": "SequenceRunner",
    "twitch_api": "TwitchAPI",
    "twitch_chat": "TwitchChat",
    "uvicorn": "Uvicorn",
}

# ANSI color codes for terminal output
MODULE_COLORS = {
    "Database": "\033[38;5;208m",  # Orange
    "EventQueue": "\033[92m",  # Green
    "HeatmapAPI": "\033[93m",  # Yellow
    "Lifespan": "\033[91m",  # Red
    "Printer": "\033[96m",  # Cyan
    "QueueManager": "\033[38;5;33m",  # Deep Blue
    "Scheduler": "\033[38;5;214m",  # Gold
    "TwitchAPI": "\033[95m",  # Purple
    "TwitchChat": "\033[94m",  # Blue
    "Uvicorn": "\033[90m",  # Dark Gray (General Uvicorn logs)
}

RESET_COLOR = "\033[0m"


def get_log_filename():
    """Generate the base log filename based on the current date (YYYY-MM-DD)."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{current_date}.log")


def rotate_logs():
    """Rotate logs by renaming them before the application starts."""
    base_log = get_log_filename()

    # Keep only the last 7 logs
    for i in range(6, 0, -1):
        old_log = f"{base_log}.{i}"
        new_log = f"{base_log}.{i + 1}"
        if os.path.exists(old_log):
            os.rename(old_log, new_log)

    if os.path.exists(base_log):
        os.rename(base_log, f"{base_log}.1")


# 🔄 Rotate logs before setting up logging
rotate_logs()


class CustomFormatter(logging.Formatter):
    """Custom formatter that applies colors and renames modules."""

    def format(self, record):
        # Extract module path (e.g., "uvicorn.error.twitch_api.auth")
        module_path = record.name

        # Find the best match in LOG_MODULE_MAP
        matched_module = next(
            (name for key, name in LOG_MODULE_MAP.items() if key in module_path),
            record.name,  # Fallback: original module name
        )

        # Store the formatted module name
        record.custom_module = matched_module

        # Apply color
        module_color = MODULE_COLORS.get(matched_module, "\033[97m")
        log_message = super().format(record)
        return f"{module_color}{log_message}{RESET_COLOR}"


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging, including full tracebacks."""

    def format(self, record):
        module_path = record.name

        # Find the best match in LOG_MODULE_MAP
        matched_module = next(
            (name for key, name in LOG_MODULE_MAP.items() if key in module_path),
            record.name,  # Fallback: original module name
        )

        # Store the formatted module name
        record.custom_module = matched_module

        log_entry = {
            "timestamp": self.formatTime(record, config.APP_LOG_TIME_FORMAT),
            "level": record.levelname,
            "module": record.custom_module,
            "message": record.getMessage(),
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        if record.exc_info:
            log_entry["traceback"] = traceback.format_exc()

        return json.dumps(log_entry, ensure_ascii=False)


# 📌 Log Handlers
log_filename = get_log_filename()

# File logging (JSON format) with rotation
file_handler = RotatingFileHandler(
    log_filename, mode="w", maxBytes=10 * 1024 * 1024, backupCount=7, encoding="utf-8"
)
file_handler.setFormatter(JSONFormatter())

# Console logging with colors
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    CustomFormatter("%(asctime)s - %(levelname)s - %(custom_module)s - %(message)s")
)

# Apply logging configuration
logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler])

# Ensure Uvicorn logs use the correct format
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
for handler in logging.getLogger("uvicorn").handlers:
    handler.setFormatter(
        CustomFormatter("%(asctime)s - %(levelname)s - %(custom_module)s - %(message)s")
    )

# Add JSON logging to Uvicorn
logging.getLogger("uvicorn").addHandler(file_handler)
