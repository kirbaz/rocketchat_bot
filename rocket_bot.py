import asyncio
import logging
from rocketchat_API.rocketchat import RocketChat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RocketChatBot:
    def __init__(self, config):
        self.config = config
        self.rocket = None
        self.user_id = None
        self.username = None
        self.running = False
        self.processed_messages = set()  # Храним ID обработанных сообщений
        self.commands = {
            'help': {
                'function': self.show_help,
                'description': 'Показать список команд'
            },
            'ping': {
                'function': self.ping,
                'description': 'Проверить работу бота'
            },
            'calc': {
                'function': self.calculate,
                'description': 'Выполнить вычисления (пример: calc 2+2)'
            }
        }

    async def connect(self):
        """Подключение к REST API"""
        try:
            self.rocket = RocketChat(
                user=self.config['username'],
                password=self.config['password'],
                server_url=self.config['server_url']
            )
            me = self.rocket.me().json()
            self.user_id = me['_id']
            self.username = me['username']
            logger.info(f"Подключено как {self.username}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False

    async def get_new_messages(self):
        try:
            # self.rocket.im_list() - Вызов REST API Rocket.Chat для получения списка личных чатов
            # .get('ims', []) - Безопасное извлечение списка чатов (если ключа нет, вернёт пустой список)
            im_list = self.rocket.im_list().json().get('ims', [])

            # Создаем задачи для параллельной обработки комнат
            tasks = []  # Инициализация списка для хранения задач
            for chat in im_list:  # Перебор всех полученных чатов
                # Создание асинхронной задачи для обработки одной комнаты:
                # Задача начинает выполняться сразу после создания
                # Не блокирует основной поток
                task = asyncio.create_task(self.process_room(chat['_id']))
                tasks.append(task)

            # *tasks - распаковка списка задач в отдельные аргументы
            await asyncio.gather(*tasks)  # Ожидание завершения всех созданных задач:

        except Exception as e:
            logger.error(f"Ошибка получения сообщений: {e}")

    async def process_room(self, room_id):
        # Rocket.Chat API имеет лимиты на частоту запросов
        # Рекомендуется добавить задержку между запросами к одной комнате:
        messages = self.rocket.im_history(room_id=room_id, count=10).json().get('messages', [])
        await asyncio.sleep(0.1)  # Задержка 100 мс между запросами
        for msg in messages:
            if msg['_id'] not in self.processed_messages:
                await self.process_message(msg)
                self.processed_messages.add(msg['_id'])

    async def process_message(self, message):
        """Обработка сообщения"""
        try:
            text = message.get('msg', '').strip()
            sender = message['u']['username']
            room_id = message['rid']

            logger.info(f"Новое сообщение от {sender}: {text}")

            # Добавляем room_id при вызове
            response = await self.handle_command(text, sender, room_id)
            if response:
                self.rocket.chat_post_message(
                    room_id=room_id,
                    text=response
                )
                logger.info(f"Отправлен ответ: {response}")

        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")

    async def handle_command(self, command_text, sender, room_id=None):
        """Обработка команд с проверкой аргументов"""
        try:
            if not command_text or not sender:
                logger.error("Не хватает обязательных аргументов")
                return None

            parts = command_text.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            if command in self.commands:
                logger.debug(f"Выполнение команды {command} от {sender} в комнате {room_id}")
                return await self.commands[command]['function'](sender, room_id, *args)
            return None

        except Exception as e:
            logger.error(f"Ошибка обработки команды: {e}")
            return f"@{sender} Произошла ошибка при выполнении команды"

    async def show_help(self, sender, room_id, *args):
        help_text = "Доступные команды:\n"
        for cmd, data in self.commands.items():
            help_text += f"• {cmd} - {data['description']}\n"
        return help_text

    async def ping(self, sender, room_id, *args):
        return "Pong! 🏓"

    async def calculate(self, sender, room_id, *args):
        if not args:
            return "Укажите выражение для вычисления (например: calc 2+2)"
        try:
            expression = ' '.join(args)
            result = eval(expression)  # Будьте осторожны с eval!
            return f"Результат: {expression} = {result}"
        except Exception as e:
            return f"Ошибка вычисления: {e}"

    async def run(self):
        """Основной цикл"""
        self.running = True

        if not await self.connect():
            self.running = False
            return

        logger.info("Бот запущен. Ожидание сообщений...")

        try:
            while self.running:
                await self.get_new_messages()
                await asyncio.sleep(3)  # Проверка каждые 3 секунды

        except KeyboardInterrupt:
            logger.info("Остановка по запросу пользователя")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        finally:
            self.running = False
            logger.info("Бот остановлен")


if __name__ == "__main__":
    config = {
        'server_url': 'http://localhost:3000',
        'username': 'ArbiTrue',
        'password': 'ArbiTrue'
    }

    bot = RocketChatBot(config)
    asyncio.run(bot.run())