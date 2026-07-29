from src.controllers.interfaces.avatar_uploader_controller_interface import (
    AvatarUploaderControllerInterface,
)
from src.validators.avatar_upload_validator import avatar_upload_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class AvatarUploaderView:
    def __init__(self, controller: AvatarUploaderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            avatar_upload_validator(http_request)

            response = await self.__controller.upload(
                user_id=http_request.token_info["user_id"],
                original_filename=http_request.body["filename"],
                content=http_request.body["content"],
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
