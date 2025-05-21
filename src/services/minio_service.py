from datetime import datetime, timedelta
from typing import IO, Optional
from uuid import UUID
import mimetypes

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import REPLACE, CopySource

from utils.config import config


class MinioService:
    TEMP_IMAGES_PREFIX: str = "temp/images/"
    TEMP_FILES_PREFIX: str = "temp/files/"
    IMAGES_PREFIX: str = "images/"
    FILES_PREFIX: str = "files/"
    DELETED_PREFIX: str = "deleted/"
    BUCKET: str = "blockscontent"

    def __init__(self):
        self.client = Minio(
            f"minio:{config.minio_port}",
            access_key=config.minio_root_user,
            secret_key=config.minio_root_password,
            secure=False
        )

    def _get_prefix_by_content_type(self, content_type: str, is_temp: bool = False) -> str:
        if content_type.startswith('image/'):
            return self.TEMP_IMAGES_PREFIX if is_temp else self.IMAGES_PREFIX
        return self.TEMP_FILES_PREFIX if is_temp else self.FILES_PREFIX

    def upload_temp_file(self, file_obj: IO, filename: str, content_type: Optional[str] = None) -> str:
        if not content_type:
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        prefix = self._get_prefix_by_content_type(content_type, is_temp=True)
        temp_path = f"{prefix}{filename}"

        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(0)
        
        try:
            self.client.stat_object(self.BUCKET, temp_path)
            return temp_path
        except S3Error:
            self.client.put_object(
                bucket_name=self.BUCKET,
                object_name=temp_path,
                data=file_obj,
                length=file_size,
                content_type=content_type
            )
            return temp_path

    def _move_to_block(self, temp_path: str, block_id: UUID) -> str:
        filename = temp_path.split('/')[-1]
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        prefix = self._get_prefix_by_content_type(content_type)
        
        new_path = f"{prefix}{block_id}/{filename}"
        
        self.client.copy_object(
            self.BUCKET,
            new_path,
            CopySource(self.BUCKET, temp_path)
        )
        
        self.client.remove_object(self.BUCKET, temp_path)
        
        return new_path
    
    def handle_block_file(self, temp_path: Optional[str], block_id: UUID) -> Optional[str]:
        restored_path = self._restore_block_file(block_id)
        if restored_path:
            return restored_path
            
        if temp_path:
            return self._move_to_block(temp_path, block_id)
            
        return None

    def soft_delete(self, file_path: str) -> str:
        deleted_path = f"{self.DELETED_PREFIX}{datetime.now().isoformat()}/{file_path}"
        
        self.client.copy_object(
            self.BUCKET,
            deleted_path,
            CopySource(self.BUCKET, file_path)
        )
        
        self.client.remove_object(self.BUCKET, file_path)
        
        return deleted_path

    def _restore_block_file(self, block_id: UUID) -> Optional[str]:
        deleted_objects = self.client.list_objects(
            self.BUCKET,
            prefix=f"{self.DELETED_PREFIX}",
            recursive=True
        )
        
        latest_file = None
        latest_date = None
        
        for obj in deleted_objects:
            try:
                if str(block_id) in obj.object_name:
                    date_str = obj.object_name.split('/')[1]
                    delete_date = datetime.fromisoformat(date_str)
                    
                    if not latest_date or delete_date > latest_date:
                        latest_file = obj.object_name
                        latest_date = delete_date
            except (IndexError, ValueError):
                continue
        
        if latest_file:
            return self._restore_from_deleted(latest_file, block_id)
        
        return None
    
    def _restore_from_deleted(self, deleted_path: str, block_id: UUID) -> str:
        filename = deleted_path.split('/')[-1]
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        prefix = self._get_prefix_by_content_type(content_type)
        
        restored_path = f"{prefix}{block_id}/{filename}"
        
        self.client.copy_object(
            self.BUCKET,
            restored_path,
            CopySource(self.BUCKET, deleted_path)
        )
        
        self.client.remove_object(self.BUCKET, deleted_path)
        
        return restored_path

    def cleanup_deleted(self, days: int = 30) -> None:
        deadline = datetime.now() - timedelta(days=days)
        
        deleted_objects = self.client.list_objects(
            self.BUCKET,
            prefix=self.DELETED_PREFIX,
            recursive=True
        )
        
        for obj in deleted_objects:
            try:
                date_str = obj.object_name.split('/')[1]
                delete_date = datetime.fromisoformat(date_str)
                
                if delete_date < deadline:
                    self.client.remove_object(self.BUCKET, obj.object_name)
            except (IndexError, ValueError):
                continue

    # def get_file(self, file_path: str) -> bytes:
    #     try:
    #         response = self.client.get_object(self.BUCKET, file_path)
    #         return response.read()
    #     except S3Error as e:
    #         deleted_objects = self.client.list_objects(
    #             self.BUCKET,
    #             prefix=f"{self.DELETED_PREFIX}",
    #             recursive=True
    #         )
    #         for obj in deleted_objects:
    #             if obj.object_name.endswith(file_path):
    #                 response = self.client.get_object(self.BUCKET, obj.object_name)
    #                 return response.read()
    #         raise e
