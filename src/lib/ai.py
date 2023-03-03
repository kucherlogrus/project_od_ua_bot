import os
import openai

class ChatGPT:

    def __init__(self, api_key=None, model="gpt-3.5-turbo"):
        if not api_key:
            api_key = os.environ.get("openai_api_key", None)
        if not api_key:
            raise ValueError("OpenAI API key is not defined")
        openai.api_key = api_key
        self.model = model

    async def get_response(self, messages: list):
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=messages,
            max_tokens=2048,
            temperature=1.0
        )
        dict_data = response.to_dict()
        choises = dict_data.get('choices', [])
        for choise in choises:
            message = choise.get('message', None)
            if message:
                content = message.get('content', None)
                if content:
                    return content
        return None