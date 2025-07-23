try:
    import subprocess
    import sys
    import requests
    import xmltodict
    import os
    import string
    import random
    import re
    import json
    import platform
    import xml.etree.ElementTree as ET
    import shutil
    from PIL import Image
    from colorama import Fore, Style, init
    import time
except ImportError:
    print(f'Missing dependencies detected. Installing...')
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

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

def acquire_csrf():
    print(f"{Fore.YELLOW}[CSRF]{Style.RESET_ALL} Acquiring new token...")
    try:
        csrf_req = session.post("https://auth.roblox.com/v2/logout")
        if "X-CSRF-Token" in csrf_req.headers:
            session.headers["X-CSRF-Token"] = csrf_req.headers["X-CSRF-Token"]
            print(f"{Fore.GREEN}[CSRF]{Style.RESET_ALL} Token refreshed successfully.")
            return True
        else:
            print(f"{Fore.RED}[CSRF]{Style.RESET_ALL} Failed to extract token from response.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}[CSRF]{Style.RESET_ALL} Request failed: {e}")
        return False

acquire_csrf()

try:
    user_info = session.get("https://users.roblox.com/v1/users/authenticated").json()
    print(f"{Fore.GREEN}[AUTH]{Style.RESET_ALL} Authenticated as {user_info['name']} (ID: {user_info['id']})\n")
except Exception as e:
    print(f"{Fore.RED}[AUTH]{Style.RESET_ALL} Authentication failed: {e}")
    input("Press Enter to exit...")
    sys.exit()

logs = []

def sanitize_text(text):
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

def validate_xml(xml_content):
    try:
        ET.fromstring(xml_content)
        return True
    except ET.ParseError:
        return False

def generate_suffix():
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(4))

