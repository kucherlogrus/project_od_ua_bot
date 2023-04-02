import os
import re
from typing import List

from telegram.ext import Application, MessageHandler, filters

class TelegramBot:

    TELEGRAMM_MAX_MESSAGE_LENGTH = 4000

    def __init__(self, token=None, configuration=None):
        if token is None:
            token = os.environ.get("telegram_token", None)
        if token is None:
            raise ValueError("Telegram token is not defined")
        if configuration is None:
            raise ValueError("Configuration is not defined for telegram bot")
        self._config = configuration
        self._token = token
        self._ai_handler = None
        self._groups_blacklist = configuration.black_lists_groups
        self._group_whitelist = configuration.white_lists_groups
        self._check_group_whitelist = True if self._group_whitelist is not None else False
        self._check_group_blacklist = True if self._groups_blacklist is not None and not self._check_group_whitelist else False
        if self._group_whitelist is not None and self._groups_blacklist is not None:
            print("Warning: groups whitelist is defined, and group blacklist is defined. Blacklist will be ignored")
        self._private_blacklist = configuration.black_lists_persons
        self._private_whitelist = configuration.white_lists_persons
        self._check_private_whitelist = True if self._private_whitelist is not None else False
        self._check_private_blacklist = True if self._private_blacklist is not None and not self._check_private_whitelist else False
        if self._private_whitelist is not None and self._private_blacklist is not None:
            print("Warning: persons whitelist is defined, and persons blacklist is defined. Blacklist will be ignored")
        self._chat_trigger_regex = re.compile(configuration.chat_trigger_regex)
        self._image_trigger_regex = re.compile(configuration.image_trigger_regex)
        self._image_change_trigger_regex = re.compile(configuration.image_change_trigger_regex)
        self._init_handle_map()

    def _init_handle_map(self):
        self._group_check = [
            [self._image_trigger_regex, self._image_create_process],
            [self._chat_trigger_regex, self._text_chat_message_process],
        ]

    def set_ai_handler(self, ai_handler):
        self._ai_handler = ai_handler

    def start_telegram_bot(self):
        application = Application.builder().token(self._token).build()
        application.add_handler(MessageHandler(filters.ChatType.GROUP, self.group_handler))
        application.add_handler(MessageHandler(filters.ChatType.SUPERGROUP, self.group_handler))
        application.add_handler(MessageHandler(filters.ChatType.PRIVATE, self.private_handler))
        application.run_polling()

    async def show_info(self, update, context):
        print("Show info")
        message = update.message
        print(message)

    async def group_handler(self, update, context):
        message = update.message
        if not self._is_message_for_handle(message) or self._is_message_from_bot(message):
            return
        check_text = message.text.lower()
        for regex, handler in self._group_check:
            if regex.match(check_text):
                if not self._group_has_access(message) or not self._person_has_access(message):
                    print("Group or person has no access")
                    return await self._send_message(message, "You are not allowed to use this bot. Maybe you are crab or in past life you did something very very bad :)")
                await handler(message, check_text)
                return

    async def private_handler(self, update, context):
        message = update.message
        if not self._is_message_for_handle(message) or self._is_message_from_bot(message):
            return
        if not self._person_has_access(message):
            return await self._send_message(message, "You are not allowed to use this bot. Maybe you are crab or in past life you did something very very bad :)")

        check_text = message.text.lower()

        if self._image_trigger_regex.match(check_text):
            await self._image_create_process(message, check_text)
            return

        await self._text_chat_message_process(message, check_text)

    async def _text_chat_message_process(self, message, check_text):
        data_to_send = []
        reply_to_message = message.reply_to_message
        if reply_to_message is not None:
            reply_message = message.reply_to_message
            if self._is_message_for_handle(reply_message):
                role = "assistant" if self._is_message_from_bot(reply_message) else "user"
                data_to_send.append({"role": role, "content": reply_message.text})
        data_to_send.append({"role": "user", "content": check_text})
        user_id = message.from_user.id
        response_text = await self._ai_handler.get_chat_message_response(data_to_send, user_id)
        if response_text is not None:
            await self._send_message(message, response_text)

    async def _image_create_process(self, message, check_text):
        normalized_text = re.sub(self._image_trigger_regex, "", check_text)
        normalized_text = normalized_text.strip()
        response_text = await self._ai_handler.get_image_create_response(normalized_text)
        if response_text is not None:
            await message.reply_photo(response_text)

    def _image_change_process(self, message):
        pass

    def _is_message_for_handle(self, message) -> bool:
        """Check if message have text, from_user and chat attributes for processing"""
        if message is None:
            return False
        attrs = ["from_user", "chat", "text"]
        for attr in attrs:
            if not hasattr(message, attr):
                return False
        return True

    def _is_message_from_bot(self, message):
        from_user = message.from_user
        if from_user is None:
            return False
        return from_user.is_bot

    def _group_has_access(self, message):
        if self._check_group_whitelist:
            return message.chat.id in self._group_whitelist or message.chat.title in self._group_whitelist
        if self._check_group_blacklist:
            return message.chat.id not in self._groups_blacklist and message.chat.title not in self._groups_blacklist
        return True

    def _person_has_access(self, message) -> bool:
        if self._check_private_whitelist:
            return message.from_user.username in self._private_whitelist or message.from_user.id in self._private_whitelist
        if self._check_private_blacklist:
            return message.from_user.username not in self._private_blacklist and message.from_user.id not in self._private_blacklist
        return True

    async def _send_message(self, message, text: str):
        parts = self._check_message_len(text)
        for text_part in parts:
            await message.reply_text(text_part)

    def _check_message_len(self, message: str) -> List[str]:
        count = len(message)
        messages = []
        if count > self.TELEGRAMM_MAX_MESSAGE_LENGTH:
            while len(message) > self.TELEGRAMM_MAX_MESSAGE_LENGTH:
                part = message[:self.TELEGRAMM_MAX_MESSAGE_LENGTH]
                messages.append(part)
                message = message[self.TELEGRAMM_MAX_MESSAGE_LENGTH:]
            if len(message) > 0:
                messages.append(message)
        else:
            messages.append(message)
        return messages







