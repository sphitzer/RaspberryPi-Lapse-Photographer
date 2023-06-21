import os
from loguru import logger
import boto3
from botocore.exceptions import NoCredentialsError

class S3Utils:
    def __init__(self, s3bucket):
        self.s3bucket = s3bucket

    def upload_to_s3(self, file_path, object_name=None):
        logger.info("Starting s3 upload")
        if object_name is None:
            object_name = os.path.basename(file_path)

        s3_client = boto3.client('s3')
        try:
            response = s3_client.upload_file(file_path, self.s3bucket, object_name)
        except NoCredentialsError as e:
            logger.error(e)
            logger.info("Failed s3 upload")
            return False

        logger.info("Completed s3 upload")
        return True

