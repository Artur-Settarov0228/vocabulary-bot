from pydantic import BaseModel
from typing import Optional

class LessonCreate(BaseModel):
    name: str
    description: str
    order_number: int
    is_active: bool = True

class LessonResponse(LessonCreate):
    id: int

    class Config:
        from_attributes = True

class WordCreate(BaseModel):
    lesson_id: int
    english_word: str
    uzbek_word: str
    question_text: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[str] = None

class WordResponse(WordCreate):
    id: int

    class Config:
        from_attributes = True
