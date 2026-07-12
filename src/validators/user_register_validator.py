from pydantic import BaseModel, EmailStr, Field


class UserRegisterValidator(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)
