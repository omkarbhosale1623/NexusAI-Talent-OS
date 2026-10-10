"""storage.py — S3 / Cloudflare R2 storage service"""
import asyncio
import logging
from typing import Optional
import boto3
from botocore.config import Config
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        kwargs = dict(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4"),
        )
        if settings.R2_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.R2_ENDPOINT_URL
        self._s3 = boto3.client("s3", **kwargs)
        self._bucket = settings.S3_BUCKET

    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._s3.put_object(
            Bucket=self._bucket, Key=key, Body=data,
            ContentType=content_type, ServerSideEncryption="AES256",
        ))
        return key

    async def download(self, key: str) -> bytes:
        loop = asyncio.get_event_loop()
        obj = await loop.run_in_executor(None, lambda: self._s3.get_object(Bucket=self._bucket, Key=key))
        return obj["Body"].read()

    async def presigned_url(self, key: str, expires: int = 3600) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        ))

    async def delete(self, key: str):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._s3.delete_object(Bucket=self._bucket, Key=key))
