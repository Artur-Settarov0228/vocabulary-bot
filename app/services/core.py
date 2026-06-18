import random
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repo import Repository
from app.database.models import User, Lesson, Word

class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = Repository(session)

    async def get_or_create_user(self, telegram_id: int, full_name: str, username: Optional[str]) -> User:
        user = await self.repo.get_user_by_telegram_id(telegram_id)
        if not user:
            user = await self.repo.create_user({"telegram_id": telegram_id, "full_name": full_name, "username": username})
        else:
            update_data = {}
            if user.username != username: update_data["username"] = username
            if user.full_name != full_name: update_data["full_name"] = full_name
            if update_data: user = await self.repo.update_user(user, update_data)
        return user

class LessonService:
    def __init__(self, session: AsyncSession):
        self.repo = Repository(session)

    async def get_active_lessons(self, skip: int=0, limit: int=10) -> List[Lesson]:
        return list(await self.repo.get_active_lessons(skip, limit))

    async def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        return await self.repo.get_lesson(lesson_id)

class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.repo = Repository(session)

    async def record_answer(self, user_id: int, lesson_id: int, is_correct: bool):
        stats = await self.repo.get_user_stats(user_id)
        if not stats:
            stats = await self.repo.create_user_stats({"user_id": user_id, "total_questions": 0, "correct_answers": 0, "wrong_answers": 0, "accuracy_percent": 0.0})
        stats.total_questions += 1
        if is_correct: stats.correct_answers += 1
        else: stats.wrong_answers += 1
        if stats.total_questions > 0: stats.accuracy_percent = (stats.correct_answers / stats.total_questions) * 100
        await self.repo.update_user_stats(stats)

        lesson_stats = await self.repo.get_user_lesson_stats(user_id, lesson_id)
        if not lesson_stats:
            lesson_stats = await self.repo.create_user_lesson_stats({"user_id": user_id, "lesson_id": lesson_id, "total_questions": 0, "correct_answers": 0, "wrong_answers": 0})
        lesson_stats.total_questions += 1
        if is_correct: lesson_stats.correct_answers += 1
        else: lesson_stats.wrong_answers += 1
        await self.repo.update_user_lesson_stats(lesson_stats)

    async def get_user_stats(self, user_id: int):
        return await self.repo.get_user_stats(user_id)
        
    async def get_user_lesson_stats(self, user_id: int):
        return await self.repo.get_all_lesson_stats(user_id)

class QuizService:
    def __init__(self, session: AsyncSession):
        self.repo = Repository(session)
        self.stats_service = StatisticsService(session)

    async def get_next_question(self, user_id: int, lesson_id: int) -> Optional[Tuple[Word, List[str], int]]:
        all_words = list(await self.repo.get_words_by_lesson(lesson_id))
        if not all_words: return None
        answered_word_ids = set(await self.repo.get_answered_word_ids(user_id, lesson_id))
        unanswered_words = [w for w in all_words if w.id not in answered_word_ids]
        if not unanswered_words: return None

        target_word = random.choice(unanswered_words)
        wrong_options = []
        if getattr(target_word, "variants", None):
            custom_variants = [v.strip() for v in target_word.variants.split(",") if v.strip()]
            wrong_options.extend(custom_variants[:3])

        if len(wrong_options) < 3:
            other_words = [w for w in all_words if w.id != target_word.id]
            wrong_options.extend([w.uzbek_word for w in other_words if w.uzbek_word not in wrong_options])
        
        if len(wrong_options) < 3:
            from sqlalchemy import select
            extra_res = await self.repo.session.execute(select(Word).filter(Word.id != target_word.id))
            all_extra = [w.uzbek_word for w in extra_res.scalars().all() if w.uzbek_word not in wrong_options]
            
            random.shuffle(all_extra)
            wrong_options.extend(all_extra[:3 - len(wrong_options)])
            
            fallbacks = [
                "Mashina 🚗", "Kitob 📚", "Qalam ✏️", "Daraxt 🌳", 
                "Telefon 📱", "Suv 💧", "Quyosh ☀️", "Oila 👨‍👩‍👦", "Uy 🏠"
            ]
            for f in fallbacks:
                if len(wrong_options) >= 3: break
                if f not in wrong_options and f != target_word.uzbek_word:
                    wrong_options.append(f)
        else:
            if len(wrong_options) > 3:
                wrong_options = random.sample(wrong_options, 3)
            
        options = [target_word.uzbek_word] + wrong_options
        random.shuffle(options)
        correct_index = options.index(target_word.uzbek_word)
        return target_word, options, correct_index

    async def save_poll_session(self, poll_id: str, user_id: int, word_id: int, correct_index: int):
        await self.repo.create_poll_session({"poll_id": poll_id, "user_id": user_id, "word_id": word_id, "correct_option_index": correct_index})

    async def handle_poll_answer(self, poll_id: str, user_id: int, selected_option_index: int):
        poll_session = await self.repo.get_poll_session(poll_id)
        if not poll_session: return None
        is_correct = (selected_option_index == poll_session.correct_option_index)
        
        word = await self.repo.get_word(poll_session.word_id)
        if not word: return None
            
        await self.repo.create_user_answer({"user_id": user_id, "word_id": poll_session.word_id, "selected_answer": str(selected_option_index), "is_correct": is_correct})
        await self.stats_service.record_answer(user_id, word.lesson_id, is_correct)
        
        return {"is_correct": is_correct, "word": word, "lesson_id": word.lesson_id}

class RatingService:
    def __init__(self, session: AsyncSession):
        self.repo = Repository(session)

    async def get_top_users(self, limit: int = 10):
        return await self.repo.get_top_users(limit)

class AdminService:
    def __init__(self, session: AsyncSession):
        self.repo = Repository(session)

    async def add_lesson(self, name: str, description: str, order_number: int) -> Lesson:
        return await self.repo.create_lesson({"name": name, "description": description, "order_number": order_number, "is_active": True})
