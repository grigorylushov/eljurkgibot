import os
import logging
import requests
import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import pymysql
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "7994222730:AAGлогично_токен_не_работаетFUG52uZtk6H7M0FWwrWGZFKm0QxMKgEk"
API_BASE_URL = "https://eljurkgi.great-site.net/api/bot"

# Настройки базы данных - ОБНОВЛЕННЫЕ ДАННЫЕ
DB_CONFIG = {
    'host': 'b978624gy.beget.tech',
    'user': 'b978624gy_eljur',
    'password': 'jpX9r86O91R94e9',
    'database': 'b978624gy_eljur',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10,
    'read_timeout': 10,
}

class Database:
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=5)
    
    async def execute_query(self, query, params=None):
        """Выполнение SQL запроса в отдельном потоке"""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self.thread_pool, 
                self._execute_sync, 
                query, 
                params
            )
            return result
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return None
    
    def _execute_sync(self, query, params=None):
        """Синхронное выполнение SQL запроса"""
        connection = None
        try:
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                    return result
                else:
                    connection.commit()
                    return cursor.rowcount
        except pymysql.Error as e:
            logger.error(f"MySQL error [{e.args[0]}]: {e.args[1]}")
            if connection:
                connection.rollback()
            return None
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
        finally:
            if connection:
                connection.close()
    
    async def test_connection(self):
        """Тестирование подключения к базе данных"""
        try:
            result = await self.execute_query("SELECT 1 as connection_test")
            if result and result[0]['connection_test'] == 1:
                logger.info("✅ Database connection successful")
                return True
            else:
                logger.error("❌ Database connection test failed")
                return False
        except Exception as e:
            logger.error(f"❌ Database test failed: {e}")
            return False

