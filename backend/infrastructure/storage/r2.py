"""
R2 Storage Service (Cloudflare)
Cloudflare R2를 사용하고 CDN Signed URL을 발급하는 스토리지 서비스
"""

import boto3
import hmac
import hashlib
import time
import logging
import mimetypes
from typing import Optional, BinaryIO, Union
from urllib.parse import urlparse, urlencode

from botocore.exceptions import ClientError
from botocore.config import Config

from .base import AbstractStorageService
from ...core.config import settings

logger = logging.getLogger(__name__)


class R2StorageService(AbstractStorageService):
    """
    Cloudflare R2 스토리지 서비스
    
    - 데이터 저장: AWS S3 호환 API 사용 (R2)
    - 데이터 서빙: Cloudflare CDN Signed URL 사용
    """

    def __init__(self):
        self.bucket_name = settings.r2_bucket_name
        self.region_name = settings.r2_region_name
        self.access_key = settings.r2_access_key_id
        self.secret_key = settings.r2_secret_access_key
        self.endpoint_url = settings.r2_endpoint_url
        
        # CDN 설정
        self.cdn_domain = settings.cloudflare_cdn_domain
        self.signing_key = settings.cloudflare_signing_key
        
        if not self.endpoint_url:
            raise ValueError("R2_ENDPOINT_URL is not set")
            
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
            config=Config(signature_version='s3v4')
        )

    def _normalize_key(self, path: str) -> str:
        """
        경로를 스토리지 키로 정규화
        HTTP URL이 들어오면 경로만 추출하고, 내부 API prefix 제거
        """
        if path.startswith(('http://', 'https://')):
            parsed = urlparse(path)
            path = parsed.path.lstrip('/')
            logger.debug(f"Normalized URL to key: {path}")

        key = path.lstrip("/")

        # /api/v1/files/ 접두사 제거
        if key.startswith("api/v1/files/"):
            key = key[len("api/v1/files/"):]
        
        return key

    async def save(
        self, 
        file_data: Union[bytes, BinaryIO], 
        path: str, 
        content_type: Optional[str] = None
    ) -> str:
        """R2에 파일 업로드"""
        key = self._normalize_key(path)
        
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
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    key,
                    ExtraArgs={"ContentType": content_type}
                )
            return key
            
        except ClientError as e:
            logger.error(f"R2 upload failed for {key}: {e}")
            raise e

    async def get(self, path: str) -> bytes:
        """R2에서 파일 다운로드"""
        key = self._normalize_key(path)
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in R2: {path}")
            raise e

    async def delete(self, path: str) -> bool:
        """R2 파일 삭제"""
        key = self._normalize_key(path)
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def exists(self, path: str) -> bool:
        """R2 파일 존재 확인"""
        key = self._normalize_key(path)
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def get_url(
        self,
        path: str,
        expires_in: Optional[int] = None,
        bypass_cdn: bool = False,
        is_shared: bool = True,
        content_type: str = 'default'
    ) -> str:
        """
        Cloudflare CDN URL 생성 (공개/비공개 구분)

        Args:
            path: 파일 경로
            expires_in: 만료 시간 (초)
            bypass_cdn: True면 Backend API(/api/v1/files/...) URL 반환 (On-demand 생성용)
            is_shared: 공개 여부 (True: 공개, False: 비공개)
            content_type: 콘텐츠 타입 ('video', 'audio', 'image', 'metadata', 'default')

        Returns:
            str: URL
        """
        key = self._normalize_key(path)

        # On-demand 생성이 필요한 경우 (예: Word Audio) Backend API URL 반환
        # Client -> Backend -> R2/Generate -> CDN
        if bypass_cdn:
             return f"{settings.storage_base_url}/{key}"

        # CDN 도메인이 설정되지 않았으면 원본 키 반환 (Fail safe)
        if not self.cdn_domain:
            logger.warning("Cloudflare CDN domain not configured, using R2 endpoint")
            return f"{self.endpoint_url}/{self.bucket_name}/{key}"

        base_url = self.cdn_domain.rstrip('/')
        url_path = f"/{key}"

        # 공개 콘텐츠: 토큰 없는 간단한 URL
        if is_shared:
            return f"{base_url}{url_path}"

        # 비공개 콘텐츠: Signed URL 생성
        # 콘텐츠 타입별 만료 시간 설정
        if expires_in is None:
            expiration_times = {
                'video': 21600,      # 6시간 (동화책 하루 사용량 커버)
                'audio': 10800,      # 3시간
                'image': 86400,      # 24시간 (거의 변경 없음)
                'metadata': 3600,    # 1시간
                'default': 3600      # 기본 1시간
            }
            expires_in = expiration_times.get(content_type, 3600)

        # 1. 만료 시간 설정
        expiration = int(time.time() + expires_in)

        # 2. 서명 문자열 생성
        sign_string = f"{url_path}-{expiration}"

        # 3. HMAC-SHA256 서명 생성
        signature = hmac.new(
            self.signing_key.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 4. Signed URL 조합
        params = {
            'verify': expiration,
            'token': signature
        }

        return f"{base_url}{url_path}?{urlencode(params)}"
