import logging
import datetime
import sys

import pytz


PREFIX = None
LOG_LEVEL = "DEBUG"
TIMEZONE = pytz.timezone("Europe/London")
FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
FORMAT_WITH_PREFIX = "%(asctime)s - %(name)s - %(levelname)s - %(prefix)s - %(message)s"

severity = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None) -> str:
        utc_time = datetime.datetime.fromtimestamp(record.created)
        local_time = utc_time.astimezone(TIMEZONE)
        str_time = local_time.strftime("%Y-%m-%d %H:%M:%S")
        timezone_name = local_time.tzname()
        time_formatted = "%s.%03d %s" % (str_time, record.msecs, timezone_name)
        return time_formatted

    def format(self, record) -> str:
        if hasattr(record, "prefix"):
            formatter = logging.Formatter(FORMAT_WITH_PREFIX)
        else:
            formatter = logging.Formatter(FORMAT)
        return formatter.format(record)


class CustomLogger(logging.Logger):

    stdout_level = severity[LOG_LEVEL]

    def __init__(self, name, level=None):
        level = level or self.stdout_level
        super().__init__(name, level)
        self.__set_handlers()

    def debug(self, msg, *args, prefix: str = None, **kwargs):
        kwargs = _add_prefix_to_extra(prefix, kwargs)
        self._log(logging.DEBUG, msg, args, **kwargs)

    def info(self, msg, *args, prefix: str = None, **kwargs):
        kwargs = _add_prefix_to_extra(prefix, kwargs)
        self._log(logging.INFO, msg, args, **kwargs)

    def warning(self, msg, *args, prefix: str = None, **kwargs):
        kwargs = _add_prefix_to_extra(prefix, kwargs)
        self._log(logging.WARNING, msg, args, **kwargs)

    def error(self, msg, *args, prefix: str = None, **kwargs):
        kwargs = _add_prefix_to_extra(prefix, kwargs)

        if "stack_info" not in kwargs:
            self._log(logging.ERROR, msg, args, **kwargs)
            return

        self._log(logging.ERROR, msg, args, **kwargs)

    def critical(self, msg, *args, prefix: str = None, **kwargs):
        kwargs = _add_prefix_to_extra(prefix, kwargs)

        if "stack_info" not in kwargs:
            self._log(logging.CRITICAL, msg, args, **kwargs)
            return

        self._log(logging.CRITICAL, msg, args, **kwargs)

    def addHandler(self, handler: logging.Handler) -> None:
        formatter = CustomFormatter()
        handler.setFormatter(formatter)

        if handler.level == logging.NOTSET:
            handler.setLevel(self.level)

        super().addHandler(handler)

    def __set_handlers(self):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(self.level)
        self.addHandler(stdout_handler)


def _add_prefix_to_extra(prefix, kwargs):
    if prefix is None:
        return kwargs

    if "extra" not in kwargs:
        kwargs["extra"] = {}

    kwargs["extra"]["prefix"] = prefix
    return kwargs
