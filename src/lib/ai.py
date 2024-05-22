import io
import math
import os
from io import BytesIO
from typing import Tuple

import tiktoken
import openai
from openai import AsyncOpenAI

from .errors import OpenAIException


class OpenAI:

    def __init__(self, api_key=None, configuration=None):
        if not api_key:
            api_key = os.environ.get("openai_api_key", None)
        if not api_key:
            raise ValueError("OpenAI API key is not defined")
        self.client = AsyncOpenAI(api_key=api_key)
        if configuration is None:
            raise ValueError("Configuration is not defined")
        self._chat_model_name = configuration.chat_model_name
        self._image_size = configuration.image_size
        size = configuration.image_size.split('x')
        self._image_w = int(size[0])
        self._image_h = int(size[1])
        self._max_tokens = configuration.max_tokens
        self._temperature = configuration.temperature
        self._tokens_per_message = configuration.tokens_per_message
        self._tokens_per_name = configuration.tokens_per_name

    async def get_chat_message_response(self, messages: list, user_id: int) -> Tuple[str | None, Exception | None]:
        try:
            response = await self.client.chat.completions.create(
                model=self._chat_model_name,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                user=str(user_id),
            )
        except Exception as e:
            return None, OpenAIException("Ошибка: " + str(e))
        dict_data = response.to_dict()
        choises = dict_data.get('choices', [])
        if not choises:
            return None, OpenAIException("Вариантов ответа не получено")
        choise = choises[0]
        message = choise.get('message', None)
        if message:
            content = message.get('content', None)
            if content:
                return content, None
        return None

    async def transcribe_voice_message(self, filename: str) -> Tuple[str | None, Exception | None]:
        try:
            with open(filename, "rb") as audio:
                result = await self.client.audio.transcriptions.create(model="whisper-1", file=audio, prompt="Необходимо распознать речь")
                return result.text, None
        except Exception as e:
            None, OpenAIException("Ошибка: " + str(e))
        return None

    async def text_to_voice(self, text: str) -> BytesIO | None:
        try:
            response = await self.client.audio.speech.create(model="tts-1",  voice="nova", input=text, response_format='opus')
            temp_file = io.BytesIO()
            temp_file.write(response.read())
            temp_file.seek(0)
            return temp_file
        except Exception as e:
            print(e)
        return None

    async def get_image_create_response(self, prompt: str) -> Tuple[str | None, Exception | None]:
        try:
            response = await self.client.images.generate(prompt=prompt, n=1, size=self._image_size, quality="standard")
            image_url = response.data[0].url
            return image_url, None
        except Exception as e:
            return None, OpenAIException("OpenAI: " + str(e))

    async def get_image_variation_response(self, buffer: BytesIO, mask: BytesIO, prompt: str):
        try:
            response = await openai.Image.acreate_edit(image=buffer, mask=mask, prompt=prompt, n=1, size=self._image_size)
            image_url = response['data'][0]['url']
        except Exception as e:
            return "Response error: " + str(e)
        return image_url

    def get_image_to_change(self, images: dict):
        nearest = -1
        nearest_id = None
        for f_id, data in images.items():
            if data['w'] == self._image_w and data['h'] == self._image_h:
                return f_id, self._image_w, self._image_h
            candidate = math.fabs(data['w'] - self._image_w) + math.fabs(data['h'] - self._image_h)
            if nearest == -1 or candidate < nearest:
                nearest = candidate
                nearest_id = f_id
        return nearest_id,  self._image_w, self._image_h

    def count_tokens(self, messages) -> int:
        model = self._chat_model_name
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            raise ValueError(f"Model {model} not recognised")
        tokens_per_message = self._tokens_per_message
        tokens_per_name = self._tokens_per_name
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                if key == 'content':
                    if isinstance(value, str):
                        num_tokens += len(encoding.encode(value))
                    # else:
                    #     for message1 in value:
                    #         if message1['type'] == 'image_url':
                    #             image = decode_image(message1['image_url']['url'])
                    #             num_tokens += self.__count_tokens_vision(image)
                    #         else:
                    #             num_tokens += len(encoding.encode(message1['text']))
                else:
                    num_tokens += len(encoding.encode(value))
                    if key == "name":
                        num_tokens += tokens_per_name
        num_tokens += 3
        return num_tokens

    def needs_summarization(self, tokens_count) -> bool:
        if tokens_count < self._max_tokens:
            return False
        return True