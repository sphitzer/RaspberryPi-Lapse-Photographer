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
from confluent_kafka import Consumer, KafkaError
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
    def __init__(self, name, timelapse_dir, s3bucket, kafka_bootstrap_servers, threshold, max_limit):
        self.name = name
        self.timelapse_dir = timelapse_dir
        self.s3bucket = s3bucket
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.consumer = self.create_consumer("timelapse_consumer_group1", "timelapse_images2" )
        self.threshold = threshold
        self.max_limit = max_limit

    # def generate_video_from_photos(self, image_file_paths, video_name_counter):
    #     capture_parent_dir = os.path.join(self.timelapse_dir, self.name)
    #     file_output_name = self.name
    #     output_path = os.path.join(capture_parent_dir, 'output', f"{file_output_name}{video_name_counter}.mp4")

    #   # List all files in the /tmp directory
    #     all_files = os.listdir("/tmp")

    #     # Filter files that match the required pattern
    #     filtered_files = [f for f in all_files if re.match(r"image_.*_\d+\.jpg", f)]

    #     # Sort the files by the counter at the end
    #     sorted_files = sorted(filtered_files, key=lambda x: int(re.search(r"\d+(?=.jpg)", x).group()))

    #     # Write the sorted file list to a text file
    #     logger.info("Writing sorted file list to /tmp/file_list.txt")
    #     with open("/tmp/file_list.txt", "w") as f:
    #         for file in sorted_files:
    #             f.write(f"file '/tmp/{file}'\n")

    #     # Use the file list as input for ffmpeg
    #     logger.info("Concatenating files into timelapse and applying filters with ffmpeg")
    #     (
    #         ffmpeg
    #         .input("/tmp/file_list.txt", format="concat", safe=0)
    #         .filter('deflicker', mode='pm', size=10)
    #         .filter('scale', size='3840x2160', force_original_aspect_ratio='increase')
    #         #.drawtext(text="Hi",start_number=0,fontsize="64",escape_text=True, fontcolor="red",x=40,y=100)
    #         .output('/tmp/current_video.mp4', crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
    #         .run(overwrite_output=True)
    #     )

    #      # Get a list of all previous video files
    #     logger.info("Getting a list of all previous video files")
    #     video_files = sorted(glob.glob(os.path.join(capture_parent_dir, 'output', f"{file_output_name}*.mp4")))
    #     logger.info("Video files: " + str(video_files))

    #     # If there is a previous video file, concatenate it with the current video
    #     if video_files:
    #         logger.info("Previous video files found, concatenating with current video")
    #         # Check if there are more than 9 video files
    #         if len(video_files) % 10 == 0:
    #             logger.info("More than 9 video files, creating an intermediate video")
    #             intermediate_video = os.path.join(capture_parent_dir, 'output', f"{file_output_name}_intermediate_{len(video_files) // 10}.mp4")
    #             (
    #                 ffmpeg
    #                 .concat(*[ffmpeg.input(video) for video in video_files], v=1, a=0)
    #                 .output(intermediate_video, crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
    #                 .run(overwrite_output=True)
    #             )
    #             # Remove previous video files
    #             logger.info("Removing previous video files")
    #             for video in video_files:
    #                 os.remove(video)

    #             # Add the intermediate video to the video_files list
    #             logger.info("Adding intermediate video to the video_files list")
    #             video_files.append(intermediate_video)

    #         last_video = video_files[-1]
    #         input1 = ffmpeg.input(last_video)
    #         input2 = ffmpeg.input('/tmp/current_video.mp4')

    #         logger.info("Concatenating current video with the last video")
    #         (
    #             ffmpeg
    #             .concat(input1, input2, v=1, a=0)
    #             .output(output_path, crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
    #             .run(overwrite_output=True)
    #         )
    #     else:
    #         logger.info("No previous video files, moving current video to the output path")
    #         # If there is no previous video file, simply move the current video to the output path
    #         shutil.copy('/tmp/current_video.mp4', output_path)

    #     file_size = os.path.getsize(output_path)
    #     logger.info(f"Current video size is {file_size} bytes")

    #     return output_path

    def generate_video_from_photos(self, image_file_paths, video_name_counter):
        capture_parent_dir = os.path.join(self.timelapse_dir, self.name)
        file_output_name = self.name
        output_path = os.path.join(capture_parent_dir, 'output', f"{file_output_name}{video_name_counter}.mp4")

        # Now using image_file_paths instead of listing files in /tmp (that are of type string)
        # Sort the image file paths based on the numeric part of their filenames
        logger.info(f"image_file_paths content: {image_file_paths}")
        sorted_files = sorted([i for i in image_file_paths if isinstance(i, str)], key=lambda x: int(re.search(r"\d+(?=.jpg)", x).group()))


        # Write the sorted file list to a text file
        logger.info("Writing sorted file list to /tmp/file_list.txt")
        with open("/tmp/file_list.txt", "w") as f:
            for file in sorted_files:
                f.write(f"file '{file}'\n")

        # Use the file list as input for ffmpeg
        logger.info("Concatenating files into timelapse and applying filters with ffmpeg")
        (
            ffmpeg
            .input("/tmp/file_list.txt", format="concat", safe=0)
            .filter('deflicker', mode='pm', size=10)
            .filter('scale', size='3840x2160', force_original_aspect_ratio='increase')
            .output('/tmp/current_video.mp4', crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
            .run(overwrite_output=True)
        )

        # Get a list of all previous video files
        logger.info("Getting a list of all previous video files")
        video_files = sorted(glob.glob(os.path.join(capture_parent_dir, 'output', f"{file_output_name}*.mp4")), 
                            key=lambda x: int(re.search(r"\d+(?=\.mp4)", x).group()))  # sort based on numeric part
        logger.info("Video files: " + str(video_files))

        # If there are previous video files, concatenate them with the current video
        if video_files:
            logger.info("Previous video files found, concatenating with current video")
            inputs = [ffmpeg.input(video) for video in video_files]
            inputs.append(ffmpeg.input('/tmp/current_video.mp4'))

            logger.info("Concatenating current video with all previous videos")
            (
                ffmpeg
                .concat(*inputs, v=1, a=0)
                .output(output_path, crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
                .run(overwrite_output=True)
            )
            for video in video_files:
                os.remove(video)  # remove old videos after successfully concatenating them
        else:
            logger.info("No previous video files, moving current video to the output path")
            # If there are no previous video files, simply move the current video to the output path
            shutil.copy('/tmp/current_video.mp4', output_path)

        file_size = os.path.getsize(output_path)
        logger.info(f"Current video size is {file_size} bytes")

        return output_path


    def upload_to_s3(self, file_path, object_name=None):
        logger.info("Starting s3 upload")
        if object_name is None:
            object_name = os.path.basename(file_path)

        s3_client = boto3.client('s3')
        try:
            response = s3_client.upload_file(file_path, self.s3bucket, object_name)
        except ClientError as e:
            logger.error(e)
            logger.info("Failed s3 upload")
            return False
        
        logger.info("Completed s3 upload")
        return True
    

    def mux_download_from_s3(self, file_name, bucket_name, previous_playback_id):
        # Create a session for requests with retries
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Check if the asset with the same file name already exists
        list_assets_response = assets_api.list_assets()
        for asset in list_assets_response.data:
            for playback_id in asset.playback_ids:
                existing_asset = None
                logger.info(f"Previous playback ID: {previous_playback_id}")
                logger.info(f"Current playback ID: {playback_id.id}")

                if previous_playback_id is not None:
                    if previous_playback_id == playback_id.id:
                        existing_asset = asset
                        logger.info(f"deleting existing asset {existing_asset.id}")
                        # Delete the existing asset
                        assets_api.delete_asset(existing_asset.id)

        def create_asset_with_retry():
            try:
                input_settings = [mux_python.InputSettings(url=f'https://{bucket_name}.s3.us-east-2.amazonaws.com/{file_name}.mp4',name=f'{file_name}')]
                create_asset_request = mux_python.CreateAssetRequest(input=input_settings)
                create_asset_response = assets_api.create_asset(create_asset_request)
                assert create_asset_response is not None
                assert create_asset_response.data.id is not None
                logger.info("create-asset OK ✅")
                return create_asset_response
            except Exception as e:
                logger.error(f"Error creating asset: {e}")
                return None

        create_asset_response = None
        for _ in range(3):
            create_asset_response = create_asset_with_retry()
            if create_asset_response is not None:
                break
            time.sleep(1)

        if create_asset_response is None:
            logger.error("Failed to create asset after retries")
            return None

        # ========== create-asset-playback-id ==========
        def create_playback_id_with_retry():
            try:
                create_playback_id_request = mux_python.CreatePlaybackIDRequest(policy=mux_python.PlaybackPolicy.PUBLIC)
                create_asset_playback_id_response = assets_api.create_asset_playback_id(create_asset_response.data.id, create_playback_id_request, _request_timeout=10)
                assert create_asset_playback_id_response is not None
                assert create_asset_playback_id_response.data is not None
                logger.info(str(create_asset_playback_id_response.data.id))
                logger.info("create-asset-playback-id OK ✅")
                return create_asset_playback_id_response.data.id
            except Exception as e:
                logger.error(f"Error creating playback ID: {e}")
                return None

        playback_id = None
        for _ in range(3):
            playback_id = create_playback_id_with_retry()
            if playback_id is not None:
                break
            time.sleep(1)

        if playback_id is None:
            logger.error("Failed to create playback ID after retries")
            return None

        return playback_id
    
    def create_consumer(self, group_id, topic):
        conf = {
            'bootstrap.servers': self.kafka_bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
        }

        consumer = Consumer(conf)
        consumer.subscribe([topic])

        return consumer


    def delete_tmp_contents(self):
        tmp_dir = "/tmp"

        for item in os.listdir(tmp_dir):
            item_path = os.path.join(tmp_dir, item)

            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Error deleting {item_path}: {e}")

    def save_decoded_image_to_disk(self, img_data, image_number):
        decoded_data = base64.b64decode(img_data)
        img = Image.open(BytesIO(decoded_data))

        temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=f"_{image_number}.jpg", prefix=f"image_")
        img.save(temp_file, "JPEG")
        return temp_file

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
            img_file_path = self.save_decoded_image_to_disk(msg.value(), len(images))
            images.append(img_file_path)
            logger.info(f"appended image {counter}")

            counter += 1

            if counter >= self.threshold:
                video_name_counter += 1
                logger.info(str(video_name_counter))
                video_path = self.generate_video_from_photos(images, video_name_counter)
                self.upload_to_s3(video_path)
                asset_playback_id = self.mux_download_from_s3(f"{self.name}{video_name_counter}", self.s3bucket, previous_playback_id)

                #reset for next timelapse
                self.delete_tmp_contents()
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

async def async_run_timelapse_generator(name, timelapse_dir, s3bucket, kafka_bootstrap_servers,threshold, max_limit):
    timelapse_generator = TimelapseGenerator(name, timelapse_dir, s3bucket, kafka_bootstrap_servers,threshold, max_limit)
    timelapse_generator.run()
    del timelapse_generator

@app.post("/start_timelapse_generator/")
async def start_timelapse_generator(
    background_tasks: BackgroundTasks,
    name: str = Query(..., description="Name of folder timelapse to be saved in"),
    timelapse_dir: str = Query(..., description="Dir that holds created timelapse & output"),
    s3bucket: str = Query(..., description="Name of the bucket where file will be uploaded and mux will download from, e.g. timelapseuploadsfortwentyfivecents2"),
    kafka_bootstrap_servers: str = Query(..., description="Kafka bootstrap servers, e.g. broker:9092"),
    threshold: int = Query(..., description="How many photos per timelapse section"),
    max_limit: int = Query(..., description="Maximum number of photos to process for this timelapse")
):
    background_tasks.add_task(async_run_timelapse_generator, name, timelapse_dir, s3bucket, kafka_bootstrap_servers, threshold, max_limit)
    return {"message": "Timelapse generator started"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8020)

