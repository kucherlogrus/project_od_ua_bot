### GPT-3 Telegram Bot

docker build --tag=gpt_t_bot .

docker run --rm --name chat_gpt_t_bot --env-file=env.dev gpt_t_bot
