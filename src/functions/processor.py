import os
import shutil
import requests
from PIL import Image
from .roblox_api import extract_asset_name, extract_image_id
from .utils import create_unique_filename
from .Debug import Debug

def forge_clothing(session, asset_id, clothing_category, apply_template):
    print()
    Debug.info("FORGE", f"Processing asset ID: {asset_id}")

    asset_name = extract_asset_name(session, asset_id)

    image_id = extract_image_id(session, asset_id)
    if not image_id:
        Debug.error("FORGE", f"Failed to determine image ID for asset {asset_id}")
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
            Debug.warning("FORGE", f"Content too small ({content_length} bytes) for ID {image_id}")
            return False

        with open(temp_path, "wb") as file_handle:
            for chunk in response.iter_content(chunk_size=8192):
                file_handle.write(chunk)

        actual_size = os.path.getsize(temp_path)
        if actual_size < min_size_threshold:
            Debug.warning("FORGE", f"Downloaded file too small ({actual_size} bytes). Cleaning up.")
            os.remove(temp_path)
            return False

    except requests.exceptions.HTTPError as e:
        Debug.error("FORGE", f"HTTP {e.response.status_code} downloading image {image_id}")
        return False
    except Exception as e:
        Debug.error("FORGE", f"Download failed for image {image_id}: {e}")
        return False

    final_path, final_filename = create_unique_filename(save_directory, asset_name)

    if apply_template:
        try:
            template_file = f"{clothing_category.lower()}.png"
            template_path = os.path.join(os.getcwd(), "Assets", "Templates", template_file)

            if not os.path.exists(template_path):
                Debug.error("TEMPLATE", f"Template not found: {template_path}")
                shutil.move(temp_path, final_path)
                Debug.success("FORGE", f"Saved (no template): {final_filename}")
                return True

            base_image = Image.open(temp_path).convert("RGBA")
            template_image = Image.open(template_path).convert("RGBA")

            if base_image.size != template_image.size:
                Debug.warning("TEMPLATE", f"Resizing template from {template_image.size} to {base_image.size}")
                template_image = template_image.resize(base_image.size, Image.LANCZOS)

            base_image.paste(template_image, (0, 0), mask=template_image)
            base_image.save(final_path)

            os.remove(temp_path)

            Debug.success("FORGE", f"Templated and saved: {final_filename}")
            return True

        except Exception as e:
            Debug.error("TEMPLATE", f"Template application failed: {e}")
            if os.path.exists(temp_path):
                shutil.move(temp_path, final_path)
                Debug.warning("FORGE", f"Saved (template error): {final_filename}")
            return True
    else:
        if os.path.exists(temp_path):
            shutil.move(temp_path, final_path)
            Debug.success("FORGE", f"Saved: {final_filename}")
            return True
        else:
            Debug.error("FORGE", f"Temp file missing for asset {asset_id}")
            return False