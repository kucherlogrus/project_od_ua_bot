import os
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

    async def get_image_variation_response(self, prompt: str, image: str):
        #TODO: implement
        # response = await openai.Image.acreate(prompt=prompt, n=1, size=self._image_size)
        # image_url = response['data'][0]['url']
        return "NOT IMPLEMENTED"

