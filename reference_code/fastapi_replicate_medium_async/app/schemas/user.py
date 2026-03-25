from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# 请求相关模型 ===============================

#DTO改造6  请求UserRegistrationData和DTO用同一个模型
class UserRegistrationDataDTO(BaseModel):
    email: str
    password: str
    username: str

# 单独请求注册数据 需提供DTO转换
class UserRegistrationRequest(BaseModel):
    user: UserRegistrationDataDTO

    def to_dto(self) -> UserRegistrationDataDTO:
        return self.user


# 请求模型
#DTO改造5  请求UserLoginData和DTO用同一个模型
class LoginUserDTO(BaseModel):
    email: str
    password: str

# 单独请求数据 需提供DTO转换
class UserLoginRequest(BaseModel):
    user: LoginUserDTO

    def to_dto(self) -> LoginUserDTO:
        return self.user

#DTO改造4  请求UserUpdateData和DTO用同一个模型
class UserUpdateDataDTO(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    image: Optional[str] = None

# 单独请求 需提供DTO转换
class UserUpdateRequest(BaseModel):
    user: UserUpdateDataDTO

    def to_dto(self) -> UserUpdateDataDTO:
        return self.user


#DTO改造7
class UserUpdateDTO(BaseModel):
    id: int
    username: str
    email: str
    bio: str = ""
    image_url: Optional[str] = None


#DTO改造1

class UserDTO(BaseModel):
    id: int
    username: str
    email: str
    password_hash: str
    bio: str = ""
    image_url: Optional[str] = None
    created_at: datetime


# 通用用户展示字段 ===============================
#DTO改造3  响应UserBaseData和DTO共用一个数据模型  响应LoggedInUserData
class LoggedInUserDTO(BaseModel):
    email: str
    username: str
    bio: str = ""
    image: Optional[str] = None
    token: Optional[str] = None

#DTO改造2  响应RegisteredUserData和DTO用同一个数据模型 CurrentUserData和DTO用同一个数据模型 UpdatedUserData
class CreatedUserDTO(BaseModel):
    id: int
    email: str
    username: str
    bio: str = ""
    image: Optional[str] = None
    token: Optional[str] = None


# 响应相关模型 ===============================


# 单独响应数据 需提供DTO转换
class UserRegistrationResponse(BaseModel):
    user: CreatedUserDTO

    @classmethod
    def from_dto(cls, dto: CreatedUserDTO) -> "UserRegistrationResponse":
        return cls(user=dto)


# 单独响应数据 需提供DTO转换
class UserLoginResponse(BaseModel):
    user: LoggedInUserDTO

    @classmethod
    def from_dto(cls, dto: LoggedInUserDTO) -> "UserLoginResponse":
        return cls(user=dto)


# 单独响应数据 需提供DTO转换
class CurrentUserResponse(BaseModel):
    user: CreatedUserDTO

    @classmethod
    def from_dto(cls, dto: UserDTO, token: str) -> "CurrentUserResponse":
        return cls(
            user=CreatedUserDTO(
                id=dto.id,
                email=dto.email,
                username=dto.username,
                bio=dto.bio,
                image=dto.image_url,
                token=token,
            )
        )

# 单独响应数据 需提供DTO转换
class UpdatedUserResponse(BaseModel):
    user: CreatedUserDTO

    @classmethod
    def from_dto(cls, dto: UserUpdateDTO, token: str) -> "UpdatedUserResponse":
        return cls(
            user=CreatedUserDTO(
                id=dto.id,
                email=dto.email,
                username=dto.username,
                bio=dto.bio,
                image=dto.image_url,
                token=token,
            )
        )

