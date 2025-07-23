import requests
import time
import re
import xmltodict
from .utils import sanitize_text, validate_xml
from .Debug import Debug

def acquire_csrf(session):
    Debug.warning("CSRF", "Acquiring new token...")
    try:
        csrf_req = session.post("https://auth.roblox.com/v2/logout")
        if "X-CSRF-Token" in csrf_req.headers:
            session.headers["X-CSRF-Token"] = csrf_req.headers["X-CSRF-Token"]
            Debug.success("CSRF", "Token refreshed successfully.")
            return True
        else:
            Debug.error("CSRF", "Failed to extract token from response.")
            return False
    except requests.exceptions.RequestException as e:
        Debug.error("CSRF", f"Request failed: {e}")
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
                Debug.success("NAME", f"Retrieved: '{asset_name}' for ID {asset_id}")
                return asset_name
            else:
                Debug.warning("NAME", f"No name data found for ID {asset_id} (Attempt {attempt + 1}/{max_retries})")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                Debug.error("NAME", f"HTTP 403 for ID {asset_id} (Attempt {attempt + 1}/{max_retries}). Refreshing CSRF...")
                acquire_csrf(session)
            else:
                Debug.error("NAME", f"HTTP {e.response.status_code} for ID {asset_id} (Attempt {attempt + 1}/{max_retries})")
            time.sleep(2 ** attempt)

        except Exception as e:
            Debug.error("NAME", f"Extraction failed for ID {asset_id} (Attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2 ** attempt)

    Debug.error("NAME", f"All attempts failed for ID {asset_id}. Using ID as fallback.")
    return str(asset_id)

def extract_image_id(session, asset_id):
    asset_url = f'https://assetdelivery.roblox.com/v1/asset/?id={asset_id}'

    try:
        response = session.get(asset_url)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')

        if 'xml' in content_type or validate_xml(response.content):
            Debug.warning("XML", f"Processing XML content for asset {asset_id}")

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
                        Debug.success("XML", f"Extracted image ID: {extracted_id} from asset {asset_id}")
                        return extracted_id
                    else:
                        Debug.warning("XML", f"No ID pattern found in URL: {url_path}")
                        return str(asset_id)
                else:
                    Debug.warning("XML", "No URL found in XML structure")
                    return str(asset_id)

            except Exception as e:
                Debug.error("XML", f"XML parsing failed for asset {asset_id}: {e}")
                return str(asset_id)
        else:
            Debug.warning("DIRECT", f"Asset {asset_id} contains direct image content")
            return str(asset_id)

    except requests.exceptions.HTTPError as e:
        Debug.error("EXTRACT", f"HTTP {e.response.status_code} while extracting image ID from {asset_id}")
        return None
    except Exception as e:
        Debug.error("EXTRACT", f"Extraction failed for {asset_id}: {e}")
        return None