from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional

class User(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=120)
    skills: List[str] = Field(default_factory=list)
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6)
    description: Optional[str] = Field("", description="User description")
    interests: List[str] = Field(default_factory=list)
    teaches: List[str] = Field(default_factory=list)
    wantsToLearn: List[str] = Field(default_factory=list)
    photo: Optional[str] = None
    country: str = Field(...)
    city: str = Field(...)
    points: int = Field(0, ge=0)

class Swipe(BaseModel):
    swiper_id: str
    target_id: str
    direction: str  # 'left' or 'right'

class Match(BaseModel):
    user1: str
    user2: str

class Message(BaseModel):
    match_id: str
    sender: str
    message: str

class ForumPost(BaseModel):
    user_id: str
    content: str
    is_anonymous: bool
    tags: List[str]

class TrainingPlan(BaseModel):
    match_id: str
    topic: str
    date: str

