from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.session import async_session
from app.database.models import Lesson, Word
from app.schemas import LessonCreate, LessonResponse, WordCreate, WordResponse
from app.database.repo import Repository

router = APIRouter(prefix="/api/admin", tags=["Admin"])

async def get_db():
    async with async_session() as session:
        async with session.begin():
            yield session

@router.get("/lessons", response_model=List[LessonResponse])
async def get_lessons(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    lessons = await repo.get_active_lessons(skip, limit)
    return lessons

@router.post("/lessons", response_model=LessonResponse)
async def create_lesson(lesson_in: LessonCreate, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    lesson = await repo.create_lesson(lesson_in.model_dump())
    return lesson

@router.get("/lessons/{lesson_id}/words", response_model=List[WordResponse])
async def get_words(lesson_id: int, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    words = await repo.get_words_by_lesson(lesson_id)
    return words

@router.post("/words", response_model=WordResponse)
async def create_word(word_in: WordCreate, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    word = await repo.create_word(word_in.model_dump())
    return word
