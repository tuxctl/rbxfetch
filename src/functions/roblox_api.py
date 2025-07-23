import requests
import time
import re
import xmltodict
from colorama import Fore, Style
from .utils import sanitize_text, validate_xml

def acquire_csrf(session):
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

def extract_asset_name(session, asset_id):
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
                acquire_csrf(session)
            else:
                print(f"{Fore.RED}[NAME]{Style.RESET_ALL} HTTP {e.response.status_code} for ID {asset_id} (Attempt {attempt + 1}/{max_retries})")
            time.sleep(2 ** attempt)

        except Exception as e:
            print(f"{Fore.RED}[NAME]{Style.RESET_ALL} Extraction failed for ID {asset_id} (Attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2 ** attempt)

    print(f"{Fore.RED}[NAME]{Style.RESET_ALL} All attempts failed for ID {asset_id}. Using ID as fallback.")
    return str(asset_id)

def extract_image_id(session, asset_id):
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
