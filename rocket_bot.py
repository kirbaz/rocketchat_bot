import asyncio
import logging
import re
from rocketchat_API.rocketchat import RocketChat
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import csv
import io
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
        self.processed_messages = set()
        self.user_contexts: Dict[str, Dict[str, Any]] = {}

        self.commands = {
            'help': {
                'function': self.show_help,
                'description': 'Показать список команд'
            },
            'ping': {
                'function': self.ping,
                'description': 'Проверить работу бота'
            },
            'new_path': {
                'function': self.start_new_path_dialog,
                'description': 'Создать новый отчет (диалоговый режим)'
            },
            'db_check': {
                'function': self.start_db_check_dialog,
                'description': 'Проверить данные в базе'
            },
            'schedule': {
                'function': self.start_schedule_meeting_dialog,
                'description': 'Запланировать встречу'
            },
            'report': {
                'function': self.start_report_request_dialog,
                'description': 'Запросить специальный отчет'
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

    # async def process_room(self, room_id):
    #     # Rocket.Chat API имеет лимиты на частоту запросов
    #     # Рекомендуется добавить задержку между запросами к одной комнате:
    #     now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    #     messages = self.rocket.im_history(room_id=room_id, count=10).json().get('messages', [])
    #     await asyncio.sleep(0.1)  # Задержка 100 мс между запросами
    #     for msg in messages:
    #         if msg['_id'] not in self.processed_messages:
    #             await self.process_message(msg)
    #             self.processed_messages.add(msg['_id'])

    async def process_room(self, room_id):
        # Загружаем только сообщения, отправленные после текущего времени минус 5 секунд
        # now_five_min = (datetime.utcnow() - timedelta(minutes=5))
        # print(f'now - {now_five_min}')
        # message_last = self.rocket.im_history(room_id=room_id, count=1, oldest=now_five_min).json().get('messages', [])
        # print(message_last)
        # if message_last:
        #     message_last_ts = datetime.strptime(message_last[0]['ts'], "%Y-%m-%dT%H:%M:%S.%fZ")
        #     print(message_last_ts)
        #     if message_last_ts < now_five_min:
        #         print('старые сообщения')
        #         print(message_last)
        #         await self.process_room(room_id)

        messages = self.rocket.im_history(room_id=room_id, count=1).json().get('messages', [])


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


    async def handle_command(self, command_text: str, sender: str, room_id: str) -> Optional[str]:
        """Основной обработчик команд с поддержкой контекста"""
        try:
            if sender in self.user_contexts:
                return await self.continue_dialog(sender, room_id, command_text)

            parts = command_text.split()
            if not parts:
                return None

            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            if command in self.commands:
                return await self.commands[command]['function'](sender, room_id, *args)

            return None
        except Exception as e:
            logger.error(f"Command handling error: {e}")
            return "Произошла ошибка при обработке команды"

    # ======================
    # Диалог для new_path
    # ======================
    async def start_new_path_dialog(self, sender: str, room_id: str) -> str:
        """Начало диалога создания пути"""
        self.user_contexts[sender] = {
            'state': 'awaiting_dates',
            'room_id': room_id,
            'handler': self.handle_new_path_dialog,
            'data': {},
            'created_at': datetime.now()
        }
        return "За какой промежуток времени? Введите 2 даты в формате ДД-ММ-ГГГГ"

    async def handle_new_path_dialog(self, sender: str, state: str, user_input: str) -> Tuple[str, str]:
        """Обработчик шагов диалога new_path"""
        if user_input.lower() == 'отмена':
            return "complete", "Диалог прерван"

        if state == 'awaiting_dates':
            try:
                date1, date2 = map(lambda x: datetime.strptime(x, "%d-%m-%Y"), user_input.split())
                if date1 > date2:
                    return "awaiting_dates", "Первая дата должна быть раньше второй. Попробуйте еще раз."

                return "awaiting_details", "Теперь укажите детали маршрута (города, транспорт и т.д.):"
            except:
                return "awaiting_dates", "Неверный формат дат. Используйте ДД-ММ-ГГГГ (например: 01-01-2025 15-01-2025)"

        elif state == 'awaiting_details':
            # Здесь можно добавить обработку деталей
            return "complete", f"Маршрут запланирован с деталями: {user_input}"


    # ======================
    # Функция обработки отчетов
    # ======================
    async def start_report_request_dialog(self, sender: str, room_id: str) -> str:
        """Начало диалога запроса специального отчета"""
        self.user_contexts[sender] = {
            'state': 'awaiting_report_type',
            'room_id': room_id,
            'handler': self.handle_report_request_dialog,
            'data': {},
            'created_at': datetime.now()
        }
        return ("Какой отчет вам нужен? Выберите тип:\n"
                "1. Ежедневный\n"
                "2. Еженедельный\n"
                "3. Пользовательский\n"
                "Введите номер варианта")

    async def handle_report_request_dialog(self, sender: str, state: str, user_input: str) -> Tuple[str, str]:
        """Обработчик шагов диалога запроса отчета"""
        if user_input.lower() == 'отмена':
            return "complete", "Диалог прерван"

        if state == 'awaiting_report_type':
            report_types = {
                '1': 'daily',
                '2': 'weekly',
                '3': 'custom'
            }

            if user_input not in report_types:
                return "awaiting_report_type", "Неверный вариант. Введите число от 1 до 3"

            if user_input == '3':  # Для пользовательского отчета запросим дополнительные параметры
                return "awaiting_custom_params", "Введите параметры отчета (период, фильтры и т.д.):"

            return "complete", f"Отчет ({report_types[user_input]}) будет сформирован и отправлен вам в течение часа"

        elif state == 'awaiting_custom_params':
            return "complete", f"Пользовательский отчет с параметрами '{user_input}' будет сформирован в течение 2 часов"

    # ======================
    # Диалог для проверки БД
    # ======================
    async def start_db_check_dialog(self, sender: str, room_id: str) -> str:
        """Начало диалога проверки базы данных"""
        self.user_contexts[sender] = {
            'state': 'awaiting_search_type',
            'room_id': room_id,
            'handler': self.handle_db_check_dialog,
            'data': {},
            'created_at': datetime.now()
        }
        return ("Как будем искать данные? Выберите тип:\n"
                "1. По ФИО\n"
                "2. По отделу\n"
                "3. По местоположению\n"
                "Введите номер варианта")

    async def handle_db_check_dialog(self, sender: str, state: str, user_input: str) -> Tuple[str, str]:
        """Обработчик шагов диалога проверки БД"""

        if user_input.lower() == 'отмена':
            return "complete", "Диалог прерван"

        if state == 'awaiting_search_type':
            search_types = {
                '1': 'fio',
                '2': 'department',
                '3': 'location'
            }

            if user_input not in search_types:
                return "awaiting_search_type", "Неверный вариант. Введите число от 1 до 3"

            return "awaiting_search_value", f"Введите значение для поиска по {search_types[user_input]}:"

        elif state == 'awaiting_search_value':
            return "awaiting_file", "Теперь отправьте CSV файл с данными для проверки"

        elif state == 'awaiting_file':
            if not user_input.lower().endswith('.csv'):
                return "awaiting_file", "Пожалуйста, отправьте именно CSV файл"

            # Здесь была бы обработка файла
            return "complete", "Данные успешно проверены. Найдено 42 совпадения"

    # ======================
    # Диалог планирования встречи
    # ======================
    async def start_schedule_meeting_dialog(self, sender: str, room_id: str) -> str:
        """Начало диалога планирования встречи"""
        self.user_contexts[sender] = {
            'state': 'awaiting_participants',
            'room_id': room_id,
            'handler': self.handle_schedule_meeting_dialog,
            'data': {},
            'created_at': datetime.now()
        }
        return "Введите участников встречи (через запятую):"

    async def handle_schedule_meeting_dialog(self, sender: str, state: str, user_input: str) -> Tuple[str, str]:
        """Обработчик шагов диалога планирования встречи"""
        if user_input.lower() == 'отмена':
            return "complete", "Диалог прерван"

        if state == 'awaiting_participants':
            participants = [p.strip() for p in user_input.split(',')]
            if len(participants) < 1:
                return "awaiting_participants", "Нужно указать хотя бы одного участника"

            return "awaiting_date", "Введите дату и время встречи (ДД-ММ-ГГГГ ЧЧ:ММ):"

        elif state == 'awaiting_date':
            try:
                meeting_time = datetime.strptime(user_input, "%d-%m-%Y %H:%M")
                if meeting_time < datetime.now():
                    return "awaiting_date", "Дата должна быть в будущем. Попробуйте еще раз"

                return "awaiting_topic", "Введите тему встречи:"
            except:
                return "awaiting_date", "Неверный формат. Используйте ДД-ММ-ГГГГ ЧЧ:ММ"

        elif state == "awaiting_topic":
            return "complete", f"Встреча запланирована на тему: {user_input}"

    # ======================
    # Общий обработчик диалогов
    # ======================
    async def continue_dialog(self, sender: str, room_id: str, user_input: str) -> Optional[str]:
        """Продолжение диалога на основе контекста"""
        if sender not in self.user_contexts:
            return None

        context = self.user_contexts[sender]
        handler = context['handler']
        state = context['state']

        try:
            new_state, response = await handler(sender, state, user_input)

            if new_state == "complete":
                del self.user_contexts[sender]
                return response
            else:
                context['state'] = new_state
                return response

        except Exception as e:
            logger.error(f"Dialog error for {sender}: {e}")
            del self.user_contexts[sender]
            return "Произошла ошибка. Диалог прерван."

    async def cleanup_contexts(self):
        while self.running:
            await asyncio.sleep(60)  # Проверка каждую минуту
            now = datetime.now()
            expired = [user for user, ctx in self.user_contexts.items()
                       if now - ctx['created_at'] > timedelta(minutes=5)]

            for user in expired:
                del self.user_contexts[user]
                logger.info(f"Удален просроченный контекст для {user}")

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
