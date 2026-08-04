import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    's3',
    endpoint_url=os.environ['R2_ENDPOINT'],
    aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
    region_name='auto'
)

bucket_name = os.environ['R2_BUCKET_NAME']

cors_configuration = {
    'CORSRules': [{
        'AllowedHeaders': ['*'],
        'AllowedMethods': ['PUT', 'POST', 'GET', 'HEAD', 'DELETE'],
        'AllowedOrigins': ['*'],
        'ExposeHeaders': ['ETag']
    }]
}

print(f"Setting CORS for bucket: {bucket_name}")
try:
    s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
    print("CORS set successfully!")
except Exception as e:
    print(f"Error: {e}")
