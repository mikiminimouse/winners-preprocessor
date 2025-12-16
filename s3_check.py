#!/usr/bin/env python3
import os, time, requests, boto3
from pathlib import Path

# берем из env
endpoint = os.environ["CLOUDRU_S3_ENDPOINT"]
bucket   = os.environ["CLOUDRU_S3_BUCKET"]
region   = os.environ["CLOUDRU_S3_REGION"]
access   = os.environ["CLOUDRU_S3_ACCESS_KEY"]
secret   = os.environ["CLOUDRU_S3_SECRET_KEY"]

img = Path("test_images/page_0002 (1).png")
if not img.exists():
    raise SystemExit(f"File not found: {img}")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access,
    aws_secret_access_key=secret,
    region_name=region,
)

key = f"s3_check/{int(time.time())}_{img.name}"
print("Uploading", img, "->", key)
s3.upload_file(str(img), bucket, key, ExtraArgs={"ContentType": "image/png"})
print("✅ Upload OK")

url = s3.generate_presigned_url(
    ClientMethod="get_object",
    Params={"Bucket": bucket, "Key": key},
    ExpiresIn=3600,
)
print("Presigned URL (1h):", url[:120], "...")

r = requests.head(url, timeout=10, allow_redirects=True)
print("HEAD status:", r.status_code, "Content-Length:", r.headers.get("Content-Length"))