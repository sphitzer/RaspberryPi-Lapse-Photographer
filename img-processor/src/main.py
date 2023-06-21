# Standard library
import argparse
import base64
import glob
import hashlib
import hmac
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from io import BytesIO
from urllib.parse import urlencode, urlunparse

# Third-party libraries
import boto3
import ffmpeg
import mux_python
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Query
from loguru import logger
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from PIL import Image
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import uvicorn

#local services
from services.file_utils import FileUtils
from services.kafka_utils import KafkaUtils
from services.mux_utils import MuxUtils
from services.s3_utils import S3Utils
from services.video_utils import VideoUtils

# Load environment variables
load_dotenv()

# Mux auth setup
configuration = mux_python.Configuration()
configuration.username = os.environ['MUX_ACCESSS_TOKEN_ID']
configuration.password = os.environ['MUX_SECRET_KEY']

# Mux API Client Initialization
assets_api = mux_python.AssetsApi(mux_python.ApiClient(configuration))
playback_ids_api = mux_python.PlaybackIDApi(mux_python.ApiClient(configuration))


class TimelapseGenerator:
    def __init__(self, name, timelapse_dir, s3bucket, kafka_bootstrap_servers, threshold, max_limit, topic_name):
        self.name = name
        self.timelapse_dir = timelapse_dir

        # move these initializations out of init
        self.video_utils = VideoUtils(timelapse_dir=timelapse_dir, name=name)

        self.s3bucket = s3bucket
        self.s3_utils = S3Utils(s3bucket)

        kafka_utils = KafkaUtils(kafka_bootstrap_servers=kafka_bootstrap_servers)
        self.consumer = kafka_utils.create_consumer(group_id="timelapse_consumer_group1", topic=topic_name)

        self.mux_utils = MuxUtils(assets_api)

        self.file_utils = FileUtils()


        self.threshold = threshold
        self.max_limit = max_limit

    def process_messages(self):
        previous_playback_id = None
        video_name_counter = 0
        no_messages_counter = 0
        counter = 0
        images = []

        while True:
            logger.info(f"Polling messages (iteration {counter})...") 
            msg = self.consumer.poll(0.2)

            if msg is None:
                no_messages_counter += 1

                if no_messages_counter > 10000:
                    logger.info("Broke loop due to no messages on queue... make this better...")
                    break

                continue
            
            if msg.error():
                logger.error (f"Msg: {counter} error while consuming message: {msg.error()} ")
                continue

            logger.info(f"Consumed message {counter}")
            img_file_path = self.file_utils.save_decoded_image_to_disk(msg.value(), len(images))
            images.append(img_file_path)
            logger.info(f"appended image {counter}")

            counter += 1

            if counter >= self.threshold:
                video_name_counter += 1
                logger.info(str(video_name_counter))
                #video_path = self.generate_video_from_photos(images, video_name_counter)
                video_path = self.video_utils.generate_video_from_photos(images, video_name_counter)

                logger.info(f"Video path: {str(video_path)}")

                #self.upload_to_s3(4)
                self.s3_utils.upload_to_s3(file_path=video_path)


                #asset_playback_id = self.mux_download_from_s3(f"{self.name}{video_name_counter}", self.s3bucket, previous_playback_id)
                asset_playback_id = self.mux_utils.mux_download_from_s3(video_path, self.s3bucket, previous_playback_id)

                #reset for next timelapse
                self.file_utils.delete_tmp_contents()
                images = []
                counter = 0
                previous_playback_id = asset_playback_id

            if counter >= self.max_limit:
                logger.info(str(video_name_counter))
                break

  
                    
    def run(self):
        self.process_messages()


app = FastAPI()

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

FastAPIInstrumentor.instrument_app(app)

async def async_run_timelapse_generator(name, timelapse_dir, s3bucket, kafka_bootstrap_servers,threshold, max_limit, topic_name):
    timelapse_generator = TimelapseGenerator(name, timelapse_dir, s3bucket, kafka_bootstrap_servers,threshold, max_limit, topic_name)
    timelapse_generator.run()
    del timelapse_generator

@app.post("/start_timelapse_generator/")
async def start_timelapse_generator(
    background_tasks: BackgroundTasks,
    name: str = Query(..., description="Name of folder timelapse to be saved in"),
    timelapse_dir: str = Query(..., description="Dir that holds created timelapse & output", example="/output"),
    s3bucket: str = Query(..., description="Name of the bucket where file will be uploaded and mux will download from, e.g. timelapseuploadsfortwentyfivecents2", example="timelapseuploadsfortwentyfivecents2"),
    kafka_bootstrap_servers: str = Query(..., description="Kafka bootstrap servers, e.g. broker:9092", example="broker:9092"),
    threshold: int = Query(..., description="How many photos per timelapse section", example=100),
    max_limit: int = Query(..., description="Maximum number of photos to process for this timelapse", example=1000),
    topic_name: str = Query(..., description="name of the kafka topic holding the photos", example="timelapse_images4")
):
    background_tasks.add_task(async_run_timelapse_generator, name, timelapse_dir, s3bucket, kafka_bootstrap_servers, threshold, max_limit, topic_name)
    return {"message": "Timelapse generator started"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8020)