class EljurBot:
    def __init__(self):
        self.api_url = API_BASE_URL
        self.db = Database()
        
    async def call_api(self, action, data):
        """Вызов API элжура"""
        try:
            payload = {"action": action, **data}
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result.get('data')
                else:
                    logger.error(f"API error: {result.get('error')}")
                    return None
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        telegram_user_id = user.id
        
        # Проверяем привязку аккаунта
        user_info = await self.get_user_by_telegram_id(telegram_user_id)
        
        if user_info:
            message = (
                f"👋 Привет, {user_info['full_name']}!\n\n"
                f"✅ Ваш аккаунт Элжур привязан\n"
                f"🎯 Роль: {self.get_role_name(user_info['role'])}\n\n"
                f"📋 <b>Доступные команды:</b>\n"
                f"📊 /grades - Посмотреть оценки\n"
                f"📚 /homework - Домашние задания\n"
                f"📅 /schedule - Расписание\n"
                f"👤 /profile - Информация о профиле\n"
                f"🔗 /unlink - Отвязать аккаунт\n"
                f"❓ /help - Помощь"
            )
        else:
            message = (
                "👋 Добро пожаловать в <b>Элжур КГИ</b>!\n\n"
                "Я ваш помощник для работы с электронным журналом.\n\n"
                "🔐 <b>Для начала работы:</b>\n"
                "1. Используйте /login для получения кода привязки\n"
                "2. Введите код в вашем профиле на сайте\n\n"
                "📋 <b>Команды:</b>\n"
                "🔐 /login - Привязать аккаунт\n"
                "❓ /help - Помощь"
            )
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерация кода для привязки аккаунта"""
        user = update.effective_user
        
        # Проверяем, не привязан ли уже аккаунт
        existing_binding = await self.get_user_by_telegram_id(user.id)
        if existing_binding:
            await update.message.reply_text(
                "❌ Ваш аккаунт уже привязан! Используйте /unlink для отвязки.",
                parse_mode='HTML'
            )
            return
        
        # Генерируем код
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expires_at = datetime.now() + timedelta(minutes=10)
        
        # Сохраняем код в базу
        try:
            sql = """
            INSERT INTO telegram_bindings 
            (telegram_user_id, telegram_username, telegram_first_name, telegram_last_name, bind_code, bind_code_expires)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            bind_code = VALUES(bind_code), 
            bind_code_expires = VALUES(bind_code_expires),
            is_active = 0
            """
            result = await self.db.execute_query(sql, (
                user.id,
                user.username,
                user.first_name,
                user.last_name,
                code,
                expires_at
            ))
            
            if result is not None:
                message = (
                    f"🔐 <b>Привязка аккаунта</b>\n\n"
                    f"Чтобы привязать ваш Telegram к аккаунту Элжур:\n\n"
                    f"1. Перейдите в ваш профиль на сайте\n"
                    f"2. Найдите раздел \"Telegram бот\"\n"
                    f"3. Введите этот код:\n\n"
                    f"<code>{code}</code>\n\n"
                    f"⏰ Код действителен до {expires_at.strftime('%H:%M')}\n"
                    f"🔒 После ввода кода ваш аккаунт будет автоматически привязан"
                )
                
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "❌ Ошибка при генерации кода. Не удалось подключиться к базе данных.",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Error saving bind code: {e}")
            await update.message.reply_text(
                "❌ Ошибка при генерации кода. Проблема с подключением к базе данных.",
                parse_mode='HTML'
            )
    
    async def handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода кода привязки"""
        # Пока просто сообщаем о необходимости использовать /login
        await update.message.reply_text(
            "🔐 Для привязки аккаунта используйте команду /login чтобы получить код, "
            "затем введите его в вашем профиле на сайте.",
            parse_mode='HTML'
        )
    
    async def grades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ оценок"""
        user = update.effective_user
        telegram_user_id = user.id
        
        # Проверяем привязку
        user_info = await self.get_user_by_telegram_id(telegram_user_id)
        if not user_info:
            await self.send_not_linked_message(update)
            return
        
        # Получаем оценки из базы
        grades_data = await self.get_user_grades(user_info['id'])
        
        if not grades_data:
            await update.message.reply_text("📊 Оценок пока нет")
            return
        
        message = "📊 <b>Последние оценки</b>\n\n"
        
        for grade in grades_data[:10]:
            emoji = self.get_grade_emoji(float(grade['grade']))
            subject_name = grade.get('subject_name', 'Неизвестный предмет')
            
            message += f"{emoji} <b>{subject_name}</b>\n"
            message += f"Оценка: <b>{grade['grade']}</b> • {grade['date']}\n"
            
            if grade.get('comment'):
                message += f"💬 {grade['comment']}\n"
            
            message += "\n"
        
        if len(grades_data) > 10:
            message += f"\n... и еще {len(grades_data) - 10} оценок"
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="refresh_grades")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
    
    async def homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ домашних заданий"""
        user = update.effective_user
        telegram_user_id = user.id
        
        user_info = await self.get_user_by_telegram_id(telegram_user_id)
        if not user_info:
            await self.send_not_linked_message(update)
            return
        
        homework_data = await self.get_user_homework(user_info['id'], user_info['role'])
        
        if not homework_data:
            await update.message.reply_text("📚 Активных заданий нет")
            return
        
        message = "📚 <b>Ближайшие задания</b>\n\n"
        
        for hw in homework_data[:5]:
            due_date = hw['due_date']
            if isinstance(due_date, str):
                days_left = self.get_days_until(due_date)
            else:
                days_left = (due_date - datetime.now().date()).days
            days_text = self.get_days_text(days_left)
            
            if user_info['role'] == 'teacher':
                message += f"👨‍🏫 <b>{hw['subject_name']}</b> - {hw.get('class_name', 'Неизвестный класс')}\n"
            else:
                message += f"📖 <b>{hw['subject_name']}</b>\n"
                if hw.get('teacher_name'):
                    message += f"👨‍🏫 {hw['teacher_name']}\n"
            
            message += f"📝 <b>{hw['title']}</b>\n"
            message += f"⏰ До: <b>{due_date}</b> ({days_text})\n"
            
            if hw.get('description'):
                desc = str(hw['description'])[:80] + "..." if len(str(hw['description'])) > 80 else str(hw['description'])
                message += f"ℹ️ {desc}\n"
            
            message += "\n"
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="refresh_homework")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
    
    async def schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ расписания"""
        user = update.effective_user
        telegram_user_id = user.id
        
        user_info = await self.get_user_by_telegram_id(telegram_user_id)
        if not user_info:
            await self.send_not_linked_message(update)
            return
        
        schedule_data = await self.get_user_schedule(user_info['id'], user_info['role'])
        
        if not schedule_data:
            await update.message.reply_text("📅 На сегодня занятий нет")
            return
        
        day_name = self.get_day_name()
        message = f"📅 <b>Расписание на {day_name}</b>\n\n"
        
        for lesson in schedule_data:
            start_time = lesson.get('start_time', '--:--')
            if isinstance(start_time, timedelta):
                start_time = str(start_time)
            start_time = str(start_time)[:5] if start_time else '--:--'
            
            end_time = lesson.get('end_time', '--:--')
            if isinstance(end_time, timedelta):
                end_time = str(end_time)
            end_time = str(end_time)[:5] if end_time else '--:--'
            
            message += f"🕒 <b>{start_time} - {end_time}</b>\n"
            message += f"📚 {lesson['subject_name']}\n"
            message += f"👨‍🏫 {lesson.get('teacher_name', 'Не указан')}\n"
            
            if lesson.get('room'):
                message += f"🚪 {lesson['room']}\n"
            
            message += "\n"
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="refresh_schedule")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
    
    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о профиле"""
        user = update.effective_user
        telegram_user_id = user.id
        
        user_info = await self.get_user_by_telegram_id(telegram_user_id)
        if not user_info:
            await self.send_not_linked_message(update)
            return
        
        message = (
            f"👤 <b>Информация о профиле</b>\n\n"
            f"👤 <b>{user_info['full_name']}</b>\n"
            f"🎯 Роль: <b>{self.get_role_name(user_info['role'])}</b>\n"
            f"📧 Логин: <code>{user_info['username']}</code>\n"
        )
        
        if user_info.get('email'):
            message += f"📨 Email: {user_info['email']}\n"
        
        if user_info.get('last_login'):
            last_login = user_info['last_login']
            if isinstance(last_login, datetime):
                last_login = last_login.strftime('%d.%m.%Y %H:%M')
            message += f"🕒 Последний вход: {last_login}\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def unlink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отвязка аккаунта"""
        user = update.effective_user
        telegram_user_id = user.id
        
        try:
            sql = "UPDATE telegram_bindings SET is_active = 0, unlinked_at = %s WHERE telegram_user_id = %s AND is_active = 1"
            result = await self.db.execute_query(sql, (datetime.now(), telegram_user_id))
            
            if result and result > 0:
                message = "✅ Аккаунт успешно отвязан!"
            else:
                message = "❌ Аккаунт не был привязан"
            
            await update.message.reply_text(message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error unlinking account: {e}")
            await update.message.reply_text("❌ Ошибка при отвязке аккаунта", parse_mode='HTML')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Помощь по командам"""
        message = (
            "❓ <b>Помощь по боту Элжур КГИ</b>\n\n"
            "<b>📋 Основные команды:</b>\n"
            "🔐 /login - Привязать аккаунт\n"
            "📊 /grades - Посмотреть оценки\n"
            "📚 /homework - Домашние задания\n"
            "📅 /schedule - Расписание\n"
            "👤 /profile - Информация о профиле\n"
            "🔗 /unlink - Отвязать аккаунт\n"
            "❓ /help - Эта справка\n\n"
            "<b>🔐 Привязка аккаунта:</b>\n"
            "1. Используйте /login для получения кода\n"
            "2. В веб-версии введите код в профиле\n\n"
            "<b>📞 Поддержка:</b>\n"
            "✉️ grigorylushov@gmail.com"
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик inline кнопок"""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        
        if action == "refresh_grades":
            await self.grades(update, context)
        elif action == "refresh_homework":
            await self.homework(update, context)
        elif action == "refresh_schedule":
            await self.schedule(update, context)
    
    async def send_not_linked_message(self, update):
        """Сообщение о непривязанном аккаунте"""
        message = (
            "🔐 <b>Аккаунт не привязан</b>\n\n"
            "Для использования бота необходимо привязать ваш аккаунт Элжур.\n\n"
            "<b>Как привязать:</b>\n"
            "1. Используйте команду /login\n"
            "2. Получите код привязки\n"
            "3. Введите код в веб-версии\n\n"
            "После привязки вам станут доступны все функции бота!"
        )
        
        if hasattr(update, 'message'):
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.callback_query.message.reply_text(message, parse_mode='HTML')
    
    # Методы работы с базой данных
    async def get_user_by_telegram_id(self, telegram_user_id):
        """Получение пользователя по Telegram ID"""
        try:
            sql = """
            SELECT u.* FROM users u
            INNER JOIN telegram_bindings tb ON u.id = tb.user_id
            WHERE tb.telegram_user_id = %s AND tb.is_active = 1
            """
            result = await self.db.execute_query(sql, (telegram_user_id,))
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user by telegram ID: {e}")
            return None
    
    async def get_user_grades(self, user_id):
        """Получение оценок пользователя"""
        try:
            sql = """
            SELECT g.*, s.name as subject_name, t.full_name as teacher_name
            FROM grades g
            LEFT JOIN subjects s ON g.subject_id = s.id
            LEFT JOIN users t ON g.teacher_id = t.id
            WHERE g.student_id = %s
            ORDER BY g.date DESC, g.id DESC
            LIMIT 20
            """
            return await self.db.execute_query(sql, (user_id,))
        except Exception as e:
            logger.error(f"Error getting user grades: {e}")
            return None
    
    async def get_user_homework(self, user_id, role):
        """Получение домашних заданий"""
        try:
            if role == 'teacher':
                sql = """
                SELECT h.*, s.name as subject_name, c.name as class_name
                FROM homeworks h
                LEFT JOIN subjects s ON h.subject_id = s.id
                LEFT JOIN classes c ON h.class_id = c.id
                WHERE h.teacher_id = %s AND h.due_date >= CURDATE()
                ORDER BY h.due_date ASC
                LIMIT 10
                """
            else:
                sql = """
                SELECT h.*, s.name as subject_name, u.full_name as teacher_name
                FROM homeworks h
                LEFT JOIN subjects s ON h.subject_id = s.id
                LEFT JOIN users u ON h.teacher_id = u.id
                LEFT JOIN class_students cs ON cs.class_id = h.class_id
                WHERE cs.student_id = %s AND h.due_date >= CURDATE()
                ORDER BY h.due_date ASC
                LIMIT 10
                """
            return await self.db.execute_query(sql, (user_id,))
        except Exception as e:
            logger.error(f"Error getting user homework: {e}")
            return None
    
    async def get_user_schedule(self, user_id, role):
        """Получение расписания"""
        try:
            day_name = self.get_day_name().lower()
            
            if role == 'teacher':
                sql = """
                SELECT s.*, sub.name as subject_name, c.name as class_name
                FROM schedule s
                LEFT JOIN subjects sub ON s.subject_id = sub.id
                LEFT JOIN classes c ON s.class_id = c.id
                WHERE s.teacher_id = %s AND s.day_of_week = %s
                ORDER BY s.lesson_number ASC
                """
            else:
                sql = """
                SELECT s.*, sub.name as subject_name, u.full_name as teacher_name
                FROM schedule s
                LEFT JOIN subjects sub ON s.subject_id = sub.id
                LEFT JOIN users u ON s.teacher_id = u.id
                LEFT JOIN class_students cs ON cs.class_id = s.class_id
                WHERE cs.student_id = %s AND s.day_of_week = %s
                ORDER BY s.lesson_number ASC
                """
            return await self.db.execute_query(sql, (user_id, day_name))
        except Exception as e:
            logger.error(f"Error getting user schedule: {e}")
            return None
    
    # Вспомогательные методы
    def get_role_name(self, role):
        roles = {
            'admin': '👑 Администратор',
            'teacher': '👨‍🏫 Учитель',
            'student': '🎓 Ученик',
            'parent': '👨‍👩‍👧‍👦 Родитель'
        }
        return roles.get(role, role)
    
    def get_grade_emoji(self, grade):
        if grade >= 4.5: return '🎯'
        if grade >= 3.5: return '👍'
        if grade >= 2.5: return '😐'
        return '😞'
    
    def get_days_until(self, date_str):
        try:
            due_date = datetime.strptime(str(date_str), '%Y-%m-%d')
            today = datetime.now()
            return (due_date - today).days
        except (ValueError, TypeError):
            return 0
    
    def get_days_text(self, days):
        if days == 0: return "сегодня"
        if days == 1: return "завтра"
        if days == -1: return "вчера"
        if days < 0: return f"просрочено на {abs(days)} дн."
        return f"через {days} дн."
    
    def get_day_name(self):
        days = [
            'Понедельник', 'Вторник', 'Среда', 
            'Четверг', 'Пятница', 'Суббота', 'Воскресенье'
        ]
        return days[datetime.now().weekday()]
    
    async def test_database_connection(self):
        """Тестирование подключения к базе данных"""
        return await self.db.test_connection()

async def initialize_bot():
    """Инициализация и проверка бота"""
    bot = EljurBot()
    
    # Проверяем подключение к базе данных
    logger.info("🔍 Проверка подключения к базе данных...")
    logger.info(f"📊 Хост: {DB_CONFIG['host']}")
    logger.info(f"👤 Пользователь: {DB_CONFIG['user']}")
    logger.info(f"🗃️ База данных: {DB_CONFIG['database']}")
    
    db_connected = await bot.test_database_connection()
    
    if not db_connected:
        logger.error("❌ Не удалось подключиться к базе данных!")
        logger.error("⚠️  Проверьте:")

        logger.error("   - Правильность логина и пароля")
        logger.error("   - Активность базы данных на хостинге")
        logger.error("   - Разрешен ли доступ с вашего IP адреса")
        return None
    
    logger.info("✅ Все проверки пройдены успешно!")
    return bot

def main():
    """Запуск бота"""
    
    # Инициализируем бота с проверками
    bot_instance = asyncio.run(initialize_bot())
    
    if not bot_instance:
        logger.error("❌ Бот не может быть запущен из-за ошибок инициализации")
        return
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", bot_instance.start))
    application.add_handler(CommandHandler("login", bot_instance.login))
    application.add_handler(CommandHandler("grades", bot_instance.grades))
    application.add_handler(CommandHandler("homework", bot_instance.homework))
    application.add_handler(CommandHandler("schedule", bot_instance.schedule))
    application.add_handler(CommandHandler("profile", bot_instance.profile))
    application.add_handler(CommandHandler("unlink", bot_instance.unlink))
    application.add_handler(CommandHandler("help", bot_instance.help_command))
    
    # Обработчик inline кнопок
    application.add_handler(CallbackQueryHandler(bot_instance.button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_code_input))
    
    # Запускаем бота
    logger.info("🤖 Бот запущен...")
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
