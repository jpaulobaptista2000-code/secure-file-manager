"""Keep size-limited uploads in RAM instead of plaintext temporary files."""

from io import BytesIO

from flask import Request, current_app
from werkzeug.exceptions import RequestEntityTooLarge


class LimitedMemoryFile(BytesIO):
    def __init__(self, limit):
        super().__init__()
        self.limit = limit

    def write(self, data):
        if self.tell() + len(data) > self.limit:
            raise RequestEntityTooLarge()
        return super().write(data)


class UploadRequest(Request):
    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return LimitedMemoryFile(current_app.config["UPLOAD_MAX_BYTES"])
