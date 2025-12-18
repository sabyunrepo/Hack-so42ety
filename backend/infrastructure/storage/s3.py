"""
S3 Storage Service
AWS S3를 사용하는 스토리지 서비스 구현체
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO, Union
import mimetypes
import logging

from .base import AbstractStorageService
from ...core.config import settings

logger = logging.getLogger(__name__)


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
        
        from botocore.config import Config
        
        self.s3_client = boto3.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=f"https://s3.{self.region_name}.amazonaws.com",
            config=Config(signature_version='s3v4')
        )
        
        self.base_url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com"

    def _normalize_key(self, path: str) -> str:
        """
        경로를 S3 키로 정규화

        Local Storage 형식의 경로(/api/v1/files/...)를 S3 경로로 변환
        ✅ HTTP(S) URL도 처리 가능 (중복 presigned URL 방지)

        Args:
            path: 파일 경로
                - 상대 경로: "shared/books/{id}/videos/page_1.mp4"
                - API 경로: "/api/v1/files/shared/books/{id}/videos/page_1.mp4"
                - HTTP URL: "https://bucket.s3.amazonaws.com/shared/books/{id}/videos/page_1.mp4?X-Amz-..."

        Returns:
            str: S3 키 (예: "shared/books/{id}/videos/page_1.mp4")
        """
        # ✅ HTTP(S) URL 감지 및 경로만 추출
        if path.startswith(('http://', 'https://')):
            from urllib.parse import urlparse
            parsed = urlparse(path)
            # Pre-signed URL의 쿼리 파라미터 제거 후 경로만 추출
            path = parsed.path.lstrip('/')
            logger.warning(f"Detected HTTP URL in path, extracted key: {path}")

        key = path.lstrip("/")

        # /api/v1/files/ 접두사 제거 (Local Storage 형식인 경우)
        if key.startswith("api/v1/files/"):
            key = key[len("api/v1/files/"):]

        return key

    async def save(
        self, 
        file_data: Union[bytes, BinaryIO], 
        path: str, 
        content_type: Optional[str] = None
    ) -> str:
        """
        파일 S3 업로드
        
        Returns:
            str: 파일 경로 (Pre-signed URL 아님)
                 예: "shared/books/{id}/audios/page_1.mp3"
        """
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
            
            # ✅ 경로만 반환 (Pre-signed URL 생성하지 않음)
            # API 응답 시 get_url()로 동적 생성
            return key
            
        except ClientError as e:
            logger.error(f"S3 upload failed for {key}: {e}")
            raise e

    async def get(self, path: str) -> bytes:
        """파일 S3 다운로드"""
        key = self._normalize_key(path)
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {path}")
            raise e

    async def delete(self, path: str) -> bool:
        """파일 S3 삭제"""
        key = self._normalize_key(path)
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def exists(self, path: str) -> bool:
        """파일 존재 여부 확인"""
        key = self._normalize_key(path)
        
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def get_url(self, path: str, expires_in: Optional[int] = None, bypass_cdn: bool = False) -> str:
        """
        Pre-signed URL 생성
        
        S3 버킷을 private으로 설정하고 Pre-signed URL로 임시 접근 권한 부여
        
        Args:
            path: 파일 경로 (예: "/api/v1/files/shared/books/{id}/videos/page_1.mp4" 또는 "shared/books/{id}/videos/page_1.mp4")
            expires_in: URL 만료 시간 (초). None이면 settings에서 가져옴
            bypass_cdn: S3에서는 CDN을 사용하지 않으므로 무시됨 (호환성 유지)
        
        Returns:
            str: Pre-signed URL (만료 시간 포함)
        """
        key = self._normalize_key(path)
        
        if expires_in is None:
            expires_in = settings.aws_s3_presigned_url_expiration
        
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            logger.debug(f"Generated pre-signed URL for {key}, expires in {expires_in}s")
            return presigned_url
        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL for {key}: {e}")
            # Fallback: 공개 URL 반환 (버킷이 public일 경우)
            return f"{self.base_url}/{key}"
