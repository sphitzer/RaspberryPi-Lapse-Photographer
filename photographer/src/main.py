import gphoto2 as gp
import os
import sys
import time
import argparse
import logging
from loguru import logger
import base64
from confluent_kafka import Producer, KafkaError

gp.error_severity[gp.GP_ERROR] = logging.DEBUG


class Timelapse:
    def __init__(self, output_path, tl_name, interval, frames, kafka_bootstrap_servers):
        self.output_path = output_path
        self.tl_name = tl_name
        self.interval = interval
        self.frames = frames
        self.capture_path = os.path.join(self.output_path, self.tl_name, 'capture')
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.producer = self.create_producer()


    def create_timelapse_dir(self):
        """
        Create the directory structure for the timelapse.
        """
        try:
            logger.info('Creating timelapse directory...')
            original_umask = os.umask(0)
            os.makedirs(os.path.join(self.output_path, self.tl_name, 'capture'), 0o777, exist_ok=True)
            os.makedirs(os.path.join(self.output_path, self.tl_name, 'output'), 0o777, exist_ok=True)
        except OSError as ose:
            logger.info(f'Timelapse with the name {self.tl_name} already exists')
            sys.exit(1)
        else:
            logger.info(f'Creating timelapse... Photos located under {self.tl_name}/capture')
        finally:
            os.umask(original_umask)

    def connect_camera(self):
        """
        Connect to the camera and return the camera object.
        """
        camera = gp.Camera()

        while True:
            try:
                camera.init()
            except gp.GPhoto2Error as ex:
                if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
                    logger.info("No camera connected - checking again in 10 seconds")
                    time.sleep(10)
                    continue
                raise
            
            # Set the camera to capture in JPEG format and 3:2 aspect ratio
            try:
                self.set_camera_capture_format(camera, "JPEG")
                self.set_camera_aspect_ratio(camera, "3:2")
            except gp.GPhoto2Error as ex:
                logger.error(f"Failed to set camera configuration: {str(ex)}")
                raise



            logger.info('Summary')
            logger.info('=======')
            logger.info(camera.get_summary())
            break

        return camera

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

    def create_producer(self):
        conf = {
                'bootstrap.servers': self.kafka_bootstrap_servers,
                'message.max.bytes':1000000000
            }
        producer = Producer(conf)
        return producer

    def send_message(self, topic, value):
        self.producer.produce(topic, value)
        self.producer.flush()

    def execute_timelapse(self, camera):
        """
        Execute the timelapse by taking photos with the given camera.
        """

        # Initialize the Kafka producer
        producer = self.create_producer

        for x in range(self.frames):
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:

                    logger.info('Starting capture...')
                    file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
                    logger.info(f'Camera file path: {file_path.folder}/{file_path.name}')
                    target = os.path.join(self.capture_path, file_path.name)
                    #logger.info(f'Copying image to {target}')
                    camera_file = camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
                    # camera_file.save(target)
                    logger.info('Copy complete')

                    logger.info('Start send to Kafka queue')
                    # Encode the image data in base64
                    img_data = camera_file.get_data_and_size()
                    img_base64 = base64.b64encode(img_data)
                    logger.info('image encoded')

                    # Send the base64-encoded image data to the Kafka queue
                    #producer.send('timelapse_images', img_base64)
                     #handle kafak upload
                    def on_send_success(record_metadata):
                        logger.info(f"Message sent successfully to topic {record_metadata.topic} at offset {record_metadata.offset}")

                    def on_send_error(excp):
                        logger.error(f"Error while sending message to Kafka: {excp}", exc_info=True)

 
                    try:
                        # Send the base64-encoded image data to the Kafka queue
                        #future = self.send_message('timelapse_images2', img_base64)
                        self.send_message('timelapse_images2', img_base64)
                        # Add the success and error callbacks
                        #future.add_callback(on_send_success)
                        #future.add_errback(on_send_error)
                        self.producer.flush()
                    except AssertionError as e:
                        logger.error(f"Error in file format potentially??!!??: {e}", exc_info=True)
                    except KafkaError as e:
                        logger.error(f"Error during timelapse execution: {e}", exc_info=True)

                    logger.info('Image sent to Kafka queue')


                    #Wait for the camera to be ready for capture, but retry photo if max retries hit
                    max_retries_capture_readiness = 3
                    for attempt in range(1, max_retries_capture_readiness + 1):
                        event_type, event_data = camera.wait_for_event(1000)
                        if event_type == gp.GP_EVENT_TIMEOUT:
                            logger.warning("Camera not ready, waiting...attempt number" + str(attempt))
                            continue

                    time.sleep(self.interval)
                    logger.info("Sleeping for interval:" + str(self.interval))
                    break  # Break the retry loop if the capture is successful

                except KafkaError as e:
                    logger.error(f'Error sending image to Kafka queue: {e}')    
                except gp.GPhoto2Error as e:
                    if e.code == gp.GP_ERROR_IO:
                        logger.warning(f'I/O problem (error code: {e.code}). Attempt {attempt} of {max_retries}')
                        if attempt < max_retries:
                            time.sleep(5)  # Wait for 5 seconds before retrying
                        else:
                            logger.error(f'Capture failed after {max_retries} attempts due to I/O problem')
                    else:
                        logger.error(e)
                except BaseException as e:
                    logger.error(str(e))


    def run(self):
        # try:
            self.create_timelapse_dir()
            camera = self.connect_camera()
            try:
                self.execute_timelapse(camera)
            except Exception as e:
                logger.error(f"Error during timelapse execution: {e}")
            finally:
                camera.exit()
        # except Exception as e:
        #     logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timelapse via picamera or gphoto2')

    parser.add_argument('--name', required=True, type=str, dest='name', help='Name of folder timelapse to be saved in')
    parser.add_argument('--outputpath', required=True, type=str, dest='output_path', help='Output dir that will hold newly created timelapse dir')
    parser.add_argument('--frames', required=True, type=int, dest='frames', help='Total number of photos to be taken')
    parser.add_argument('--interval', required=True, dest='interval', type=int, help='Time between each photo in seconds')
    parser.add_argument('--kafka-bootstrap-servers', required=True, type=str, dest='kafka_bootstrap_servers',
                            help='Kafka bootstrap servers (e.g., "localhost:9092")')

    args = parser.parse_args()

    timelapse = Timelapse(args.output_path, args.name, args.interval, args.frames, args.kafka_bootstrap_servers)
    timelapse.run()
