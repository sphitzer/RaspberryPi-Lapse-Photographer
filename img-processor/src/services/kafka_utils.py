from confluent_kafka import Consumer

class KafkaUtils:
    def __init__(self, kafka_bootstrap_servers):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers

    def create_consumer(self, group_id, topic):
        conf = {
            'bootstrap.servers': self.kafka_bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
        }

        consumer = Consumer(conf)
        consumer.subscribe([topic])

        return consumer
    