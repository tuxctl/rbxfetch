import os
import string
import random
import re
import xml.etree.ElementTree as ET

def sanitize_text(text):
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
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
