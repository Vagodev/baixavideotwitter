
import logging
import json
import sys

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "level": record.levelname,
            "time": self.formatTime(record, self.datefmt),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        return json.dumps(log_record)

def setup_logger():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("twitter_downloader")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

logger = setup_logger()
