from app.repositories.r2.r2_service import s3_client
from app.core.config import settings

def generate_presigned_url(r2_key: str, expiration: int = 3600, filename: str = None) -> str:
    """Generate a presigned URL to share an S3 object."""
    params = {
        'Bucket': settings.r2_bucket_name,
        'Key': r2_key,
    }
    if filename:
        # Force browser to download instead of previewing the file
        params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
    response = s3_client.generate_presigned_url(
        'get_object',
        Params=params,
        ExpiresIn=expiration
    )
    return response

def generate_presigned_put_url(r2_key: str, content_type: str, expiration: int = 3600) -> str:
    """Generate a presigned URL to upload an S3 object."""
    response = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.r2_bucket_name,
            'Key': r2_key,
            'ContentType': content_type
        },
        ExpiresIn=expiration
    )
    return response
