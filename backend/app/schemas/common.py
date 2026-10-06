from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"
