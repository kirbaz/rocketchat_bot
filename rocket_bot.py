import asyncio
import logging
from rocketchat_API.rocketchat import RocketChat
from datetime import datetime, timedelta

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
        self.user_contexts = {}  # Храним контексты диалогов
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
            },
            'new_path': {
                'function': self.start_new_path_dialog,
                'description': 'Создать новый отчет (диалоговый режим)'
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

    async def handle_command(self, command_text, sender, room_id):
        """Обработка команд с проверкой аргументов"""
        try:
            # Проверяем, есть ли активный контекст у пользователя
            if sender in self.user_contexts:
                return await self.continue_dialog(sender, room_id, command_text)

            # Обработка команды new_path
            if command_text.startswith('new_path'):
                return await self.start_new_path_dialog(sender, room_id)

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

    async def process_path_request(self, sender, date_from, date_to, additional_info):
        # Здесь реализуйте вашу логику обработки
        # Это пример - замените на реальную логику
        try:
            # Имитация долгой обработки
            await asyncio.sleep(2)
            return (f"Отчет для {sender} с {date_from.strftime('%d-%m-%Y')} "
                    f"по {date_to.strftime('%d-%m-%Y')}\n"
                    f"Дополнительные параметры: {additional_info}\n"
                    f"Результат: данные успешно обработаны")
        except Exception as e:
            logger.error(f"Ошибка обработки запроса: {e}")
            return "Ошибка при обработке запроса"

    async def cleanup_contexts(self):
        while self.running:
            await asyncio.sleep(60)  # Проверка каждую минуту
            now = datetime.now()
            expired = [user for user, ctx in self.user_contexts.items()
                       if now - ctx['created_at'] > timedelta(minutes=5)]

            for user in expired:
                del self.user_contexts[user]
                logger.info(f"Удален просроченный контекст для {user}")

    async def start_new_path_dialog(self, sender, room_id):
        """Начало диалога создания отчета"""
        self.user_contexts[sender] = {
            'state': 'awaiting_dates',
            'room_id': room_id,
            'data': {},
            'created_at': datetime.now()
        }
        return "За какой промежуток времени? Введите 2 даты в формате ДД-ММ-ГГГГ. Например: 01-03-2025 01-04-2025"

    async def continue_dialog(self, sender, room_id, user_input):
        """Продолжение диалога"""
        context = self.user_contexts.get(sender)
        if not context:
            return "Диалог прерван. Начните заново командой new_path."

        try:
            if context['state'] == 'awaiting_dates':
                dates = user_input.split()
                if len(dates) != 2:
                    return "Нужно ввести ровно 2 даты. Попробуйте еще раз."

                try:
                    date1 = datetime.strptime(dates[0], "%d-%m-%Y")
                    date2 = datetime.strptime(dates[1], "%d-%m-%Y")

                    if date1 > date2:
                        return "Первая дата должна быть раньше второй. Попробуйте еще раз."

                    context['data']['dates'] = (date1, date2)
                    context['state'] = 'awaiting_additional_info'
                    return "Теперь укажите дополнительные параметры (например, тип отчета):"

                except ValueError:
                    return "Неверный формат даты. Используйте ДД-ММ-ГГГГ."

            elif context['state'] == 'awaiting_additional_info':
                result = await self.process_path_request(
                    sender,
                    context['data']['dates'][0],
                    context['data']['dates'][1],
                    user_input
                )
                del self.user_contexts[sender]
                return result

        except Exception as e:
            logger.error(f"Ошибка в диалоге: {e}")
            del self.user_contexts[sender]
            return "Произошла ошибка. Диалог прерван. Начните заново командой new_path."

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
        asyncio.create_task(self.cleanup_contexts())  # Добавить эту строку

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