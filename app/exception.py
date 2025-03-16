class APIError(Exception):
    def __init__(self, message, status_code=500, payload=None):
        self.message = message
        self.status_code = status_code
        self.payload = payload
        super().__init__(self.message)

    def to_dict(self):
        error_dict = dict(self.payload or {})
        error_dict["message"] = self.message
        error_dict["status"] = "error"
        return error_dict


class ValidationError(APIError):
    def __init__(self, message, payload=None):
        super().__init__(message, status_code=400, payload=payload)


class NotFoundError(APIError):
    def __init__(self, message="Resource not found", payload=None):
        super().__init__(message, status_code=404, payload=payload)


class AuthorizationError(APIError):
    def __init__(self, message="Unauthorized", payload=None):
        super().__init__(message, status_code=401, payload=payload)
