import boto3
import logging
import traceback

logging.getLogger('botocore').setLevel(logging.CRITICAL)

from pathlib import Path
from botocore.config import Config
from botocore.exceptions import ClientError

from config.settings import B2_APPKEY_RW, B2_BUCKET_IMAGES, B2_ENDPOINT, B2_KEYID_RW

# Return a boto3 resource object for B2 service
def get_b2_resource(endpoint, key_id, application_key):
    return boto3.resource(service_name='s3',
                        endpoint_url=endpoint,     # Backblaze endpoint
                        aws_access_key_id=key_id,  # Backblaze keyID
                        aws_secret_access_key=application_key,  # Backblaze applicationKey
                        config=Config(signature_version='s3v4'))

def get_b2_client(endpoint, keyID, applicationKey):
        b2_client = boto3.client(service_name='s3',
                                 endpoint_url=endpoint,                # Backblaze endpoint
                                 aws_access_key_id=keyID,              # Backblaze keyID
                                 aws_secret_access_key=applicationKey) # Backblaze applicationKey
        return b2_client


def get_image_bucket():
    return get_b2_resource(B2_ENDPOINT, B2_KEYID_RW, B2_APPKEY_RW).Bucket(B2_BUCKET_IMAGES)


def upload_image(fileobj, file_name, extra_args=None):
    get_image_bucket().upload_fileobj(
        fileobj,
        file_name,
        ExtraArgs=extra_args
    )


# Upload specified file into the specified bucket
def upload_file(b2, fileobj, bucket, b2_path, extra_args=None):
    b2.Bucket(bucket).upload_fileobj(
        fileobj,
        b2_path,
        ExtraArgs=extra_args
    )

def download_file(b2, bucket, directory, local_name, key_name):
    file_path = directory + '/' + local_name
    try:
        b2.Bucket(bucket).download_file(key_name, file_path)
    except ClientError as ce:
        print('error', ce)


if __name__=='__main__':
    import os
    import environ
    from pathlib import Path
    # Build paths inside the project like this: BASE_DIR / 'subdir'.
    BASE_DIR = Path(__file__).resolve().parent.parent
    # Take environment variables from .env file
    env = environ.Env()
    environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

    # # Possible override of settings to test
    # B2_KEYID_RW=''
    # B2_APPKEY_RW=''
    # B2_ENDPOINT=''
    # B2_BUCKET_IMAGES=''

    b2 = get_b2_resource(B2_ENDPOINT, B2_KEYID_RW, B2_APPKEY_RW)
    c = get_b2_client(B2_ENDPOINT, B2_KEYID_RW, B2_APPKEY_RW)
    
    import IPython
    IPython.embed()


