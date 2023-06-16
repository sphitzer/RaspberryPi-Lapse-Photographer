import os
import base64
import logging
import sys
from loguru import logger

class FileUtils:
    @staticmethod
    def save_base64_image(output_path, tl_name, img_iterator, img_base64):
        """
        Save a base64 encoded image to a specified directory.

        :param output_path: The output directory where the image will be saved
        :param tl_name: The name of the timelapse folder
        :param img_iterator: The index of the image in the timelapse sequence
        :param img_base64: The base64 encoded image data
        """
        logger.info('writing image to file')

        # Save the base64 encoded image to the /capture directory
        target_path = os.path.join(output_path, tl_name, 'capture', f'image_{img_iterator}.jpg')
        with open(target_path, 'wb') as f:
            f.write(base64.b64decode(img_base64))
        
        logger.info(f'Image saved to {target_path}')


    @staticmethod
    def create_timelapse_dir(output_path, tl_name):
        """
        Create the directory structure for the timelapse.
        """
        try:
            logger.info('Creating timelapse directory...')
            original_umask = os.umask(0)
            os.makedirs(os.path.join(output_path, tl_name, 'capture'), 0o777, exist_ok=True)
            os.makedirs(os.path.join(output_path, tl_name, 'output'), 0o777, exist_ok=True)
        except OSError as ose:
            logger.info(f'Timelapse with the name {tl_name} already exists')
            sys.exit(1)
        else:
            logger.info(f'Creating timelapse... Photos located under {tl_name}/capture')
        finally:
            os.umask(original_umask)

