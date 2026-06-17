from telegram import Update, Poll, InputMediaPhoto
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import with_session
from app.services.core import QuizService, UserService

@with_session
async def start_quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    query = update.callback_query
    await query.answer()
    
    lesson_id = int(query.data.split("_")[-1])
    user = update.effective_user
    db_user = await UserService(session).get_or_create_user(user.id, user.full_name, user.username)
    
    quiz_service = QuizService(session)
    next_q = await quiz_service.get_next_question(db_user.id, lesson_id)
    
    if not next_q:
        await query.message.reply_text("Tabriklaymiz! 🎉 Siz bu darsdagi barcha savollarni yakunladingiz.\n(Yoki bu darsga hali so'zlar qo'shilmagan)")
        return
        
    target_word, options, correct_index = next_q
    
    question_text = f"Bu nima? ({target_word.english_word})"
    
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
        poll_kwargs["api_kwargs"] = {"media": InputMediaPhoto(media=target_word.image_url).to_dict()}
        # Note: Depending on ptb version, sometimes .to_dict() is needed or just passing the object works.
        # But looking at user code they passed the object. Let's pass the dictionary to be 100% safe since api_kwargs takes a dict.
        # Wait, the user specifically commented: "Bot kutubxonasi xato bermasligi uchun json string emas, InputMediaPhoto obyekti uzatamiz".
        # So I will pass the object.
        poll_kwargs["api_kwargs"] = {"media": InputMediaPhoto(media=target_word.image_url)}
        
    poll_message = await context.bot.send_poll(**poll_kwargs)
    
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
        
    await context.bot.send_message(chat_id=user_id, text=text)
    
    # Automatically send next question
    next_q = await quiz_service.get_next_question(db_user.id, lesson_id)
    if not next_q:
        await context.bot.send_message(chat_id=user_id, text="Tabriklaymiz! 🎉 Siz bu darsdagi barcha savollarni yakunladingiz.\n(Yoki bu darsga hali so'zlar qo'shilmagan)")
        return
        
    target_word, options, correct_index = next_q
    
    poll_kwargs = {
        "chat_id": user_id,
        "question": f"Bu nima? ({target_word.english_word})",
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
        
    poll_message = await context.bot.send_poll(**poll_kwargs)
    
    await quiz_service.save_poll_session(
        poll_id=poll_message.poll.id,
        user_id=db_user.id,
        word_id=target_word.id,
        correct_index=correct_index
    )
