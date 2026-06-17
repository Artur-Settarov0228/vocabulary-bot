from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from app.database.session import async_session

def with_session(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        async with async_session() as session:
            async with session.begin():
                kwargs['session'] = session
                return await func(update, context, *args, **kwargs)
    return wrapper
