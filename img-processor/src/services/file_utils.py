import base64
from PIL import Image
from io import BytesIO
import tempfile
import os
import shutil
from loguru import logger

class FileUtils:
    def save_decoded_image_to_disk(self, img_data, image_number):
        decoded_data = base64.b64decode(img_data)
        img = Image.open(BytesIO(decoded_data))

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{image_number}.jpg", prefix=f"image_")
        img.save(temp_file, "JPEG")
        temp_file.close()  # ensure file is written and closed before we return the name
        return temp_file.name

    def delete_tmp_contents(self):
        tmp_dir = "/tmp"

        for item in os.listdir(tmp_dir):
            item_path = os.path.join(tmp_dir, item)

            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    logger.info(f"Deleted file: {item_path}")
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    logger.info(f"Deleted directory: {item_path}")
            except OSError as e:
                logger.error(f"Error deleting {item_path}: {e}")
