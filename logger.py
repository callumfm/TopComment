import logging
import datetime

import pytz

CONSOLE_SEVERITY = "INFO"
TIMEZONE = pytz.timezone("Europe/London")
FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

severity = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


class LocalTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None) -> str:
        utc_time = datetime.datetime.fromtimestamp(record.created)
        local_time = utc_time.astimezone(TIMEZONE)
        str_time = local_time.strftime("%Y-%m-%d %H:%M:%S")
        timezone_name = local_time.tzname()
        time_formatted = "%s.%03d %s" % (str_time, record.msecs, timezone_name)
        return time_formatted


def get_configured_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(severity[CONSOLE_SEVERITY])
    formatter = LocalTimeFormatter(FORMAT)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger
