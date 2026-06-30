from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import with_session
from app.services.core import UserService, RatingService, StatisticsService, LessonService

@with_session
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    user_service = UserService(session)
    user = update.effective_user
    await user_service.get_or_create_user(user.id, user.full_name, user.username)
    
    keyboard = [
        [InlineKeyboardButton("📚 Darslar", callback_data="menu_lessons")],
        [InlineKeyboardButton("📊 Statistika", callback_data="menu_stats")],
        [InlineKeyboardButton("🏆 Top 10", callback_data="menu_top")],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"Assalomu alaykum, {user.full_name}! 👋\n\n"
        "Ingliz tili lug'at botiga xush kelibsiz.\n"
        "O'rganishni boshlash uchun quyidagilardan birini tanlang:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

@with_session
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    stats_service = StatisticsService(session)
    user = update.effective_user
    db_user = await UserService(session).get_or_create_user(user.id, user.full_name, user.username)
    
    global_stats = await stats_service.get_user_stats(db_user.id)
    lesson_stats = await stats_service.get_user_lesson_stats(db_user.id)
    
    if not global_stats or global_stats.total_questions == 0:
        text = "Siz hali hech qanday savolga javob bermadingiz. Darslardan birini tanlab boshlang!"
    else:
        text = (
            f"📊 **Umumiy statistika**:\n"
            f"Jami savollar: {global_stats.total_questions}\n"
            f"To'g'ri javoblar: {global_stats.correct_answers}\n"
            f"Noto'g'ri javoblar: {global_stats.wrong_answers}\n"
            f"Aniqlik: {global_stats.accuracy_percent:.1f}%\n\n"
            f"📚 **Darslar bo'yicha statistika**:\n"
        )
        for ls in lesson_stats:
            text += (
                f"\n{ls.lesson_id}-dars\n"
                f"Yechildi: {ls.total_questions} | To'g'ri: {ls.correct_answers} | Noto'g'ri: {ls.wrong_answers}"
            )
            
    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="menu_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
            
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        try:
            await update.callback_query.answer()
        except Exception:
            pass
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

@with_session
async def top_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    rating_service = RatingService(session)
    top_users = await rating_service.get_top_users(10)
    
    text = "🏆 **Global Top 10**\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for idx, (u, s) in enumerate(top_users):
        medal = medals[idx] if idx < 3 else f"{idx+1}."
        name = u.full_name or u.username or f"Foydalanuvchi{u.id}"
        text += f"{medal} {name} - {s.correct_answers} ta to'g'ri\n"
        
    if not top_users:
        text = "Hozircha reyting mavjud emas."
        
    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="menu_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
        
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        try:
            await update.callback_query.answer()
        except Exception:
            pass
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

@with_session
async def lessons_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    lesson_service = LessonService(session)
    lessons = await lesson_service.get_active_lessons()
    
    keyboard = []
    for lesson in lessons:
        keyboard.append([InlineKeyboardButton(f"{lesson.name}", callback_data=f"start_lesson_{lesson.id}")])
        
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="menu_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("O'qimoqchi bo'lgan darsingizni tanlang:", reply_markup=reply_markup)
