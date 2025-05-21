import mimetypes
import hashlib
from io import BytesIO
from typing import Dict, Annotated

from litestar import Controller, post, get
from litestar.response import Response
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from services.base import Services


class S3Controller(Controller):
    path = "/s3"
    tags = ["s3"]

    @post(path="/upload", max_upload_size=50_000_000)
    async def upload_file(
        self,
        services: Services,
        data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> Response[Dict[str, str]]:
        try:
            file_content = await data.read()

            file_hash = hashlib.sha256(file_content).hexdigest()

            content_type = data.content_type
            if not content_type:
                content_type = (
                    mimetypes.guess_type(data.filename)[0] or "application/octet-stream"
                )

            file_extension = mimetypes.guess_extension(content_type) or ""
            unique_filename = f"{file_hash}{file_extension}"

            temp_path = services.s3.upload_temp_file(
                file_obj=BytesIO(file_content),
                filename=unique_filename,
                content_type=content_type,
            )

            return Response(
                content={
                    "original_name": data.filename,
                    "content_type": content_type,
                    "path": temp_path,
                    "size": len(file_content),
                    "hash": file_hash,
                },
                status_code=HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                content={"error": f"Failed to upload file {data.filename}: {str(e)}"},
                status_code=HTTP_400_BAD_REQUEST,
            )

    # @get(path="/file/{file_path:str}")
    # async def get_file(
    #     self,
    #     services: Services,
    #     file_path: str,
    # ) -> Response:
    #     try:
    #         file_content = services.s3.get_file(file_path)
    #         content_type = (
    #             mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    #         )

    #         return Response(
    #             content=file_content,
    #             media_type=content_type,
    #             headers={
    #                 "Content-Disposition": f'attachment; filename="{file_path.split("/")[-1]}"'
    #             },
    #         )
    #     except Exception as e:
    #         return Response(
    #             content={"error": f"Failed to get file {file_path}: {str(e)}"},
    #             status_code=HTTP_404_NOT_FOUND,
    #         )
