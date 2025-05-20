from litestar import Controller, post
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST

from services.base import Services


class MigrationController(Controller):
    path = "/migrations"
    tags = ["migrations"]

    @post(path="/up")
    async def up_migrations(self, services: Services) -> Response:
        try:
            services.migration.up()
            return Response(
                content={"status": "OK"},
                status_code=HTTP_200_OK
            )
        except Exception as e:
            return Response(
                content={"error": str(e)},
                status_code=HTTP_400_BAD_REQUEST
            )

    @post(path="/down")
    async def down_migrations(self, services: Services) -> Response:
        try:
            services.migration.down_to_base()
            return Response(
                content={"status": "OK"},
                status_code=HTTP_200_OK
            )
        except Exception as e:
            return Response(
                content={"error": str(e)},
                status_code=HTTP_400_BAD_REQUEST
            )
