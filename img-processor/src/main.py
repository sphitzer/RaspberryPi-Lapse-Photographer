import sys, os, time
import argparse
import logging
from loguru import logger
import ffmpeg
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import mux_python
from confluent_kafka import Consumer, KafkaError
from io import BytesIO
from PIL import Image
import tempfile
import shutil
import logging
#import kafka
import base64
from fastapi import FastAPI, Query, BackgroundTasks
import uvicorn
import glob
import re

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
    def __init__(self, name, timelapse_dir, s3bucket, kafka_bootstrap_servers, threshold):
        self.name = name
        self.timelapse_dir = timelapse_dir
        self.s3bucket = s3bucket
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.consumer = self.create_consumer("timelapse_consumer_group1", "timelapse_images2" )
        self.threshold = threshold

    def generate_video_from_photos(self, image_file_paths, video_name_counter):
        capture_parent_dir = os.path.join(self.timelapse_dir, self.name)
        file_output_name = self.name
        output_path = os.path.join(capture_parent_dir, 'output', f"{file_output_name}{video_name_counter}.mp4")

      # List all files in the /tmp directory
        all_files = os.listdir("/tmp")

        # Filter files that match the required pattern
        filtered_files = [f for f in all_files if re.match(r"image_.*_\d+\.jpg", f)]

        # Sort the files by the counter at the end
        sorted_files = sorted(filtered_files, key=lambda x: int(re.search(r"\d+(?=.jpg)", x).group()))

        # Write the sorted file list to a text file
        with open("/tmp/file_list.txt", "w") as f:
            for file in sorted_files:
                f.write(f"file '/tmp/{file}'\n")

        # Use the file list as input for ffmpeg
        (
            ffmpeg
            .input("/tmp/file_list.txt", format="concat", safe=0)
            .filter('deflicker', mode='pm', size=10)
            .filter('scale', size='3840x2160', force_original_aspect_ratio='increase')
            #.drawtext(text="Hi",start_number=0,fontsize="64",escape_text=True, fontcolor="red",x=40,y=100)
            .output('/tmp/current_video.mp4', crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
            .run(overwrite_output=True)
        )

        # Get a list of all previous video files
        video_files = sorted(glob.glob(os.path.join(capture_parent_dir, 'output', f"{file_output_name}*.mp4")))

        # If there is a previous video file, concatenate it with the current video
        if video_files:
            last_video = video_files[-1]

            input1 = ffmpeg.input(last_video)
            input2 = ffmpeg.input('/tmp/current_video.mp4')

            (
                ffmpeg
                .concat(input1, input2, v=1, a=0)
                .output(output_path, crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
                .run(overwrite_output=True)
            )
        else:
            # If there is no previous video file, simply move the current video to the output path
            shutil.copy('/tmp/current_video.mp4', output_path)

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
    


    def mux_download_from_s3(self, file_name, bucket_name):
        # https://github.com/muxinc/mux-python/blob/master/examples/video/exercise-assets.py
        # see this for reference 

        input_settings = [mux_python.InputSettings(url=f'https://{bucket_name}.s3.us-east-2.amazonaws.com/{file_name}.mp4')]
        create_asset_request = mux_python.CreateAssetRequest(input=input_settings)
        create_asset_response = assets_api.create_asset(create_asset_request)
        assert create_asset_response != None
        assert create_asset_response.data.id != None
        logger.info("create-asset OK ✅")

        # Wait for the asset to become ready...
        if create_asset_response.data.status != 'ready':
            logger.info("    waiting for asset to become ready...")
            while True:
                # ========== get-asset ==========
                asset_response = assets_api.get_asset(create_asset_response.data.id)
                assert asset_response != None
                assert asset_response.data.id == create_asset_response.data.id
                if asset_response.data.status != 'ready':
                    #logger.print_debug("Asset still not ready. Status was: " + asset_response.data.status)
                    time.sleep(1)
                else:
                    # ========== get-asset-input-info ==========
                    #logger.print_debug("Asset Ready. Checking input info.")
                    get_asset_input_info_response = assets_api.get_asset_input_info(create_asset_response.data.id)
                    #logger.print_debug("Got Asset Input Info: " + str(get_asset_input_info_response))
                    assert get_asset_input_info_response != None
                    assert get_asset_input_info_response.data != None
                    break
        logger.info("get-asset OK ✅")
        logger.info("get-asset-input-info OK ✅")

        # ========== create-asset-playback-id ==========
        create_playback_id_request = mux_python.CreatePlaybackIDRequest(policy=mux_python.PlaybackPolicy.PUBLIC)
        create_asset_playback_id_response = assets_api.create_asset_playback_id(create_asset_response.data.id, create_playback_id_request)
        #logger.print_debug("Added Playback ID: " + str(create_asset_playback_id_response))
        assert create_asset_playback_id_response != None
        assert create_asset_playback_id_response.data != None
        logger.info(str(create_asset_playback_id_response.data.id))
        logger.info("create-asset-playback-id OK ✅")
        return create_asset_playback_id_response.data.id

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
        video_name_counter = 0
        counter = 0
        images = []

        while True:
            logger.info(f"Polling messages (iteration {counter})...") 
            msg = self.consumer.poll(4.0)

            if msg is None:
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
                asset_playback_id = self.mux_download_from_s3(f"{self.name}{video_name_counter}", self.s3bucket)


                #reset for next timelapse
                self.delete_tmp_contents()
                images = []
                counter = 0
                    
    def run(self):
        self.process_messages()


app = FastAPI()

async def async_run_timelapse_generator(name, timelapse_dir, s3bucket, kafka_bootstrap_servers,threshold):
    timelapse_generator = TimelapseGenerator(name, timelapse_dir, s3bucket, kafka_bootstrap_servers,threshold)
    timelapse_generator.run()
    del timelapse_generator

@app.post("/start_timelapse_generator/")
async def start_timelapse_generator(
    background_tasks: BackgroundTasks,
    name: str = Query(..., description="Name of folder timelapse to be saved in"),
    timelapse_dir: str = Query(..., description="Dir that holds created timelapse & output"),
    s3bucket: str = Query(..., description="Name of the bucket where file will be uploaded and mux will download from"),
    kafka_bootstrap_servers: str = Query(..., description="Kafka bootstrap servers, e.g. broker:9092"),
    threshold: int = Query(..., description="How many photos per timelapse section")
):
    background_tasks.add_task(async_run_timelapse_generator, name, timelapse_dir, s3bucket, kafka_bootstrap_servers, threshold)
    return {"message": "Timelapse generator started"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8020)

