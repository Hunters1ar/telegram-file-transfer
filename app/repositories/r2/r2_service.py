import boto3
from botocore.config import Config
from app.core.config import settings
from fastapi.concurrency import run_in_threadpool

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

s3_client = get_s3_client()

async def empty_r2_bucket():
    def _empty():
        bucket = settings.r2_bucket_name
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket)
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
    await run_in_threadpool(_empty)

async def delete_file_from_r2(r2_key: str):
    def _delete():
        s3_client.delete_object(Bucket=settings.r2_bucket_name, Key=r2_key)
    await run_in_threadpool(_delete)
