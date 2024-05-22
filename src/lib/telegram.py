import asyncio
import os
import re
from io import BytesIO
from typing import List
from PIL import Image


from pydub import AudioSegment
from telegram import Message
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from telegram.constants import ChatType

from .telegram_history import TelegamUserHistory


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
        self._logs_dir = configuration.logs_dir
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
        self._image_vision_trigger_regex = re.compile(configuration.image_vision_trigger_regex)
        self._triggers_check = [
            [self._image_trigger_regex, self._image_create_process],
            [self._chat_trigger_regex, self._text_group_chat_message_process],
        ]

        self._images_triggers = [
            [self._image_vision_trigger_regex, self._image_vision_process],
            [self._image_change_trigger_regex, self._image_change_process],
            [self._image_trigger_regex, self._image_create_process],
        ]

        self._private_chats_gistory = {}

    def set_ai_handler(self, ai_handler):
        self._ai_handler = ai_handler

    def start_telegram_bot(self):
        application = Application.builder().token(self._token).build()
        application.add_handler(CommandHandler('reset', self.reset_private_history, filters=filters.ChatType.PRIVATE))
        application.add_handler(CommandHandler('summ', self.summary_private_history, filters=filters.ChatType.PRIVATE))
        application.add_handler(CommandHandler('help', self.help_private_chat, filters=filters.ChatType.PRIVATE))
        application.add_handler(CommandHandler('info', self.info_private_chat, filters=filters.ChatType.PRIVATE))
        application.add_handler(CommandHandler('image', self._image_create_process_from_cmd, filters=filters.ChatType.PRIVATE | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP))
        application.add_handler(MessageHandler(filters.ChatType.GROUP, self.group_messages_handler))
        application.add_handler(MessageHandler(filters.ChatType.SUPERGROUP, self.group_messages_handler))
        application.add_handler(MessageHandler(filters.ChatType.PRIVATE, self.private_chat_handler))
        application.run_polling()

    async def reset_private_history(self, update, context):
        message = update.message
        private_chat = message.chat.type == ChatType.PRIVATE
        if not private_chat:
            return
        user_history = TelegamUserHistory.get_history(message, self._logs_dir)
        await user_history.clear_history()
        await self._send_message(message, "Диалог сброшен.")

    async def help_private_chat(self, update, context):
        help_text = "Поддерживаемые команды:\n" + \
             "/help - Показать это сообщение.\n" + \
             "/info - Показать информацию о количестве сообщений в контексте диалога и текущее количество токенов.\n" + \
             "/summ - Обобщить текущий диалог в одно системное сообщение.\n" + \
             "/reset - Сбросить историю переписки из памяти.\n"
        await self._send_message(update.message, help_text)

    async def info_private_chat(self, update, context):
        message = update.message
        user_history = TelegamUserHistory.get_history(message, self._logs_dir)
        storage = user_history.get_storage()
        messages_count = len(storage)
        tokens_count = 0 if messages_count == 0 else self._ai_handler.count_tokens(storage)
        info_text = f"Количество сообщений: {messages_count}\nКоличество токенов: {tokens_count}"
        await self._send_message(message, info_text)

    async def summary_private_history(self, update, context):
        message = update.message
        user_history = TelegamUserHistory.get_history(message, self._logs_dir)
        if len(user_history.get_storage()) == 0:
            return await self._send_message(message, "Нет сообщений в контексте.")
        await self._summarize_if_need(message, user_history, hard_reset=True)

    async def private_chat_handler(self, update, context):
        message = update.message
        if not await self._check_is_valid_private_chat_update(message):
            return
        user_history = TelegamUserHistory.get_history(message, self._logs_dir)
        if message.voice:
            transcript = await self._get_voice_message_as_text(message, context)
            if transcript is None:
                return
            await self._handle_text_message(message, transcript, user_history)
            return
        stop = await self._check_and_handle_image_intent(message, context, user_history)
        if stop:
            return
        if message.text and len(message.text) > 0:
            await self._handle_text_message(message, message.text, user_history)

    async def _handle_text_message(self, message, text, user_history):
        is_bot = self._is_message_from_bot(message)
        user_history.add_to_history(text, is_bot=is_bot)
        await self._summarize_if_need(message, user_history)
        if is_bot:
            return
        generated_message = await self._text_private_chat_message_process(message, user_history)
        if generated_message is not None:
            user_history.add_to_history(generated_message, is_bot=True)
            await self._summarize_if_need(message, user_history)
        return

    async def group_messages_handler(self, update, context):
        message = update.message
        if not self._group_has_access(message):
            return await self._send_message(message, "You are not allowed to use this bot. Maybe you are crab or in past life you did something very very bad :).  Call @logrusak for help.")
        if not message.text:
            return
        text_message = message.text.lower()
        for regex, handler in self._triggers_check:
            if regex.match(text_message):
                await handler(message, text_message)
                return
        if self._is_message_reply_to_bot(message):
            reply = message.reply_to_message
            is_replay_image = reply.photo is not None and len(reply.photo) > 0
            if is_replay_image:
                await self._image_change_process(message, text_message)
                return
            await self._text_group_chat_message_process(message, text_message)
            return

    async def _check_and_handle_image_intent(self, message, context, user_history) -> bool:
        if message.photo is None:
            return False
        for regex, handler in self._images_triggers:
            if regex.match(message.text):
                await handler(message, message.text)
                return True
        return False

    async def _check_is_valid_private_chat_update(self, message) -> bool:
        if not self._is_message_for_handle(message):
            return False
        if not self._person_has_access(message):
            await self._send_message(message, "You are not allowed to use this bot. Maybe you are crab or in past life you did something very very bad :). Call @logrusak for help.")
            return False
        return True

    async def _summarize_if_need(self, message: Message, user_history: TelegamUserHistory, hard_reset=False):
        if not hard_reset:
            tokens_len = self._ai_handler.count_tokens(user_history.get_storage())
            if not self._ai_handler.needs_summarization(tokens_len):
                return
        messages = [
            {"role": "assistant", "content": "Обобщи этот разговор не более чем в 700 символах или меньше."},
            {"role": "user", "content": str(user_history.get_storage())}
        ]
        response_text, error = await self._ai_handler.get_chat_message_response(messages, user_history.user_id)
        if error is not None:
            return await self._send_message(message, "Ошибка при обобщении диалога:" + error)
        await user_history.summary_history(response_text)
        await self._send_message(message, "Достигнут лимит токенов. Диалог обобщен.")

    async def _text_private_chat_message_process(self, message: Message, history: TelegamUserHistory) -> str:
        user_id = message.from_user.id
        storage = history.get_storage()
        response_text, error = await self._ai_handler.get_chat_message_response(storage, user_id)
        if error is not None:
            return await self._send_message(message, "Ошибка при отправке сообщения:" + str(error))
        if response_text is not None:
            await self._send_message(message, response_text)
            history.add_to_history(response_text, is_bot=True)
            return response_text
        return None

    async def _text_group_chat_message_process(self, message, check_text):
        data_to_send = []
        reply_to_message = message.reply_to_message
        if reply_to_message is not None:
            reply_message = message.reply_to_message
            if self._is_message_for_handle(reply_message):
                role = "assistant" if self._is_message_from_bot(reply_message) else "user"
                data_to_send.append({"role": role, "content": reply_message.text})
        data_to_send.append({"role": "user", "content": check_text})
        user_id = message.from_user.id
        response_text, error = await self._ai_handler.get_chat_message_response(data_to_send, user_id)
        if error is not None:
            return await self._send_message(message, "Ошибка при обработке сообщения:" + error)
        if response_text is not None:
            await self._send_message(message, response_text)

    async def _image_create_process_from_cmd(self, update, context):
        message = update.message
        text = message.text
        await self._image_create_process(message, text)

    async def _image_create_process(self, message, generation_text):
        normalized_text = re.sub(self._image_trigger_regex, "", generation_text)
        normalized_text = normalized_text.strip()
        response_text, error = await self._ai_handler.get_image_create_response(normalized_text)
        if error is not None:
            return await self._send_message(message, "Ошибка при создании картинки:" + error)
        if response_text is not None:
            if response_text.startswith("http"):
                await message.reply_photo(response_text)
                return
            await self._send_message(message, response_text)

    async def _image_vision_process(self, message, check_text):
        normalized_text = re.sub(self._image_trigger_regex, "", check_text)
        normalized_text = normalized_text.strip()
        response_text = await self._ai_handler.get_image_create_response(normalized_text)
        if response_text is not None:
            if response_text.startswith("http"):
                await message.reply_photo(response_text)
                return
            await self._send_message(message, response_text)

    async def _image_change_process(self, message, check_text):
        return

    def _is_message_for_handle(self, message) -> bool:
        """Check if message have text, from_user and chat attributes for processing"""
        if message is None:
            return False
        attrs = ["from_user", "chat"]
        for attr in attrs:
            atr_val = getattr(message, attr, None)
            if atr_val is None:
                return False
        text_message = getattr(message, "text", None)
        image_message = getattr(message, "photo", None) and getattr(message, "caption", None)
        if text_message is None and image_message is None:
            return False
        return True

    def _is_message_from_bot(self, message):
        from_user = message.from_user
        if from_user is None:
            return False
        return from_user.is_bot

    def _is_message_reply_to_bot(self, message):
        reply_to_message = message.reply_to_message
        if reply_to_message is not None:
            return self._is_message_from_bot(reply_to_message)
        return False

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

    async def _get_voice_message_as_text(self, message: Message, context):
        filename = message.effective_attachment.file_unique_id
        filename_mp3 = f'/tmp/{filename}.mp3'
        try:
            media_file = await context.bot.get_file(message.effective_attachment.file_id)
            await media_file.download_to_drive(filename)
        except Exception as e:
            print("Error downloading voice message: ", e)
            return
        try:
            audio_track = AudioSegment.from_file(filename)
            audio_track.export(filename_mp3, format="mp3")
        except Exception as err:
            print(err)
        if await asyncio.to_thread(os.path.exists, filename):
            await asyncio.to_thread(os.remove, filename)
        transcript, error = await self._ai_handler.transcribe_voice_message(filename_mp3)
        if error is not None:
            return await self._send_message(message, "Ошибка при обработке голосового сообщения:" + error)
        if await asyncio.to_thread(os.path.exists, filename_mp3):
            await asyncio.to_thread(os.remove, filename_mp3)
        return transcript







