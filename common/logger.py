import logging

from concurrent_log_handler import ConcurrentRotatingFileHandler
import colorlog


class Logger:
    loggers = set()

    def __init__(
        self,
        name,
        fmt="s%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s() | %(threadName)s | %(message)s",
        level=logging.INFO,
        colors=True,
    ):
        try:
            # Construct Logger
            self.name = name
            self.format = fmt
            self.level = level

            # Config Logger
            self.stream_handler = logging.StreamHandler()
            self.standard_formatter = logging.Formatter(self.format)
            if colors:
                self.color_formatter = colorlog.ColoredFormatter(f"%(log_color){fmt}")
                self.stream_handler.setFormatter(self.color_formatter)
            else:
                self.stream_handler.setFormatter(self.standard_formatter)

            self.logger = logging.getLogger(name)

            # Prevent duplicate loggers
            if name not in self.loggers:
                self.loggers.add(name)
                self.logger.setLevel(self.level)
                self.logger.addHandler(self.stream_handler)
        except Exception as e:
            raise ValueError(f"Error creating logger: {e}")  # pylint: disable=W0707

    def get_logger(self):
        """
        Returns logger instance.
        """
        return self.logger

    def add_file_handler(
        self, file_path, level=None, max_bytes=10485760, backup_count=5
    ):
        """
        Adds a thread-safe file handler to the logger.
        Args:
            file_path: location of the log file to be written
            level: logging level to of logs to be written
            max_bytes: maximum size of log file in bytes
            backup_count: number of backup log files to keep after rotation of log file
        Returns:

        """
        try:
            level = level or self.level
            file_handler = ConcurrentRotatingFileHandler(
                filename=file_path, maxBytes=max_bytes, backupCount=backup_count
            )
            file_handler.setFormatter(logging.Formatter(self.format))
            file_handler.setLevel(level)
            self.logger.addHandler(file_handler)
        except Exception as e:
            raise ValueError(f"Failed to add file handler: {e}") from e
