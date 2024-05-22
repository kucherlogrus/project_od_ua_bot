import asyncio
import json
import os

from telegram import Message

class TelegamUserHistory:

    def __init__(self, user_id: int, user_name: str, logs_folder):
        self.user_name = user_name
        self.user_id = user_id
        self._folder = logs_folder
        self._user_history_path = f'{self._folder}/{self.user_name}_{self.user_id}.txt'
        self._storage = self._genStorage()

    @staticmethod
    def get_history(message: Message, logs_folder: str):
        user_id = message.from_user.id
        user_name = message.from_user.username
        return TelegamUserHistory(user_id, user_name, logs_folder)

    def get_storage(self):
        return self._storage

    def _genStorage(self) -> list:
        try:
            with open(self._user_history_path, 'r') as file:
                data = file.read()
                return json.loads(data)
        except FileNotFoundError:
            return []

    def saveHistory(self):
        with open(self._user_history_path, 'w') as user_history_file:
            json.dump(self._storage, user_history_file)

    def add_to_history(self, text: dict, is_bot: bool):
        role = "assistant" if is_bot else "user"
        self._storage.append({"role": role, "content": text})
        self.saveHistory()

    async def clear_history(self):
        self._storage = []
        if await asyncio.to_thread(os.path.exists, self._user_history_path):
            await asyncio.to_thread(os.remove, self._user_history_path)

    async def summary_history(self, text: str):
        await self.clear_history()
        self._storage.append({"role": "system", "content": text})
        self.saveHistory()
