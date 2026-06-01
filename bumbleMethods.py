from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import uuid
import os
import socket
import urllib.error
import urllib.request


DOWNLOAD_TIMEOUT = 10  # seconds per image


# this downloads all pictures into a folder labelled by the profiles name age and a uuid
# returns the profile id (folder name) on success, or None if no image could be saved
def find_download_all_pictures(driver, data_folder):
    idnum = str(uuid.uuid4())
    savePath = os.path.join(data_folder, idnum)
    os.makedirs(savePath, exist_ok=True)
    pictures = driver.find_elements(By.CLASS_NAME, "media-box__picture-image")
    saved = 0
    for i, pic in enumerate(pictures):
        src = pic.get_attribute("src")
        if not src:
            continue
        try:
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
                data = resp.read()
            with open(os.path.join(savePath, f"image_{i}.png"), "wb") as f:
                f.write(data)
            saved += 1
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
            print(f"  ! Skipping image {i}: {e}")
            continue
    if saved == 0:
        return None
    return idnum


# like this profile that we are working on
def like_profile(driver):
    driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.RIGHT)


# dislike the profile we are workig on
def dislike_profile(driver):
    driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.LEFT)
