"""
S3 Storage Service
AWS S3를 사용하는 스토리지 서비스 구현체
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO, Union
import mimetypes

from .base import AbstractStorageService
from ...core.config import settings


class S3StorageService(AbstractStorageService):
    """
    AWS S3 스토리지 서비스
    """

    def __init__(self):
        """
        AWS 자격 증명은 환경 변수 또는 settings에서 로드
        """
        self.bucket_name = settings.aws_s3_bucket_name
        self.region_name = settings.aws_s3_region
        self.access_key = settings.aws_access_key_id
        self.secret_key = settings.aws_secret_access_key
        
        self.s3_client = boto3.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        
        self.base_url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com"

    async def save(
        self, 
        file_data: Union[bytes, BinaryIO], 
        path: str, 
        content_type: Optional[str] = None
    ) -> str:
        """파일 S3 업로드"""
        # path 앞의 슬래시 제거
        key = path.lstrip("/")
        
        # Content-Type 추론
        if not content_type:
            content_type, _ = mimetypes.guess_type(path)
            if not content_type:
                content_type = "application/octet-stream"
        
        try:
            if isinstance(file_data, bytes):
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_data,
                    ContentType=content_type
                )
            else:
                # file-like object
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    key,
                    ExtraArgs={"ContentType": content_type}
                )
                
            return self.get_url(key)
            
        except ClientError as e:
            # TODO: 로깅 추가
            raise e

    async def get(self, path: str) -> bytes:
        """파일 S3 다운로드"""
        key = path.lstrip("/")
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {path}")
            raise e

    async def delete(self, path: str) -> bool:
        """파일 S3 삭제"""
        key = path.lstrip("/")
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def exists(self, path: str) -> bool:
        """파일 존재 여부 확인"""
        key = path.lstrip("/")
        
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def get_url(self, path: str) -> str:
        """파일 접근 URL 반환"""
        key = path.lstrip("/")
        return f"{self.base_url}/{key}"
