import asyncio
import logging
from typing import Optional

import asyncpg

class DatabaseClient:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn
    
    @classmethod
    async def create(cls, database_url: str) -> Optional['DatabaseClient']:
        try:
            conn = await asyncpg.connect(database_url)
            logging.info(f"Connection to database was successfully estabilished")
            return cls(conn)
        except Exception as error:
            logging.error(f"Connection to database wasn't estabilished: {error}") 
    
    async def save_ticket_in_db(self, ticket_name: str, chat_id: int, ticket_id: int, open: bool = True) -> None:
        try:
            await self._conn.execute("""
                INSERT INTO tickets (ticket_name, chat_id, ticket_id, open)
                VALUES ($1, $2, $3, $4)
                """, 
                ticket_name, chat_id, ticket_id, open
            )
            logging.info("Ticket was successfully saved in the database")
        except Exception as error:
            logging.error(f"Failed to save ticket in the database: {error}")

    async def save_message_in_db(self, message: str, chat_id: int, role: str, received_at: str, sent_to_pyrus: bool = False) -> None:
        try: 
            await self._conn.execute("""
                INSERT INTO messages (message, chat_id, role, sent_to_pyrus, received_at)
                VALUES ($1, $2, $3, $4, $5)
                """, 
                message, chat_id, role, sent_to_pyrus, received_at
            )
            logging.info("Message was successfully saved in the database")
        except Exception as error:
            logging.error(f"Failed to save message in the database: {error}")

    async def select_unsend_messages(self, chat_id: int) -> Optional[list['asyncpg.Record']]:
        try:
            result = await self._conn.fetch("""
                SELECT * FROM messages 
                WHERE chat_id = $1 AND sent_to_pyrus = FALSE
                ORDER BY received_at ASC
                """, 
                chat_id
            )
            logging.info(f"Request for messages was successfully executed")
            return result
        except Exception as error:
            logging.error(f"Failed to get unsend messages from the database: {error}")

    async def mark_message_as_sent(self, message_id: int) -> None:
        try:
            await self._conn.execute("""
                UPDATE messages
                SET sent_to_pyrus = TRUE
                WHERE id = $1
                """, 
                message_id
            )
            logging.info(f"Marked message with id {message_id} as sent")
        except Exception as error:
            logging.error(f"Failed to mark message as sent: {error}")

    async def select_open_ticket(self, chat_id: int) -> Optional['asyncpg.Record']:
        try:
            result = await self._conn.fetchrow("""
                SELECT * FROM tickets 
                WHERE chat_id = $1 AND open = TRUE
                """, 
                chat_id
            )
            logging.info(f"Request for ticket was successfully executed")
            return result
        except Exception as error:
            logging.error(f"Failed to get open ticket from the database: {error}")

    async def close_ticket(self, ticket_id: int) -> bool:
        try:
            result = await self._conn.execute("""
                UPDATE tickets
                SET open = FALSE
                WHERE ticket_id = $1
                """,
                ticket_id
            )
            updated_rows = int(result.split()[-1])
            if updated_rows == 0:
                logging.error(f"No ticket with id {ticket_id} found to close")
                return False
            else:
                logging.info(f"Ticket #{ticket_id} closed successfully")
                return True
        except Exception as error:
            logging.error(f"Failed to close ticket #{ticket_id} in the database: {error}")
            return False

    async def create_tickets_table_if_not_exists(self) -> None:
        try:
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    ticket_name TEXT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    ticket_id BIGINT NOT NULL,
                    open BOOLEAN NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()            
                );
            """)
            logging.info("Tickets table check/create successful")
        except Exception as error:
            logging.error(f"Failed to create tickets table: {error}")

    async def create_messages_table_if_not_exists(self) -> None:
        try:
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    message TEXT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('client', 'operator')),
                    sent_to_pyrus BOOLEAN NOT NULL,
                    received_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            logging.info("Messages table check/create successful")
        except Exception as error:
            logging.error(f"Failed to create messages table: {error}")

    async def close(self) -> None:
        await self._conn.close()
        logging.info("Close Database client connection")
