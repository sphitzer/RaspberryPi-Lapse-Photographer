import gphoto2 as gp
import time
import os
import base64
import logging

from loguru import logger

gp.error_severity[gp.GP_ERROR] = logging.DEBUG

class Camera:

    def __init__(self):
        self.camera = gp.Camera()

    def connect_camera(self):
        """
        Connect to the camera and return the camera object.
        """
 
        while True:
            try:
                self.camera.init()
            except gp.GPhoto2Error as ex:
                if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
                    logger.info("No camera connected - checking again in 10 seconds")
                    time.sleep(10)
                    continue
                raise
            
            # Set the camera to capture in JPEG format and 3:2 aspect ratio
            try:
                self.set_camera_capture_format(self.camera, "JPEG")
                self.set_camera_aspect_ratio(self.camera, "3:2")
                self.set_camera_focus_mode(self.camera, "manual")
            except gp.GPhoto2Error as ex:
                logger.error(f"Failed to set camera configuration: {str(ex)}")
                raise

            logger.info('Summary')
            logger.info('=======')
            logger.info(self.camera.get_summary())
            break

    def set_camera_capture_format(self, camera, format):
        format_mapping = {
            "JPEG": "Standard",
            "RAW": "RAW",
            "RAW+JPEG": "RAW & JPEG"
        }

        if format not in format_mapping:
            raise ValueError(f"Invalid format '{format}'. Supported formats are: {', '.join(format_mapping.keys())}")

        config = camera.get_config()
        capture_format = config.get_child_by_name("imagequality")

        target_format = format_mapping[format]

        for i in range(capture_format.count_choices()):
            choice_value = capture_format.get_choice(i)
            if choice_value == target_format:
                capture_format.set_value(choice_value)
                camera.set_config(config)
                logger.info(f"Camera capture format set to {format}")
                break

    def set_camera_aspect_ratio(self, camera, aspect_ratio):
        aspect_ratios = ["3:2", "16:9"]

        if aspect_ratio not in aspect_ratios:
            raise ValueError(f"Invalid aspect ratio '{aspect_ratio}'. Supported aspect ratios are: {', '.join(aspect_ratios)}")

        config = camera.get_config()
        aspect_ratio_config = config.get_child_by_name("aspectratio")

        for i in range(aspect_ratio_config.count_choices()):
            choice_value = aspect_ratio_config.get_choice(i)
            if choice_value == aspect_ratio:
                aspect_ratio_config.set_value(choice_value)
                camera.set_config(config)
                logger.info(f"Camera aspect ratio set to {aspect_ratio}")
                break

    def set_camera_focus_mode(self, camera, focus_mode):
        focus_modes = ["auto", "manual"]

        if focus_mode not in focus_modes:
            raise ValueError(f"Invalid focus mode '{focus_mode}'. Supported focus modes are: {', '.join(focus_modes)}")

        config = camera.get_config()
        focus_mode_config = config.get_child_by_name("focusmode")

        for i in range(focus_mode_config.count_choices()):
            choice_value = focus_mode_config.get_choice(i)
            if choice_value == focus_mode:
                focus_mode_config.set_value(choice_value)
                camera.set_config(config)
                logger.info(f"Camera focus mode set to {focus_mode}")
                break

    def camera_readiness_check(self):
         #Wait for the camera to be ready for capture, but retry photo if max retries hit
        max_retries_capture_readiness = 3
        for attempt in range(1, max_retries_capture_readiness + 1):
            event_type, event_data = self.camera.wait_for_event(5000)
            if event_type == gp.GP_EVENT_TIMEOUT:
                logger.warning("Camera not ready, waiting...attempt number" + str(attempt))
                if attempt == max_retries_capture_readiness:
                    logger.error("Camera not ready after maximum number of retries. Restarting camera...")
                    self.exit()
                    time.sleep(10)
                    self.connect_camera()
                    time.sleep(10)
            else:
                break
        

    # captures image and returns a base64 encoded image
    def capture_image(self, target_folder, target_name):
        try:
            logger.info('Starting capture...')
            file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE)
            logger.info("Captured " + file_path.folder + "/" + file_path.name)

            logger.info('Copy file from camera')
            camera_file = self.camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
            logger.info('Copy complete')

            logger.info('image encoding start')
            # Encode the image data in base64
            img_data = camera_file.get_data_and_size()
            img_base64 = base64.b64encode(img_data)
            logger.info('image encoded')
        except gp.GPhoto2Error as e:
            if e.code == gp.GP_ERROR_IO:
                logger.error(f'I/O problem (error code: {e.code}).')
                logger.error("Camera not ready after maximum number of retries. Restarting camera...")
                self.exit()
                time.sleep(10)
                self.connect_camera()
                time.sleep(10)
                logger.error("Camera restarted...")

                return e

            else:
                logger.error(f'An unexpected error occurred (error code: {e.code}).')
                logger.error("Camera not ready after maximum number of retries. Restarting camera...")
                self.exit()
                time.sleep(10)
                self.connect_camera()
                time.sleep(10)
                logger.error("Camera restarted...")

                return e

        return img_base64

    def exit(self):
        self.camera.exit()