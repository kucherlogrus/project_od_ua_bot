### GPT-3 Telegram Bot


* Create env.dev file with params:

  openai_api_key=< YOUR API KEY >
  
  telegram_token=< TELEGRAM BOT TOKEN >

* Build docker container:

  docker build --tag=gpt_t_bot .

* Run simple::


  docker run --rm --name chat_gpt_t_bot --env-file=env.dev gpt_t_bot

* Run in background::


  docker run --rm --name chat_gpt_t_bot -d --env-file=env.dev gpt_t_bot

