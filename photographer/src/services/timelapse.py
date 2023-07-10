import sys
import time
import os
import base64

from .camera import Camera 
from .kafkahelper import KafkaHelper
from .fileutils import FileUtils

from loguru import logger

class Timelapse:
    def __init__(self, output_path, tl_name, interval, frames, kafka_bootstrap_servers, topic_name):
        self.output_path = output_path
        self.tl_name = tl_name
        self.interval = interval
        self.frames = frames
        self.capture_path = os.path.join(self.output_path, self.tl_name, 'capture')
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self. topic_name = topic_name
        self.img_iterator = 0

        self.camera = Camera()
        self.kafka = KafkaHelper(self.kafka_bootstrap_servers)
        self.producer = self.kafka.create_producer()

    def run(self):
        self.camera.connect_camera()

        try:
            self.execute_timelapse()
        except Exception as e:
            logger.error(f"Error during timelapse execution: {e}")
        finally:
            self.camera.exit()

    def execute_timelapse(self):
        """
        Execute the timelapse by taking photos with the given camera.
        """

        logger.info("Starting Timelapse")

        for x in range(self.frames):
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    #determine if camera ready
                    self.camera.camera_readiness_check()

                    # capture image w/ camera & return base64 encoded image
                    img_base64 = self.camera.capture_image(self.output_path, self.tl_name)
      
                    # place image on kafka queue 
                    self.kafka.place_image_on_kafka_queue(img_base64,self.topic_name)

                    # save image to disk (make this optional)
                    FileUtils.save_base64_image(self.output_path, self.tl_name, self.img_iterator, img_base64)

                    # Increment the iterator for the next image
                    self.img_iterator += 1

                    break  # Break the retry loop if the capture is successful

                except BaseException as e:
                    logger.error(str(e))
    
            # sleep for provided interval (seconds)
            logger.info("Sleeping for interval (seconds): " + str(self.interval))
            time.sleep(self.interval)

        logger.info("Timelapse Completed")

