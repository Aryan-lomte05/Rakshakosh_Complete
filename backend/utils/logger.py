
import sys
import time
from datetime import datetime

class RakshaLogger:
    """
    Centralized logger for RakshaKosh to provide high-visibility runtime info.
    """
    
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M:%S")

    @classmethod
    def info(cls, module: str, message: str):
        print(f"{cls.OKCYAN}[{cls._timestamp()}] [INFO] [{module}] {message}{cls.ENDC}")

    @classmethod
    def section(cls, title: str):
        print(f"\n{cls.HEADER}{'='*60}")
        print(f"🚀 {title.upper()}")
        print(f"{'='*60}{cls.ENDC}")

    @classmethod
    def success(cls, module: str, message: str):
        print(f"{cls.OKGREEN}[{cls._timestamp()}] [SUCCESS] [{module}] {message}{cls.ENDC}")

    @classmethod
    def warning(cls, module: str, message: str):
        print(f"{cls.WARNING}[{cls._timestamp()}] [WARNING] [{module}] {message}{cls.ENDC}")

    @classmethod
    def error(cls, module: str, message: str):
        print(f"{cls.FAIL}[{cls._timestamp()}] [ERROR] [{module}] {message}{cls.ENDC}")

    @classmethod
    def debug(cls, module: str, message: str):
        # Always print debug for now, as per user request to "see everything"
        print(f"{cls.OKBLUE}[{cls._timestamp()}] [DEBUG] [{module}] {message}{cls.ENDC}")
