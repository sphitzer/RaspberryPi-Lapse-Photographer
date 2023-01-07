import sys, os, time 
import argparse

#replace w/ preferred logging tool 
import logging
import logger

import ffmpeg
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import requests
import mux_python

# load environment variables
load_dotenv()

#mux auth setup
configuration = mux_python.Configuration()
configuration.username = os.environ['MUX_ACCESSS_TOKEN_ID']
configuration.password = os.environ['MUX_SECRET_KEY']

# Mux API Client Initialization
assets_api = mux_python.AssetsApi(mux_python.ApiClient(configuration))
playback_ids_api = mux_python.PlaybackIDApi(mux_python.ApiClient(configuration))



def generate_video_from_photos(capture_parent_dir, file_output_name):

    (
        ffmpeg
        .input(capture_parent_dir + '/capture/*.jpg', pattern_type='glob', framerate=60)
        .filter('deflicker', mode='pm', size=10)
        .filter('scale', size='3840x2160', force_original_aspect_ratio='increase')
        .output(capture_parent_dir + '/output/' + file_output_name + '.mp4', crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
        #.view(filename='filter_graph')
        .run()
    )

    return capture_parent_dir + '/output/' + file_output_name + '.mp4'


def upload_to_s3(file_path, bucket, object_name=None):

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_path, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

#mux takes the file uploaded to s3 and processes it for streaming
#function returns 
def mux_download_from_s3(bucket_name, file_name):
    # https://github.com/muxinc/mux-python/blob/master/examples/video/exercise-assets.py
    # see this for reference 

    input_settings = [mux_python.InputSettings(url=f'https://{bucket_name}.s3.us-east-2.amazonaws.com/{file_name}')]
    create_asset_request = mux_python.CreateAssetRequest(input=input_settings)
    create_asset_response = assets_api.create_asset(create_asset_request)
    assert create_asset_response != None
    assert create_asset_response.data.id != None
    print("create-asset OK ✅")

    # Wait for the asset to become ready...
    if create_asset_response.data.status != 'ready':
        print("    waiting for asset to become ready...")
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
    print("get-asset OK ✅")
    print("get-asset-input-info OK ✅")

    # ========== create-asset-playback-id ==========
    create_playback_id_request = mux_python.CreatePlaybackIDRequest(policy=mux_python.PlaybackPolicy.PUBLIC)
    create_asset_playback_id_response = assets_api.create_asset_playback_id(create_asset_response.data.id, create_playback_id_request)
    #logger.print_debug("Added Playback ID: " + str(create_asset_playback_id_response))
    assert create_asset_playback_id_response != None
    assert create_asset_playback_id_response.data != None
    print("create-asset-playback-id OK ✅")
    return create_asset_playback_id_response['data']['id']


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timelapse via picamera or gphoto2')

    #parser.add_argument('--name', required=True, type=str, dest='name', help='name of folder timelapse to be saved in')
    #parser.add_argument('--timelapsedir', required=True, type=str, dest='timelapse_dir', help='dir that holds created timelapse & output')
 
    #args = parser.parse_args()
    #print(args)
    args = {"name": "deskmovie3.mp4", "dir": "../../remote-test2/output/", "s3bucket": "timelapseuploadsfortwentyfivecents2"}

    #display_image()
    #livestream()
    #edge_detection()

    #generate_video_from_photos
    
    # upload to s3
    #file_path = args.dir + args.name
    #upload_to_s3(file_path, args.s3bucket)

    # have mux grab video & encode for streaming 
    asset_playback_id = mux_download_from_s3(args['s3bucket'], args['name'])

    # delete file from bucket once uploaded??? 