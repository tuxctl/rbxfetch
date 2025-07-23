import sys
import requests
import json
import time
from .roblox_api import acquire_csrf
from .processor import forge_clothing
from .Debug import Debug

def run():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        Debug.error("FATAL","config.json not found. Aborting execution.")
        input("Press Enter to exit...")
        sys.exit()
    except json.JSONDecodeError:
        Debug.error("FATAL", "Malformed config.json detected. Fix and restart.")
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
        Debug.success("AUTH",f"Authenticated as {user_info['name']} (ID: {user_info['id']})\n")

    except Exception as e:
        Debug.error("AUTH",f"Authentication failed: {e}")
        input("Press Enter to exit...")
        sys.exit()

    clothing_types = {
        "s": "Shirts", "shirt": "Shirts", "shirts": "Shirts",
        "p": "Pants", "pant": "Pants", "pants": "Pants"
    }

    user_choice = input("Clothing type (s/p): ").lower()
    selected_type = clothing_types.get(user_choice)

    if not selected_type:
        Debug.error("INPUT", "Invalid clothing type selected.")
        input("Press Enter to exit...")
        sys.exit()

    Debug.info("RBXFETCH", f"Selected: {selected_type}")

    search_keywords = input("Enter search keywords (e.g., emo goth y2k): ").strip().replace(" ", "+").lower()

    search_url = (
        f"https://catalog.roblox.com/v1/search/items?"
        f"category=Clothing&keyword={search_keywords}&limit=120"
        f"&maxPrice=5&minPrice=5&salesTypeFilter=1"
        f"&subcategory=Classic{selected_type}"
    )

    print()
    Debug.info("RBXFETCH", "Gathering clothing items...\n")

    asset_ids = []
    page_counter = 0
    current_url = search_url

    while True:
        page_counter += 1
        Debug.warning("GATHER", f"Processing page {page_counter}...")

        try:
            response = session.get(current_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            Debug.error("GATHER", f"HTTP {e.response.status_code} on page {page_counter}")
            break
        except Exception as e:
            Debug.error("GATHER", f"Request failed on page {page_counter}: {e}")
            break

        data = response.json()
        items = data.get("data", [])

        if not items:
            Debug.warning("GATHER", f"No items found on page {page_counter}")
            break

        asset_ids.extend(item["id"] for item in items)
        Debug.success("GATHER", f"Collected {len(items)} items from page {page_counter}")

        next_cursor = data.get("nextPageCursor")
        if not next_cursor:
            Debug.success("GATHER", "Reached final page")
            break

        current_url = search_url + f"&cursor={next_cursor}"
        time.sleep(0.5)

    print()
    Debug.success("RBXFETCH", f"Total items collected: {len(asset_ids)}")
    Debug.warning("RBXFETCH", "Starting download process...\n")

    successful_downloads = 0
    for asset_id in asset_ids:
        if forge_clothing(session, asset_id, selected_type, settings["use_custom_template"]):
            successful_downloads += 1

        time.sleep(2)

    print()
    Debug.success("RBXFETCH", "Download process completed!")
    Debug.success("STATS", f"Successfully downloaded: {successful_downloads} items")
    input("\nPress Enter to exit...")