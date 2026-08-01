from app.services.storage.r2_service import s3_client
from app.core.config import settings

def generate_presigned_url(r2_key: str, expiration: int = 3600) -> str:
    """Generate a presigned URL to share an S3 object."""
    response = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.r2_bucket_name,
            'Key': r2_key
        },
        ExpiresIn=expiration
    )
    return response