def create_unique_filename(directory, base_name, extension=".png"):
    separator = " $"

    clean_base = "".join(c for c in base_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
    clean_base = clean_base.replace(" ", "_") if clean_base else "unnamed"

    while True:
        suffix = generate_suffix()
        filename = f"{clean_base}{separator}{suffix}{extension}"
        full_path = os.path.join(directory, filename)

        if not os.path.exists(full_path):
            return full_path, filename

def extract_asset_name(asset_id):
    asset_name = None
    max_retries = 3

    for attempt in range(max_retries):
        try:
            payload = {
                "items": [
                    {
                        "itemType": "Asset",
                        "id": int(asset_id)
                    }
                ]
            }

            response = session.post("https://catalog.roblox.com/v1/catalog/items/details", json=payload)
            response.raise_for_status()
            catalog_data = response.json()

            if catalog_data and 'data' in catalog_data and len(catalog_data['data']) > 0:
                asset_name = sanitize_text(catalog_data['data'][0]['name'])
                print(f"{Fore.GREEN}[NAME]{Style.RESET_ALL} Retrieved: '{asset_name}' for ID {asset_id}")
                return asset_name
            else:
                print(f"{Fore.YELLOW}[NAME]{Style.RESET_ALL} No name data found for ID {asset_id} (Attempt {attempt + 1}/{max_retries})")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"{Fore.RED}[NAME]{Style.RESET_ALL} HTTP 403 for ID {asset_id} (Attempt {attempt + 1}/{max_retries}). Refreshing CSRF...")
                acquire_csrf()
            else:
                print(f"{Fore.RED}[NAME]{Style.RESET_ALL} HTTP {e.response.status_code} for ID {asset_id} (Attempt {attempt + 1}/{max_retries})")
            time.sleep(2 ** attempt)

        except Exception as e:
            print(f"{Fore.RED}[NAME]{Style.RESET_ALL} Extraction failed for ID {asset_id} (Attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2 ** attempt)

    print(f"{Fore.RED}[NAME]{Style.RESET_ALL} All attempts failed for ID {asset_id}. Using ID as fallback.")
    return str(asset_id)

def extract_image_id(asset_id):
    asset_url = f'https://assetdelivery.roblox.com/v1/asset/?id={asset_id}'

    try:
        response = session.get(asset_url)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')

        if 'xml' in content_type or validate_xml(response.content):
            print(f"{Fore.YELLOW}[XML]{Style.RESET_ALL} Processing XML content for asset {asset_id}")

            try:
                parsed_data = xmltodict.parse(response.content)
                url_path = None

                if 'roblox' in parsed_data and 'Item' in parsed_data['roblox'] and 'Properties' in parsed_data['roblox']['Item'] and 'Content' in parsed_data['roblox']['Item']['Properties'] and 'url' in parsed_data['roblox']['Item']['Properties']['Content']:
                    url_path = parsed_data['roblox']['Item']['Properties']['Content']['url']
                elif 'roblox' in parsed_data and 'ExternalFile' in parsed_data['roblox'] and 'url' in parsed_data['roblox']['ExternalFile']:
                    url_path = parsed_data['roblox']['ExternalFile']['url']

                if url_path:
                    id_match = re.search(r'id=(\d+)', url_path)
                    if id_match:
                        extracted_id = id_match.group(1)
                        print(f"{Fore.GREEN}[XML]{Style.RESET_ALL} Extracted image ID: {extracted_id} from asset {asset_id}")
                        return extracted_id
                    else:
                        print(f"{Fore.YELLOW}[XML]{Style.RESET_ALL} No ID pattern found in URL: {url_path}")
                        return str(asset_id)
                else:
                    print(f"{Fore.YELLOW}[XML]{Style.RESET_ALL} No URL found in XML structure")
                    return str(asset_id)

            except Exception as e:
                print(f"{Fore.RED}[XML]{Style.RESET_ALL} XML parsing failed for asset {asset_id}: {e}")
                return str(asset_id)
        else:
            print(f"{Fore.YELLOW}[DIRECT]{Style.RESET_ALL} Asset {asset_id} contains direct image content")
            return str(asset_id)

    except requests.exceptions.HTTPError as e:
        print(f"{Fore.RED}[EXTRACT]{Style.RESET_ALL} HTTP {e.response.status_code} while extracting image ID from {asset_id}")
        return None
    except Exception as e:
        print(f"{Fore.RED}[EXTRACT]{Style.RESET_ALL} Extraction failed for {asset_id}: {e}")
        return None

def forge_clothing(asset_id, clothing_category, apply_template):
    print(f"\n{Fore.CYAN}[FORGE]{Style.RESET_ALL} Processing asset ID: {asset_id}")

    asset_name = extract_asset_name(asset_id)

    image_id = extract_image_id(asset_id)
    if not image_id:
        print(f"{Fore.RED}[FORGE]{Style.RESET_ALL} Failed to determine image ID for asset {asset_id}")
        return False

    save_directory = os.path.join(os.getcwd(), "Assets", clothing_category)
    os.makedirs(save_directory, exist_ok=True)

    temp_path = os.path.join(save_directory, f"{asset_id}_temp.png")

    try:
        image_url = f'https://assetdelivery.roblox.com/v1/asset/?id={image_id}'
        response = session.get(image_url, stream=True)
        response.raise_for_status()

        content_length = int(response.headers.get('content-length', 0))
        min_size_threshold = 500

        if content_length > 0 and content_length < min_size_threshold:
            print(f"{Fore.YELLOW}[FORGE]{Style.RESET_ALL} Content too small ({content_length} bytes) for ID {image_id}")
            return False

        with open(temp_path, "wb") as file_handle:
            for chunk in response.iter_content(chunk_size=8192):
                file_handle.write(chunk)

        actual_size = os.path.getsize(temp_path)
        if actual_size < min_size_threshold:
            print(f"{Fore.YELLOW}[FORGE]{Style.RESET_ALL} Downloaded file too small ({actual_size} bytes). Cleaning up.")
            os.remove(temp_path)
            return False

    except requests.exceptions.HTTPError as e:
        print(f"{Fore.RED}[FORGE]{Style.RESET_ALL} HTTP {e.response.status_code} downloading image {image_id}")
        return False
    except Exception as e:
        print(f"{Fore.RED}[FORGE]{Style.RESET_ALL} Download failed for image {image_id}: {e}")
        return False

    final_path, final_filename = create_unique_filename(save_directory, asset_name)

    if apply_template:
        try:
            template_file = f"{clothing_category.lower()}.png"
            template_path = os.path.join(os.getcwd(), "Assets", "Templates", template_file)

            if not os.path.exists(template_path):
                print(f"{Fore.RED}[TEMPLATE]{Style.RESET_ALL} Template not found: {template_path}")
                shutil.move(temp_path, final_path)
                print(f"{Fore.GREEN}[FORGE]{Style.RESET_ALL} Saved (no template): {final_filename}")
                return True

            base_image = Image.open(temp_path).convert("RGBA")
            template_image = Image.open(template_path).convert("RGBA")

            if base_image.size != template_image.size:
                print(f"{Fore.YELLOW}[TEMPLATE]{Style.RESET_ALL} Resizing template from {template_image.size} to {base_image.size}")
                template_image = template_image.resize(base_image.size, Image.LANCZOS)

            base_image.paste(template_image, (0, 0), mask=template_image)
            base_image.save(final_path)

            os.remove(temp_path)

            print(f"{Fore.GREEN}[FORGE]{Style.RESET_ALL} Templated and saved: {final_filename}")
            return True

        except Exception as e:
            print(f"{Fore.RED}[TEMPLATE]{Style.RESET_ALL} Template application failed: {e}")
            if os.path.exists(temp_path):
                shutil.move(temp_path, final_path)
                print(f"{Fore.YELLOW}[FORGE]{Style.RESET_ALL} Saved (template error): {final_filename}")
            return True
    else:
        if os.path.exists(temp_path):
            shutil.move(temp_path, final_path)
            print(f"{Fore.GREEN}[FORGE]{Style.RESET_ALL} Saved: {final_filename}")
            return True
        else:
            print(f"{Fore.RED}[FORGE]{Style.RESET_ALL} Temp file missing for asset {asset_id}")
            return False

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
    if forge_clothing(asset_id, selected_type, settings["use_custom_template"]):
        successful_downloads += 1

    time.sleep(2)

print(f"\n{Fore.GREEN}[RBXFETCH]{Style.RESET_ALL} Download process completed!")
print(f"{Fore.GREEN}[STATS]{Style.RESET_ALL} Successfully downloaded: {successful_downloads} items")
input("\nPress Enter to exit...")
