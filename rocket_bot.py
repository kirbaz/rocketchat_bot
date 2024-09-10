    import json
    import requests
    from flask import Flask, request
    from rocketchat_API.rocketchat import RocketChat

    app = Flask(__name__)

    ROCKETCHAT_URL = 'https://your_rocketchat_instance_url'
    BOT_TOKEN = 'your_bot_token'
    rocket = RocketChat(user_id='your_bot_user_id', auth_token=BOT_TOKEN, server_url=ROCKETCHAT_URL)

    @app.route('/webhook', methods=['POST'])
    def webhook():
        data = request.json
        if data and 'messages' in data:
            for message in data['messages']:
                if message['msg'].startswith('!'):  # Проверяем, что сообщение адресовано боту
                    user_id = message['u']['_id']
                    reply_to_user(user_id, message['msg'][1:])  # Отправляем ответ без '!' символа

        return '', 200

    def reply_to_user(user_id, message):
        response = handle_message(message)  # Ваша логика обработки сообщения
        rocket.chat_post_message(response, channel=user_id).json()

    def handle_message(message):
        # Пример логики обработки сообщения
        if message.lower() == 'привет':
            return 'Привет! Как я могу помочь?'
        return 'Я вас не понимаю. Попробуйте другое сообщение.'

    if __name__ == '__main__':
        app.run(port=5000)
    