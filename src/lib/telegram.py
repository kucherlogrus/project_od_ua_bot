import os
import re
from typing import List, Dict

from telegram.ext import Application, MessageHandler, filters


class TelegramBot:

    def __init__(self, token=None, port=8080, group_id=None):
        if token is None:
            token = os.environ.get("telegram_token", None)
        if token is None:
            raise ValueError("Telegram token is not defined")
        self._token = token
        self._port = port
        self._group_id = group_id
        self._ai_message_handler = None
        self._name_in_message_regexp = re.compile(r'вал.+[ерка|ерчик|ерон|ера]')

    def set_ai_message_handler(self, message_handler):
        self._message_handler = message_handler

    def start_telegram_bot(self):
        application = Application.builder().token(self._token).build()
        application.add_handler(MessageHandler(filters.ALL, self.update_processor))
        application.run_polling()

    async def update_processor(self, update, context):
        if not self._is_message_valid(update.message):
            return
        text = update.message.text.lower()
        messages = [{"role": "user", "content": text}]
        messages = self._gen_messages_from_update(update, messages)
        if len(messages) == 1:
            name_in_message = self._name_in_message_regexp.search(text)
            if name_in_message is None:
                return
            if '?' not in text:
                return
        response_text = await self._message_handler.get_response(messages)
        if response_text is not None:
            await update.message.reply_text(response_text)

    def _gen_messages_from_update(self, update, messages: List[Dict]) -> list:
        bot_check = True
        message = update.message
        while True:
            reply_to_message = message.reply_to_message
            message = reply_to_message
            if reply_to_message is None or not self._is_message_valid(reply_to_message):
                break
            if bot_check:
                if not reply_to_message.from_user.is_bot:
                    break
                messages.append({"role": "assistant", "content": reply_to_message.text})
                bot_check = False
                continue
            role = "assistant" if reply_to_message.from_user.is_bot else "user"
            messages.append({"role": role, "content": reply_to_message.text})
        if len(messages) > 0:
            messages.reverse()
        return messages

    def _is_message_valid(self, message) -> bool:
        if message is None:
            return False
        attrs = ["from_user", "chat", "text"]
        for attr in attrs:
            if not hasattr(message, attr):
                return False
        return True



