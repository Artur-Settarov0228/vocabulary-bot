from telegram import Update, Poll, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import with_session
from app.services.core import QuizService, UserService
from telegram.error import BadRequest, RetryAfter
import asyncio

async def safe_send_poll(context, **poll_kwargs):
    while True:
        try:
            return await context.bot.send_poll(**poll_kwargs)
        except RetryAfter as e:
            # Telegram kutishni so'rasa, o'sha vaqtcha kutib keyin qayta urinamiz
            await asyncio.sleep(e.retry_after + 1)
        except BadRequest as e:
            if "api_kwargs" in poll_kwargs:
                del poll_kwargs["api_kwargs"]
                # rasmsiz jo'natib ko'ramiz, loop davom etadi
                continue
            raise e

async def safe_send_message(context, **kwargs):
    while True:
        try:
            return await context.bot.send_message(**kwargs)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)

@with_session
async def start_quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass
    
    lesson_id = int(query.data.split("_")[-1])
    user = update.effective_user
    db_user = await UserService(session).get_or_create_user(user.id, user.full_name, user.username)
    
    quiz_service = QuizService(session)
    next_q = await quiz_service.get_next_question(db_user.id, lesson_id)
    
    if not next_q:
        keyboard = [
            [
                InlineKeyboardButton("🔄 Qayta yechish", callback_data=f"restart_lesson_{lesson_id}"),
                InlineKeyboardButton("🔙 Orqaga", callback_data="menu_lessons")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        stats = await quiz_service.stats_service.repo.get_user_lesson_stats(db_user.id, lesson_id)
        
        text = "Tabriklaymiz! 🎉 Siz bu darsdagi barcha savollarni yakunladingiz.\n"
        if stats:
            text += (
                f"\n📊 **Dars natijangiz**:\n"
                f"Jami yechilgan: {stats.total_questions} ta\n"
                f"✅ To'g'ri: {stats.correct_answers} ta\n"
                f"❌ Noto'g'ri: {stats.wrong_answers} ta\n"
            )
        else:
            text += "\n(Bu darsga hali so'zlar qo'shilmagan)"
            
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return
        
    target_word, options, correct_index = next_q
    
    question_text = target_word.question_text if getattr(target_word, "question_text", None) else f"Bu nima? ({target_word.english_word})"
    
    poll_kwargs = {
        "chat_id": user.id,
        "question": question_text,
        "options": options,
        "type": Poll.QUIZ,
        "correct_option_id": correct_index,
        "is_anonymous": False,
        "read_timeout": 60,
        "write_timeout": 60,
        "connect_timeout": 60
    }
    
    if target_word.image_url:
        poll_kwargs["api_kwargs"] = {"media": InputMediaPhoto(media=target_word.image_url)}
        
    poll_message = await safe_send_poll(context, **poll_kwargs)
    
    # Save poll session
    await quiz_service.save_poll_session(
        poll_id=poll_message.poll.id,
        user_id=db_user.id,
        word_id=target_word.id,
        correct_index=correct_index
    )

@with_session
async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    answer = update.poll_answer
    poll_id = answer.poll_id
    user_id = answer.user.id
    selected_option = answer.option_ids[0] if answer.option_ids else -1
    
    db_user = await UserService(session).get_or_create_user(user_id, answer.user.full_name, answer.user.username)
    quiz_service = QuizService(session)
    
    result = await quiz_service.handle_poll_answer(poll_id, db_user.id, selected_option)
    if not result:
        return
        
    is_correct = result["is_correct"]
    word = result["word"]
    lesson_id = result["lesson_id"]
    
    if is_correct:
        text = "✅ To'g'ri!"
    else:
        text = f"❌ Noto'g'ri!\nTo'g'ri javob: {word.uzbek_word}"
        
    if word.description:
        text += f"\nQo'shimcha ma'lumot: {word.description}"
        
    keyboard = [[InlineKeyboardButton("🔙 Darslarga qaytish", callback_data="menu_lessons")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
        
    await safe_send_message(context, chat_id=user_id, text=text, reply_markup=reply_markup)
    
    # Automatically send next question
    next_q = await quiz_service.get_next_question(db_user.id, lesson_id)
    if not next_q:
        keyboard = [
            [
                InlineKeyboardButton("🔄 Qayta yechish", callback_data=f"restart_lesson_{lesson_id}"),
                InlineKeyboardButton("🔙 Orqaga", callback_data="menu_lessons")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        stats = await quiz_service.stats_service.repo.get_user_lesson_stats(db_user.id, lesson_id)
        
        text = "Tabriklaymiz! 🎉 Siz bu darsdagi barcha savollarni yakunladingiz.\n"
        if stats:
            text += (
                f"\n📊 **Dars natijangiz**:\n"
                f"Jami yechilgan: {stats.total_questions} ta\n"
                f"✅ To'g'ri: {stats.correct_answers} ta\n"
                f"❌ Noto'g'ri: {stats.wrong_answers} ta\n"
            )
            
        await safe_send_message(context, chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return
        
    target_word, options, correct_index = next_q
    
    poll_kwargs = {
        "chat_id": user_id,
        "question": target_word.question_text if getattr(target_word, "question_text", None) else f"Bu nima? ({target_word.english_word})",
        "options": options,
        "type": Poll.QUIZ,
        "correct_option_id": correct_index,
        "is_anonymous": False,
        "read_timeout": 60,
        "write_timeout": 60,
        "connect_timeout": 60
    }
    
    if target_word.image_url:
        poll_kwargs["api_kwargs"] = {"media": InputMediaPhoto(media=target_word.image_url)}
        
    poll_message = await safe_send_poll(context, **poll_kwargs)
    
    await quiz_service.save_poll_session(
        poll_id=poll_message.poll.id,
        user_id=db_user.id,
        word_id=target_word.id,
        correct_index=correct_index
    )

@with_session
async def restart_quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass
    
    lesson_id = int(query.data.split("_")[-1])
    user = update.effective_user
    db_user = await UserService(session).get_or_create_user(user.id, user.full_name, user.username)
    
    quiz_service = QuizService(session)
    await quiz_service.repo.delete_user_answers_for_lesson(db_user.id, lesson_id)
    
    next_q = await quiz_service.get_next_question(db_user.id, lesson_id)
    if not next_q:
        await query.message.reply_text("Bu darsda so'zlar topilmadi.")
        return
        
    target_word, options, correct_index = next_q
    
    poll_kwargs = {
        "chat_id": user.id,
        "question": target_word.question_text if getattr(target_word, "question_text", None) else f"Bu nima? ({target_word.english_word})",
        "options": options,
        "type": Poll.QUIZ,
        "correct_option_id": correct_index,
        "is_anonymous": False,
        "read_timeout": 60,
        "write_timeout": 60,
        "connect_timeout": 60
    }
    
    if target_word.image_url:
        poll_kwargs["api_kwargs"] = {"media": InputMediaPhoto(media=target_word.image_url)}
        
    poll_message = await safe_send_poll(context, **poll_kwargs)
    
    await quiz_service.save_poll_session(
        poll_id=poll_message.poll.id,
        user_id=db_user.id,
        word_id=target_word.id,
        correct_index=correct_index
    )
