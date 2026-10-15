import logging
import os
import sys
from datetime import datetime
import logfire

LOG_FILE = (f"{datetime.now().strftime('%m-%d-%Y-%H-%M-%S')}.log")
logs_path = os.path.join(os.getcwd(),"logs")
os.makedirs(logs_path,exist_ok=True)
LOG_FILE_PATH = os.path.join(logs_path,LOG_FILE)
LOG_FORMAT = (
    "[ %(asctime)s ] "
    "%(lineno)d "
    "%(name)s - "
    "%(levelname)s - "
    "%(message)s"
)
formatter = logging.Formatter(LOG_FORMAT)
file_handler = logging.FileHandler(LOG_FILE_PATH,encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

def attach_logfire_handler() -> None:
    for handler in root_logger.handlers:
        if isinstance(handler,logfire.LogfireLoggingHandler):
            return
    logfire_handler = logfire.LogfireLoggingHandler()
    logfire_handler.setLevel(logging.INFO)
    root_logger.addHandler(logfire_handler)
    logging.info("Logfire logging handler attached successfully")