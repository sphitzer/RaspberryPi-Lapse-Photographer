import glob, os, base64
from .kafkahelper import KafkaHelper

from loguru import logger


class ReprocessTimelapse:
    def __init__(self, output_path, name, bootstrap_servers, topic_name):
        self.output_path = output_path
        self.kafka = KafkaHelper(bootstrap_servers)
        self.topic_name = topic_name
        self.name = name
        
    def reprocess(self):
        # List all jpg files in output_path
        file_list = glob.glob(os.path.join(self.output_path, self.name, 'capture/*.jpg'))
        
        # Define a custom sorting function that extracts the number from the filename
        def get_img_number(filename):
            base = os.path.basename(filename)
            img_number = int(base.split('_')[1].split('.')[0])
            return img_number

        # Sort the list of files in numerical order
        file_list = sorted(file_list, key=get_img_number)
        
        for file_path in file_list:
            logger.info("Uploading File: " + str(file_path))

            with open(file_path, 'rb') as img_file:
                # Read the image data and encode it in base64
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data)
                
                # Put the base64-encoded image data onto the Kafka queue
                self.kafka.place_image_on_kafka_queue(img_base64, self.topic_name)
