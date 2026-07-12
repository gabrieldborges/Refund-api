from pydantic import BaseModel, EmailStr


class UserLoginValidator(BaseModel):
    email: EmailStr
    password: str
