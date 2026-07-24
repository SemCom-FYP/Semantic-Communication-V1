import os
import requests

BASE_URL = "https://r0k.us/graphics/kodak/kodak"
OUTPUT_DIR = "kodak_images"

os.makedirs(OUTPUT_DIR, exist_ok=True)

for i in range(1, 25):
    filename = f"kodim{i:02d}.png"
    url = f"{BASE_URL}/{filename}"

    print(f"Downloading {filename}...")

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(os.path.join(OUTPUT_DIR, filename), "wb") as f:
        f.write(response.content)

print("Done!")