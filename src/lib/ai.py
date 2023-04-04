import math
import os
from io import BytesIO

import openai

class OpenAI:

    def __init__(self, api_key=None, configuration=None):
        if not api_key:
            api_key = os.environ.get("openai_api_key", None)
        if not api_key:
            raise ValueError("OpenAI API key is not defined")
        openai.api_key = api_key
        if configuration is None:
            raise ValueError("Configuration is not defined")
        self._chat_model_name = configuration.chat_model_name
        self._image_size = configuration.image_size
        size = configuration.image_size.split('x')
        self._image_w = int(size[0])
        self._image_h = int(size[1])
        self._max_tokens = configuration.max_tokens
        self._temperature = configuration.temperature

    async def get_chat_message_response(self, messages: list, user_id: int) -> str | None:
        try:
            response = await openai.ChatCompletion.acreate(
                model=self._chat_model_name,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                user=str(user_id),
            )
        except Exception as e:
            return "Response error: " + str(e)
        dict_data = response.to_dict()
        choises = dict_data.get('choices', [])
        if not choises:
            return None
        choise = choises[0]
        message = choise.get('message', None)
        if message:
            content = message.get('content', None)
            if content:
                return content
        return None

    async def get_image_create_response(self, prompt: str):
        try:
            response = await openai.Image.acreate(prompt=prompt, n=1, size=self._image_size)
            image_url = response['data'][0]['url']
        except Exception as e:
            return "Response error: " + str(e)
        return image_url

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


