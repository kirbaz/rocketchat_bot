   from rocketchat_API.rocketchat import RocketChat
   import requests
   import json

   # Параметры подключения к Rocket.Chat
   server_url = 'https://your-rocketchat-server.com'  # URL вашего Rocket.Chat сервера
   bot_user = 'bot_username'  # Имя пользователя вашего бота
   bot_password = 'bot_password'  # Пароль вашего бота

   # Создаем подключение к Rocket.Chat
   rocket = RocketChat(bot_user, bot_password, server_url=server_url)
      
def handle_message(message):
       user_id = message['u']['_id']
       text = message['msg']
       
       # Логика обработки сообщения
       if 'привет' in text.lower():
           response = 'Привет! Как я могу помочь?'
       else:
           response = 'Извините, я не понимаю ваш запрос.'
       
       # Ответ пользователю
       rocket.chat_post_message(response, channel=user_id)
   
   from flask import Flask, request

   app = Flask(__name__)


WEBHOOK_URL = "ваш_вебхук_URL"  # Укажите ваш webhook URL
TOKEN = "ваш_токен"  # Укажите ваш токен

@app.route(WEBHOOK_URL, methods=['POST'])
def webhook():
    data = request.json
    # Проверяем наличие сообщения в данных
    if 'messages' in data:
        for message in data['messages']:
            handle_message(message)
    return '', 200

if __name__ == '__main__':
    app.run(port=5000)

   if __name__ == '__main__':
       app.run(port=5000)
   