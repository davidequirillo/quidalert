# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from urllib.parse import urlparse
import boto3
from botocore.config import Config
from core.settings import settings

def get_s3_client():
    s3_config = Config(
        retries={'max_attempts': 3, 'mode': 'standard'},
        connect_timeout=5, 
        read_timeout=60
    )
    minio_url = urlparse(settings.minio_endpoint)
    is_https = (minio_url.scheme == "https")
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        use_ssl=is_https,
        config=s3_config
    )
    return s3_client