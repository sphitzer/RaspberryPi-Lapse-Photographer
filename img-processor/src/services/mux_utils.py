import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import mux_python
from loguru import logger
import os

class MuxUtils:
    def __init__(self, assets_api):
        self.assets_api = assets_api

    def mux_download_from_s3(self, file_path, bucket_name, previous_playback_id, object_name=None):

        if object_name is None:
            object_name = os.path.basename(file_path)

        logger.info(f"file name:{object_name}")

        # Create a session for requests with retries
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Check if the asset with the same file name already exists
        list_assets_response = self.assets_api.list_assets()
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
                        self.assets_api.delete_asset(existing_asset.id)

        create_asset_response = None
        for _ in range(3):
            create_asset_response = self.create_asset_with_retry(object_name, bucket_name)
            if create_asset_response is not None:
                break
            time.sleep(1)

        if create_asset_response is None:
            logger.error("Failed to create asset after retries")
            return None

        playback_id = None
        for _ in range(3):
            playback_id = self.create_playback_id_with_retry(create_asset_response.data.id)
            if playback_id is not None:
                break
            time.sleep(1)

        if playback_id is None:
            logger.error("Failed to create playback ID after retries")
            return None

        return playback_id

    def create_asset_with_retry(self, file_name, bucket_name):
        try:
            input_settings = [mux_python.InputSettings(url=f'https://{bucket_name}.s3.us-east-2.amazonaws.com/{file_name}',name=f'{file_name}')]
            create_asset_request = mux_python.CreateAssetRequest(input=input_settings)
            create_asset_response = self.assets_api.create_asset(create_asset_request)
            assert create_asset_response is not None
            assert create_asset_response.data.id is not None
            logger.info("create-asset OK ✅")
            return create_asset_response
        except Exception as e:
            logger.error(f"Error creating asset: {e}")
            return None

    def create_playback_id_with_retry(self, asset_id):
        try:
            create_playback_id_request = mux_python.CreatePlaybackIDRequest(policy=mux_python.PlaybackPolicy.PUBLIC)
            create_asset_playback_id_response = self.assets_api.create_asset_playback_id(asset_id, create_playback_id_request, _request_timeout=10)
            assert create_asset_playback_id_response is not None
            assert create_asset_playback_id_response.data is not None
            logger.info(str(create_asset_playback_id_response.data.id))
            logger.info("create-asset-playback-id OK ✅")
            return create_asset_playback_id_response.data.id
        except Exception as e:
            logger.error(f"Error creating playback ID: {e}")
            return None
