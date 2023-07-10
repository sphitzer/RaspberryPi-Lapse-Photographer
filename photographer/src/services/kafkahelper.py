from confluent_kafka import Producer, KafkaError
from loguru import logger


class KafkaHelper:
    def __init__(self, kafka_bootstrap_server):
        self.kafka_bootstrap_servers = kafka_bootstrap_server
        self.producer = self.create_producer()

    def create_producer(self):
        conf = {
                'bootstrap.servers': self.kafka_bootstrap_servers,
                'message.max.bytes':1000000000
            }
        producer = Producer(conf)
        return producer

    def send_message(self, topic, value, callback=None):
        self.producer.produce(topic, value, callback=callback)
        self.producer.flush()

    def on_send_success(self, record_metadata):
        logger.info(f"Message sent successfully to topic {record_metadata.topic} at offset {record_metadata.offset}")

    def on_send_error(self, excp):
        logger.error(f"Error while sending message to Kafka: {excp}", exc_info=True)

    def place_image_on_kafka_queue(self, img_base64, topic):
        logger.info('Start send to Kafka queue')

        try:
            # Send the base64-encoded image data to the Kafka queue
            self.send_message(topic, img_base64, callback=self.kafka_callback)
            self.producer.flush()
        except AssertionError as e:
            logger.error(f"Error in file format potentially??!!??: {e}", exc_info=True)
        except KafkaError as e:
            logger.error(f"Error during timelapse execution: {e}", exc_info=True)

        logger.info('Image sent to Kafka queue')

    def kafka_callback(self, err, msg):
        if err is not None:
            self.on_send_error(err)
        else:
            self.on_send_success(msg)