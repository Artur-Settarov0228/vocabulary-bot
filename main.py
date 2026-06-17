from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler
from app.config import settings
from app.handlers.user_handlers import start_handler, stats_handler, top_handler, lessons_menu_handler
from app.handlers.quiz_handlers import start_quiz_handler, poll_answer_handler
from app.handlers.admin_handlers import admin_start, add_lesson_conv, add_word_conv
from app.database.session import engine
from app.database.models import Base

ptb_app = Application.builder().token(settings.BOT_TOKEN).build()

def setup_handlers(app: Application):
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("top", top_handler))
    
    app.add_handler(CallbackQueryHandler(lessons_menu_handler, pattern="^menu_lessons$"))
    app.add_handler(CallbackQueryHandler(stats_handler, pattern="^menu_stats$"))
    app.add_handler(CallbackQueryHandler(top_handler, pattern="^menu_top$"))
    app.add_handler(CallbackQueryHandler(start_quiz_handler, pattern="^start_lesson_"))
    
    app.add_handler(PollAnswerHandler(poll_answer_handler))
    
    # Admin
    app.add_handler(CommandHandler("admin", admin_start))
    app.add_handler(add_lesson_conv)
    app.add_handler(add_word_conv)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    setup_handlers(ptb_app)
    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.bot.set_webhook(url=settings.WEBHOOK_URL)
    yield
    await ptb_app.stop()
    await ptb_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/")
async def process_update(request: Request):
    try:
        update_data = await request.json()
        update = Update.de_json(data=update_data, bot=ptb_app.bot)
        await ptb_app.process_update(update)
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error processing update: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
