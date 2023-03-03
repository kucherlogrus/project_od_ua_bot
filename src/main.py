from lib.ai import ChatGPT
from lib.telegram import TelegramBot

def main():
    chat_gpt = ChatGPT()
    telegram_app = TelegramBot()
    telegram_app.set_ai_message_handler(chat_gpt)
    telegram_app.start_telegram_bot()

if __name__ == '__main__':
    main()