from typing import Optional

from pydantic import BaseModel


class ProfileDTO(BaseModel):
    user_id: int  # 如果在业务逻辑中需要用户 ID，请保留
    username: str
    bio: str = ""
    image: Optional[str] = None
    following: bool = False


class ProfileData(BaseModel):
    username: str
    bio: Optional[str] = ""
    image: Optional[str] = None
    following: bool


class ProfileResponse(BaseModel):
    profile: ProfileData

    @classmethod
    def from_profile(cls, profile: ProfileDTO) -> "ProfileResponse":
        return ProfileResponse(
            profile=ProfileData(
                username=profile.username,
                bio=profile.bio,
                image=profile.image,
                following=profile.following,
            )
        )