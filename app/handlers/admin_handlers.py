from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import with_session
from app.services.core import AdminService
from app.config import settings

ADD_LESSON_NAME, ADD_LESSON_DESC, ADD_LESSON_ORDER = range(3)

def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Sizda bu buyruqdan foydalanish huquqi yo'q.")
        return
    await update.message.reply_text("🛠 **Admin Menyusi:**\n/add_lesson - Yangi dars qo'shish\n/add_word - Darsga so'z qo'shish\n/cancel - Bekor qilish")

async def add_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    await update.message.reply_text("Yangi darsning nomini kiriting (masalan: Hayvonlar):")
    return ADD_LESSON_NAME

async def add_lesson_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['lesson_name'] = update.message.text
    await update.message.reply_text("Dars uchun qisqacha izoh kiriting:")
    return ADD_LESSON_DESC

async def add_lesson_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['lesson_desc'] = update.message.text
    await update.message.reply_text("Darsning tartib raqamini kiriting (faqat butun son, masalan: 1):")
    return ADD_LESSON_ORDER

@with_session
async def add_lesson_order(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    try:
        order_num = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Tartib raqami faqat butun son bo'lishi kerak. Qaytadan urinib ko'ring:")
        return ADD_LESSON_ORDER
        
    admin_service = AdminService(session)
    await admin_service.add_lesson(
        context.user_data['lesson_name'],
        context.user_data['lesson_desc'],
        order_num
    )
    
    await update.message.reply_text("Dars muvaffaqiyatli qo'shildi! 🎉\nEndi unga so'zlar qo'shish uchun /add_word buyrug'idan foydalanishingiz mumkin.")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Jarayon bekor qilindi. ❌")
    context.user_data.clear()
    return ConversationHandler.END

add_lesson_conv = ConversationHandler(
    entry_points=[CommandHandler('add_lesson', add_lesson_start)],
    states={
        ADD_LESSON_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_lesson_name)],
        ADD_LESSON_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_lesson_desc)],
        ADD_LESSON_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_lesson_order)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

ADD_WORD_LESSON_ID, ADD_WORD_ENGLISH, ADD_WORD_UZBEK, ADD_WORD_IMAGE = range(3, 7)

@with_session
async def add_word_start(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
        
    admin_service = AdminService(session)
    lessons = await admin_service.repo.get_active_lessons(limit=100)
    
    if not lessons:
        await update.message.reply_text("Hali hech qanday dars yo'q. Iltimos, avval /add_lesson orqali dars qo'shing.")
        return ConversationHandler.END
        
    text = "Qaysi darsga lug'at qo'shmoqchisiz? \nQuyidagi ro'yxatdan kerakli darsning **ID raqamini** (faqat son) kiriting:\n\n"
    for l in lessons:
        text += f"🆔 **{l.id}** — {l.name}\n"
        
    await update.message.reply_text(text, parse_mode="Markdown")
    return ADD_WORD_LESSON_ID

async def add_word_lesson_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        lesson_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text("ID faqat raqamlardan iborat bo'lishi kerak. Qaytadan urinib ko'ring:")
        return ADD_WORD_LESSON_ID
        
    context.user_data['word_lesson_id'] = lesson_id
    await update.message.reply_text("Iltimos, o'rganilishi kerak bo'lgan **Inglizcha so'zni** yuboring (masalan: Apple):", parse_mode="Markdown")
    return ADD_WORD_ENGLISH

async def add_word_english(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['word_english'] = update.message.text
    await update.message.reply_text("Endi uning **O'zbekcha tarjimasini** yuboring (masalan: Olma):", parse_mode="Markdown")
    return ADD_WORD_UZBEK

async def add_word_uzbek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['word_uzbek'] = update.message.text
    await update.message.reply_text("Ajoyib! Endi ushbu so'zga oid **rasm** yuboring (Telegramdan to'g'ridan-to'g'ri rasm yuboring yoki rasm linkini tashlang):", parse_mode="Markdown")
    return ADD_WORD_IMAGE

@with_session
async def add_word_image(update: Update, context: ContextTypes.DEFAULT_TYPE, session: AsyncSession):
    if update.message.photo:
        image_url = update.message.photo[-1].file_id
    else:
        image_url = update.message.text
        
    admin_service = AdminService(session)
    await admin_service.repo.create_word({
        "lesson_id": context.user_data['word_lesson_id'],
        "english_word": context.user_data['word_english'],
        "uzbek_word": context.user_data['word_uzbek'],
        "image_url": image_url
    })
    
    await update.message.reply_text("So'z muvaffaqiyatli qo'shildi! ✅\nYana so'z qo'shish uchun yana /add_word buyrug'ini bering.")
    context.user_data.clear()
    return ConversationHandler.END

add_word_conv = ConversationHandler(
    entry_points=[CommandHandler('add_word', add_word_start)],
    states={
        ADD_WORD_LESSON_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_word_lesson_id)],
        ADD_WORD_ENGLISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_word_english)],
        ADD_WORD_UZBEK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_word_uzbek)],
        ADD_WORD_IMAGE: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), add_word_image)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
