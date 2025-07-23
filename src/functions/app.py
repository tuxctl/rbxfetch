import sys
import requests
import json
import time
from colorama import Fore, Style, init
from .roblox_api import acquire_csrf
from .processor import forge_clothing

def run():
    init(autoreset=True)

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} config.json not found. Aborting execution.")
        input("Press Enter to exit...")
        sys.exit()
    except json.JSONDecodeError:
        print(f"{Fore.RED}[FATAL]{Style.RESET_ALL} Malformed config.json detected. Fix and restart.")
        input("Press Enter to exit...")
        sys.exit()

    settings = {
        "cookie": {
            ".ROBLOSECURITY": config["settings"]["auth"]["cookie"]
        },
        "use_custom_template": config["settings"]["use_custom_template"]
    }

    session = requests.Session()
    for name, value in settings["cookie"].items():
        session.cookies.set(name, value, domain=".roblox.com")

    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    acquire_csrf(session)

    try:
        user_info = session.get("https://users.roblox.com/v1/users/authenticated").json()
        print(f"{Fore.GREEN}[AUTH]{Style.RESET_ALL} Authenticated as {user_info['name']} (ID: {user_info['id']})\n")
    except Exception as e:
        print(f"{Fore.RED}[AUTH]{Style.RESET_ALL} Authentication failed: {e}")
        input("Press Enter to exit...")
        sys.exit()

    clothing_types = {
        "s": "Shirts", "shirt": "Shirts", "shirts": "Shirts",
        "p": "Pants", "pant": "Pants", "pants": "Pants"
    }

    user_choice = input("Clothing type (s/p): ").lower()
    selected_type = clothing_types.get(user_choice)

    if not selected_type:
        print(f"{Fore.RED}[INPUT]{Style.RESET_ALL} Invalid clothing type selected.")
        input("Press Enter to exit...")
        sys.exit()

    print(f"{Fore.CYAN}[RBXFETCH]{Style.RESET_ALL} Selected: {selected_type}")

    search_keywords = input("Enter search keywords (e.g., emo goth y2k): ").strip().replace(" ", "+").lower()

    search_url = (
        f"https://catalog.roblox.com/v1/search/items?"
        f"category=Clothing&keyword={search_keywords}&limit=120"
        f"&maxPrice=5&minPrice=5&salesTypeFilter=1"
        f"&subcategory=Classic{selected_type}"
    )

    print(f"\n{Fore.CYAN}[RBXFETCH]{Style.RESET_ALL} Gathering clothing items...\n")

    asset_ids = []
    page_counter = 0
    current_url = search_url

    while True:
        page_counter += 1
        print(f"{Fore.YELLOW}[GATHER]{Style.RESET_ALL} Processing page {page_counter}...")

        try:
            response = session.get(current_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"{Fore.RED}[GATHER]{Style.RESET_ALL} HTTP {e.response.status_code} on page {page_counter}")
            break
        except Exception as e:
            print(f"{Fore.RED}[GATHER]{Style.RESET_ALL} Request failed on page {page_counter}: {e}")
            break

        data = response.json()
        items = data.get("data", [])

        if not items:
            print(f"{Fore.YELLOW}[GATHER]{Style.RESET_ALL} No items found on page {page_counter}")
            break

        asset_ids.extend(item["id"] for item in items)
        print(f"{Fore.GREEN}[GATHER]{Style.RESET_ALL} Collected {len(items)} items from page {page_counter}")

        next_cursor = data.get("nextPageCursor")
        if not next_cursor:
            print(f"{Fore.GREEN}[GATHER]{Style.RESET_ALL} Reached final page")
            break

        current_url = search_url + f"&cursor={next_cursor}"
        time.sleep(0.5)

    print(f"\n{Fore.GREEN}[RBXFETCH]{Style.RESET_ALL} Total items collected: {len(asset_ids)}")
    print(f"{Fore.YELLOW}[RBXFETCH]{Style.RESET_ALL} Starting download process...\n")

    successful_downloads = 0
    for asset_id in asset_ids:
        if forge_clothing(session, asset_id, selected_type, settings["use_custom_template"]):
            successful_downloads += 1

        time.sleep(2)

    print(f"\n{Fore.GREEN}[RBXFETCH]{Style.RESET_ALL} Download process completed!")
    print(f"{Fore.GREEN}[STATS]{Style.RESET_ALL} Successfully downloaded: {successful_downloads} items")
    input("\nPress Enter to exit...")
