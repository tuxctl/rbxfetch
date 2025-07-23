import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

class Debug:
    @staticmethod
    def _print(color: str, header: str, text: str):
        print(f"{color}[{header.upper()}]{Style.RESET_ALL} {text}")

    @staticmethod
    def info(header: str, text: str):
        Debug._print(Fore.CYAN, header, text)

    @staticmethod
    def success(header: str, text: str):
        Debug._print(Fore.GREEN, header, text)

    @staticmethod
    def warning(header: str, text: str):
        Debug._print(Fore.YELLOW, header, text)

    @staticmethod
    def error(header: str, text: str):
        Debug._print(Fore.RED, header, text)
