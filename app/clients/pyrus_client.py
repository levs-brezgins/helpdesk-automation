import httpx
import asyncio
import logging

class PyrusClient:
    PYRUS_URL: str = "https://accounts.pyrus.com/api/v4/"

    def __init__(self, security_key: str, login: str) -> None:
        self._security_key = security_key
        self._login = login 
        self._access_token = None
        self._api_url = None
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def access_token(self) -> str | None:
        return self._access_token

    async def auth(self) -> bool:
        payload = { 
            "login": self._login,
            "security_key": self._security_key
        }
        
        response = await self._post('auth', payload)
        if response:    
            data = response.json()
            self._access_token = data['access_token']
            logging.info("Pyrus access token was successfully created and set")
            if not self._api_url:
                self._api_url = data['api_url']
                logging.info("Api url was successfully created and set")
            return True 
        else:
            logging.error("Error ocured for pyrus access token generation")
            return False 

    async def create_ticket(self, ticket_name: str) -> int | None:
        # Return ticket_id if ticket was successfully created, and None if an error occurred
        payload = {
            "text": f"{ticket_name}"
        }
        
        headers = self.__get_headers()
        response = await self._post('tasks', payload, headers)
        if response:
            ticket_id = response.json()['task']['id']
            logging.info(f"Ticket #{ticket_id} was successfully created")
            return ticket_id
        else:
            logging.error(f"Failed to create ticket")
            return None

    async def add_message(self, ticket_id: int, message: str) -> bool:
        # Return True if the message for the ticket was added successfully and False if an error occurred
        payload = {"text": f"{message}"}
        headers = self.__get_headers()
        response = await self._post(f"tasks/{ticket_id}/comments", payload, headers)
        if response:
            logging.info(f"Message for ticket #{ticket_id} was successfully added")
            return True
        else:
            logging.error(f"Failed to add message to ticket #{ticket_id}")
            return False

    async def close_ticket(self, ticket_id: int) -> bool:
        # Return True if the ticket was closed successfully, False if an error occurred
        payload = {
            "text": "Проблема решена",
            "action": "finished"
        }

        headers = self.__get_headers()
        response = await self._post(f"tasks/{ticket_id}/comments", payload, headers)
        if response:
            logging.info(f"Ticket #{ticket_id} was successfully closed")
            return True
        else:
            logging.error(f"Failed to close ticket #{ticket_id}")
            return False
    
    # Close AsyncClient connection
    async def close(self) -> None: 
        await self._client.aclose()
        logging.info("Close Pyrus client connection")

    # Access token auto update
    async def auto_update_access_token(self, interval_sec: int = 3600) -> None:
        while True:
            auth = await self.auth()
            if auth:
                logging.info("Background task 'auto_update_access_token' successfully executed")
            else:
                logging.error("Background task 'auto_update_access_token' executed with error")
            await asyncio.sleep(interval_sec) # 1 hour by default
            
    #------------------------------------------------------Private methods------------------------------------------------------
    async def _post(self, endpoint: str, payload: dict, headers: dict | None = None) -> httpx.Response | None:
        # Return response itself on success or None on failure
        url = f"{self._api_url}{endpoint}" if self._api_url else f"{self.PYRUS_URL}{endpoint}"
        try:
            response = await self._client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response
            else:
                logging.error(f"Request to {url} failed with status code {response.status_code}. Description: {response.text}")
        except Exception as error:
            logging.error(f"Request to {url} failed with error: {error}")
        return None 

    def __get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
