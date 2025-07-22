import asyncio
import os
import logging
from dotenv import load_dotenv

from telethon import TelegramClient

from bot.helpdesk_bot import HelpdeskBot
from utils.logger_setup import setup_logger
from clients.pyrus_client import PyrusClient
from database.database_client import DatabaseClient

async def main():
    setup_logger()
    load_dotenv()
    # Code phrase
    CODE_PHRASE = os.getenv('CODE_PHRASE')
    if not CODE_PHRASE:
        raise ValueError("CODE_PHRASE environment variables must be set")

    # Telethon keys 
    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    # Check if API_ID and API_HASH was set for the Telegram client
    if not API_ID or not API_HASH:
        raise ValueError("API_ID and API_HASH environment variables must be set")

    # Pyrus key
    SECURITY_KEY = os.getenv('SECURITY_KEY')
    LOGIN = os.getenv('LOGIN')
    # Check if SECURITY_KEY was set for the Pyrus client 
    if not SECURITY_KEY or not LOGIN:
        raise ValueError("SECURITY_KEY and LOGIN environment variables must be set")

    # Initialize Telegram client and Pyrus client 
    telegram_client = TelegramClient('bot', api_id=int(API_ID), api_hash=API_HASH)
    pyrus_client = PyrusClient(security_key=SECURITY_KEY, login=LOGIN)

    # Database setup
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set")
    
    database_client = await DatabaseClient.create(DATABASE_URL)
    if not database_client:
        return 
    # Initialize Helpdesk bot
    bot = HelpdeskBot(telegram_client, pyrus_client, database_client, CODE_PHRASE)
    try:
        # Create background task for PyrusClient access token auto update 
        asyncio.create_task(pyrus_client.auto_update_access_token())
        # Create or check tables Tickets and Messages in the database
        await database_client.create_tickets_table_if_not_exists()
        await database_client.create_messages_table_if_not_exists()
        # Start bot
        await bot.start()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("Shutdown...")
    finally:
        await pyrus_client.close()
        await database_client.close()

if __name__ == "__main__":
    asyncio.run(main())
