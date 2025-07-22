import logging
from colorama import init, Fore, Style

init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.ERROR:
            record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler('app.log', mode='a')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
