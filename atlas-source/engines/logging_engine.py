from datetime import datetime


class LoggingEngine:

    def info(self, message):
        print(f"[INFO] {datetime.now()} - {message}")

    def warning(self, message):
        print(f"[WARNING] {datetime.now()} - {message}")

    def error(self, message):
        print(f"[ERROR] {datetime.now()} - {message}")