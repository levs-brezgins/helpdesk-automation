import logging
from collections import defaultdict
import asyncio

from telethon import TelegramClient, events
from telethon.events import NewMessage

from clients.pyrus_client import PyrusClient
from bot.text_formatter import client_message, operator_message
from database.database_client import DatabaseClient

class HelpdeskBot:
    def __init__(self, telegram_client: TelegramClient, pyrus_client: PyrusClient, database_client: DatabaseClient, code_phrase: str) -> None:
        self._code_phrase = code_phrase
        # Telegram client 
        self._telegram_client = telegram_client 
        # Pyrus client 
        self._pyrus_client = pyrus_client
        # Database client
        self._database_client = database_client
        # locks to avoid races within one chat
        self._locks = defaultdict(asyncio.Lock)

    async def start(self) -> None:
        logging.info("Starting bot...")
        # Add handlers for incoming and outgoing messages
        self._telegram_client.add_event_handler(self.on_incoming, events.NewMessage(incoming=True))
        self._telegram_client.add_event_handler(self.on_outgoing, events.NewMessage(outgoing=True))
        async with self._telegram_client:
            await self._telegram_client.run_until_disconnected()

    async def on_incoming(self, event: NewMessage.Event) -> None:
        # Log incoming message
        logging.info(f"[IN] {event.chat_id}: {event.raw_text}")

        if event.chat_id is None:            
            logging.error(f"Failed to interact with message. Message doesn't have chat_id")
            return 

        async with self._locks[event.chat_id]:
            # 1. Save message to the DB
            await self._database_client.save_message_in_db(event.raw_text, event.chat_id, "client", event.message.date)

            # 2. Find if open ticket exists for this chat
            open_ticket = await self._database_client.select_open_ticket(event.chat_id)
            # 3. If open ticket exists, get ticket_id
            if open_ticket is not None:
                ticket_id = open_ticket['ticket_id']
                # 4. Send all unsend mesages to tickets (including new message/only new message, if there isn't missed messages)
                messages = await self._database_client.select_unsend_messages(event.chat_id)
                if messages: # We know, that there is at least one unsend message, but still
                    for message in messages:
                        # 5. Choose correct role for the message
                        role = client_message(message['message']) if message['role'] == 'client' else operator_message(message['message'])
                        # 6. Sent message to Pyrus
                        add_message = await self._pyrus_client.add_message(ticket_id, role)
                        # 7. Only if message was added to pyrus, we mark it as sent to pyrus in the DB
                        if add_message:
                            # 7. Mark message as sent in DB
                            await self._database_client.mark_message_as_sent(message['id'])
            
            # 9. If open ticket dosn't exist yet, we don't do anything. Just save message in the DB
                

    async def on_outgoing(self, event: NewMessage.Event) -> None:
        # Log outgoing message
        logging.info(f"[OUT] {event.chat_id}: {event.raw_text}")
     
        if event.chat_id is None:            
            logging.error(f"Failed to interact with message. Message doesn't have chat_id")
            return 
        
        async with self._locks[event.chat_id]:
            # 0. If operator writes first, we don't processing this case
            messages = await self._database_client.select_unsend_messages(event.chat_id)
            if messages is None:
                return 
            else:
                has_client_message = any(m['role'] == 'client' for m in messages)
                if not has_client_message:
                    # 0.0 If there isn't unsend client messages, that can mean that operator writes first or ticket is open. We need to check this
                    if not await self._database_client.select_open_ticket(event.chat_id):
                        return

            # 1. Save message to the DB
            await self._database_client.save_message_in_db(event.raw_text, event.chat_id, "operator", event.message.date)
            
            # 2. Get all messages including new message
            messages = await self._database_client.select_unsend_messages(event.chat_id)

            # 3. Find if open ticket exists for this chat
            open_ticket = await self._database_client.select_open_ticket(event.chat_id)
            ticket_id = None
            
            # 4. If open ticket exists, get ticket_id
            if open_ticket is not None:
                ticket_id = open_ticket['ticket_id']
            else:
                # 5. If there isn't open ticket for this chat, create new one
                if messages: # We know, that there is messages, but sill :(
                    # 6. Get client's first message
                    ticket_name = messages[0]['message']
                    # 7. Create new ticket in the Pyrus and get ticket_id
                    ticket_id = await self._pyrus_client.create_ticket(ticket_name)
                    if ticket_id is not None: # Check if Pyrus created ticket succussfully and returned new ticket id 
                        # 8. Save new ticket to the DB
                        await self._database_client.save_ticket_in_db(ticket_name, event.chat_id, ticket_id)
                        # 9. Mark this messages as sent, because Pyrus will use this message as a first comment also
                        await self._database_client.mark_message_as_sent(messages[0]['id'])
                        # 10. Remove this message from unsend messages
                        messages = messages[1:]

            if messages: # We know, that we have at least one message from operator, but still :(
                for message in messages:
                    # 11. Choose correct role for the message
                    role = client_message(message['message']) if message['role'] == 'client' else operator_message(message['message'])
                    # 12. Sent unsend messages to Pyrus 
                    add_message = await self._pyrus_client.add_message(ticket_id, role)
                    if add_message:
                        # 13. Mark them in the DB as sent
                        await self._database_client.mark_message_as_sent(message['id'])
                        # 14. Check if operator wants to close the ticket with a keyword
                        if message['message'] == self._code_phrase:
                            # 15. Close Pyrus ticket
                            await self._pyrus_client.close_ticket(ticket_id)
                            # 16. Close ticket in the DB
                            await self._database_client.close_ticket(ticket_id)
