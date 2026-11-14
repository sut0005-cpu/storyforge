"""S3-compatible Hugging Face Storage Bucket client.

Preferred setup: configure the AWS CLI profile named `hf` locally, then this
module uses that profile. Alternatively set HF_S3_ACCESS_KEY_ID and
HF_S3_SECRET_ACCESS_KEY in the environment. Never bundle credentials in an EXE.
"""
import os
import boto3
from botocore.config import Config

ENDPOINT_URL = os.getenv("HF_S3_ENDPOINT_URL", "https://s3.hf.co/gygax0312")
DEFAULT_BUCKET = os.getenv("HF_S3_BUCKET", "storyforge")


def create_storage_client():
    config = Config(
        region_name="us-east-1",
        s3={"addressing_style": "path"},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )
    access_key = os.getenv("HFAKD2oKRbOGavKkUYcQtS71CE8LgSC") or os.getenv("HFAKD2oKRbOGavKkUYcQtS71CE8LgSC")
    secret_key = os.getenv("30331d6654139470b2bc926b7c8f4f0dc22d5833a5590b50131c31986c4736fa") or os.getenv("30331d6654139470b2bc926b7c8f4f0dc22d5833a5590b50131c31986c4736fa")
    if access_key and secret_key:
        return boto3.client(
            "s3", endpoint_url=ENDPOINT_URL,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=config,
        )
    # Uses credentials saved by `aws configure --profile hf`.
    session = boto3.Session(profile_name=os.getenv("HF_AWS_PROFILE", "hf"))
    credentials = session.get_credentials()
    if credentials is None:
        raise RuntimeError(
            "    return session.client("s3", endpoint_url=ENDPOINT_URL, config=config)


def list_project_files(bucket=DEFAULT_BUCKET, prefix=""):
    client = create_storage_client()
    paginator = client.get_paginator("list_objects_v2")
    return [obj["Key"] for page in paginator.paginate(Bucket=bucket, Prefix=prefix)
            for obj in page.get("Contents", [])]


def upload_project_file(local_path, object_key, bucket=DEFAULT_BUCKET):
    create_storage_client().upload_file(os.fspath(local_path), bucket, object_key)


def download_project_file(object_key, local_path, bucket=DEFAULT_BUCKET):
    target = os.fspath(local_path)
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    create_storage_client().download_file(bucket, object_key, target)
