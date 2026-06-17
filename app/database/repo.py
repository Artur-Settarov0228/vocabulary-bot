from typing import Sequence, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.database.models import User, Lesson, Word, UserAnswer, UserStats, UserLessonStats, PollSession

class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Users
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).filter(User.telegram_id == telegram_id))
        return result.scalars().first()

    async def create_user(self, data: dict) -> User:
        user = User(**data)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_user(self, user: User, data: dict) -> User:
        for k, v in data.items():
            setattr(user, k, v)
        self.session.add(user)
        await self.session.flush()
        return user

    # Lessons
    async def get_active_lessons(self, skip: int = 0, limit: int = 10) -> Sequence[Lesson]:
        result = await self.session.execute(
            select(Lesson).filter(Lesson.is_active == True).order_by(Lesson.order_number.asc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        result = await self.session.execute(select(Lesson).filter(Lesson.id == lesson_id))
        return result.scalars().first()
        
    async def create_lesson(self, data: dict) -> Lesson:
        lesson = Lesson(**data)
        self.session.add(lesson)
        await self.session.flush()
        return lesson

    # Words
    async def get_words_by_lesson(self, lesson_id: int) -> Sequence[Word]:
        result = await self.session.execute(select(Word).filter(Word.lesson_id == lesson_id))
        return result.scalars().all()

    async def get_word(self, word_id: int) -> Optional[Word]:
        result = await self.session.execute(select(Word).filter(Word.id == word_id))
        return result.scalars().first()

    async def create_word(self, data: dict) -> Word:
        word = Word(**data)
        self.session.add(word)
        await self.session.flush()
        return word

    # Answers & Polls
    async def get_answered_word_ids(self, user_id: int, lesson_id: int) -> Sequence[int]:
        result = await self.session.execute(
            select(UserAnswer.word_id)
            .join(Word, Word.id == UserAnswer.word_id)
            .filter(UserAnswer.user_id == user_id, Word.lesson_id == lesson_id)
        )
        return result.scalars().all()

    async def get_poll_session(self, poll_id: str) -> Optional[PollSession]:
        result = await self.session.execute(select(PollSession).filter(PollSession.poll_id == poll_id))
        return result.scalars().first()

    async def create_poll_session(self, data: dict) -> PollSession:
        poll = PollSession(**data)
        self.session.add(poll)
        await self.session.flush()
        return poll

    async def create_user_answer(self, data: dict) -> UserAnswer:
        ans = UserAnswer(**data)
        self.session.add(ans)
        await self.session.flush()
        return ans

    # Stats
    async def get_user_stats(self, user_id: int) -> Optional[UserStats]:
        result = await self.session.execute(select(UserStats).filter(UserStats.user_id == user_id))
        return result.scalars().first()

    async def create_user_stats(self, data: dict) -> UserStats:
        stats = UserStats(**data)
        self.session.add(stats)
        await self.session.flush()
        return stats
        
    async def update_user_stats(self, stats: UserStats):
        self.session.add(stats)
        await self.session.flush()

    async def get_user_lesson_stats(self, user_id: int, lesson_id: int) -> Optional[UserLessonStats]:
        result = await self.session.execute(
            select(UserLessonStats).filter(UserLessonStats.user_id == user_id, UserLessonStats.lesson_id == lesson_id)
        )
        return result.scalars().first()
        
    async def get_all_lesson_stats(self, user_id: int) -> Sequence[UserLessonStats]:
        result = await self.session.execute(
            select(UserLessonStats).filter(UserLessonStats.user_id == user_id)
        )
        return result.scalars().all()

    async def create_user_lesson_stats(self, data: dict) -> UserLessonStats:
        stats = UserLessonStats(**data)
        self.session.add(stats)
        await self.session.flush()
        return stats

    async def update_user_lesson_stats(self, stats: UserLessonStats):
        self.session.add(stats)
        await self.session.flush()

    # Rating
    async def get_top_users(self, limit: int = 10) -> Sequence[Any]:
        result = await self.session.execute(
            select(User, UserStats)
            .join(UserStats, User.id == UserStats.user_id)
            .order_by(UserStats.correct_answers.desc())
            .limit(limit)
        )
        return result.all()
