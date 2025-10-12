import os
import logging
import requests
import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import pymysql
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "7994222730:AAGFUG52uZtk6H7M0FWwrWGZFKm0QxMKgEk"
API_BASE_URL = "https://eljurkgi.great-site.net/api/bot"

# Настройки базы данных
DB_CONFIG = {
    'host': 'sql307.infinityfree.com',
    'user': 'if0_39061882',
    'password': 'jpX9rbOg91WR9e9',
    'database': 'if0_39061882_eljur',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

class EljurBot:
    def __init__(self):
        self.api_url = API_BASE_URL
        
    def get_db_connection(self):
        """Создание соединения с базой данных"""
        try:
            return pymysql.connect(**DB_CONFIG)
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
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
        connection = self.get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    # Создаем временную запись о привязке
                    sql = """
                    INSERT INTO telegram_bindings 
                    (telegram_user_id, telegram_username, telegram_first_name, telegram_last_name, bind_code, bind_code_expires)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    bind_code = VALUES(bind_code), 
                    bind_code_expires = VALUES(bind_code_expires),
                    is_active = 0
                    """
                    cursor.execute(sql, (
                        user.id,
                        user.username,
                        user.first_name,
                        user.last_name,
                        code,
                        expires_at
                    ))
                connection.commit()
                
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
                
            except Exception as e:
                logger.error(f"Error saving bind code: {e}")
                await update.message.reply_text(
                    "❌ Ошибка при генерации кода. Попробуйте позже.",
                    parse_mode='HTML'
                )
            finally:
                connection.close()
        else:
            await update.message.reply_text(
                "❌ Ошибка подключения к базе данных.",
                parse_mode='HTML'
            )
    
    async def handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода кода привязки"""
        user = update.effective_user
        code = update.message.text.upper().strip()
        
        connection = self.get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    # Проверяем код
                    sql = """
                    SELECT * FROM telegram_bindings 
                    WHERE bind_code = %s AND bind_code_expires > %s AND is_active = 0
                    """
                    cursor.execute(sql, (code, datetime.now()))
                    binding = cursor.fetchone()
                    
                    if binding:
                        # Активируем привязку
                        sql = """
                        UPDATE telegram_bindings 
                        SET is_active = 1, linked_at = %s, bind_code = NULL, bind_code_expires = NULL
                        WHERE bind_code = %s
                        """
                        cursor.execute(sql, (datetime.now(), code))
                        connection.commit()
                        
                        # Получаем информацию о пользователе
                        sql = """
                        SELECT u.* FROM users u
                        INNER JOIN telegram_bindings tb ON u.id = tb.user_id
                        WHERE tb.bind_code = %s
                        """
                        cursor.execute(sql, (code,))
                        user_info = cursor.fetchone()
                        
                        if user_info:
                            message = (
                                f"✅ <b>Аккаунт успешно привязан!</b>\n\n"
                                f"👤 {user_info['full_name']}\n"
                                f"🎯 {self.get_role_name(user_info['role'])}\n\n"
                                f"Теперь вы можете использовать все функции бота!"
                            )
                        else:
                            message = "✅ Аккаунт успешно привязан!"
                            
                        await update.message.reply_text(message, parse_mode='HTML')
                    else:
                        await update.message.reply_text(
                            "❌ Неверный или просроченный код. Попробуйте снова.",
                            parse_mode='HTML'
                        )
                        
            except Exception as e:
                logger.error(f"Error processing bind code: {e}")
                await update.message.reply_text(
                    "❌ Ошибка при обработке кода. Попробуйте позже.",
                    parse_mode='HTML'
                )
            finally:
                connection.close()
    
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
        
        for grade in grades_data[:10]:  # Показываем последние 10 оценок
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
        
        for hw in homework_data[:5]:  # Показываем 5 ближайших заданий
            due_date = hw['due_date']
            days_left = self.get_days_until(due_date)
            days_text = self.get_days_text(days_left)
            
            if user_info['role'] == 'teacher':
                message += f"👨‍🏫 <b>{hw['subject_name']}</b> - {hw['class_name']}\n"
            else:
                message += f"📖 <b>{hw['subject_name']}</b>\n"
                if hw.get('teacher_name'):
                    message += f"👨‍🏫 {hw['teacher_name']}\n"
            
            message += f"📝 <b>{hw['title']}</b>\n"
            message += f"⏰ До: <b>{due_date}</b> ({days_text})\n"
            
            if hw.get('description'):
                desc = hw['description'][:80] + "..." if len(hw['description']) > 80 else hw['description']
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
            start_time = lesson.get('start_time', '--:--')[:5]
            end_time = lesson.get('end_time', '--:--')[:5]
            
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
            last_login = user_info['last_login'].strftime('%d.%m.%Y %H:%M') if isinstance(user_info['last_login'], datetime) else user_info['last_login']
            message += f"🕒 Последний вход: {last_login}\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def unlink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отвязка аккаунта"""
        user = update.effective_user
        telegram_user_id = user.id
        
        connection = self.get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    sql = "UPDATE telegram_bindings SET is_active = 0, unlinked_at = %s WHERE telegram_user_id = %s AND is_active = 1"
                    cursor.execute(sql, (datetime.now(), telegram_user_id))
                    connection.commit()
                    
                    if cursor.rowcount > 0:
                        message = "✅ Аккаунт успешно отвязан!"
                    else:
                        message = "❌ Аккаунт не был привязан"
                
                await update.message.reply_text(message, parse_mode='HTML')
                
            except Exception as e:
                logger.error(f"Error unlinking account: {e}")
                await update.message.reply_text("❌ Ошибка при отвязке аккаунта", parse_mode='HTML')
            finally:
                connection.close()
        else:
            await update.message.reply_text("❌ Ошибка подключения к базе данных", parse_mode='HTML')
    
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
        connection = self.get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    sql = """
                    SELECT u.* FROM users u
                    INNER JOIN telegram_bindings tb ON u.id = tb.user_id
                    WHERE tb.telegram_user_id = %s AND tb.is_active = 1
                    """
                    cursor.execute(sql, (telegram_user_id,))
                    return cursor.fetchone()
            except Exception as e:
                logger.error(f"Error getting user by telegram ID: {e}")
                return None
            finally:
                connection.close()
        return None
    
    async def get_user_grades(self, user_id):
        """Получение оценок пользователя"""
        connection = self.get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    sql = """
                    SELECT g.*, s.name as subject_name, t.full_name as teacher_name
                    FROM grades g
                    LEFT JOIN subjects s ON g.subject_id = s.id
                    LEFT JOIN users t ON g.teacher_id = t.id
                    WHERE g.student_id = %s
                    ORDER BY g.date DESC, g.id DESC
                    LIMIT 20
                    """
                    cursor.execute(sql, (user_id,))
                    return cursor.fetchall()
            except Exception as e:
                logger.error(f"Error getting user grades: {e}")
                return None
            finally:
                connection.close()
        return None
    
    async def get_user_homework(self, user_id, role):
        """Получение домашних заданий"""
        connection = self.get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
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
                        cursor.execute(sql, (user_id,))
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
                        cursor.execute(sql, (user_id,))
                    return cursor.fetchall()
            except Exception as e:
                logger.error(f"Error getting user homework: {e}")
                return None
            finally:
                connection.close()
        return None
    
    async def get_user_schedule(self, user_id, role):
        """Получение расписания"""
        connection = self.get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
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
                        cursor.execute(sql, (user_id, day_name))
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
                        cursor.execute(sql, (user_id, day_name))
                    return cursor.fetchall()
            except Exception as e:
                logger.error(f"Error getting user schedule: {e}")
                return None
            finally:
                connection.close()
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
            if isinstance(date_str, str):
                due_date = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                due_date = date_str
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

def main():
    """Запуск бота"""
    bot = EljurBot()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("login", bot.login))
    application.add_handler(CommandHandler("grades", bot.grades))
    application.add_handler(CommandHandler("homework", bot.homework))
    application.add_handler(CommandHandler("schedule", bot.schedule))
    application.add_handler(CommandHandler("profile", bot.profile))
    application.add_handler(CommandHandler("unlink", bot.unlink))
    application.add_handler(CommandHandler("help", bot.help_command))
    
    # Обработчик inline кнопок
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Обработчик текстовых сообщений (для кодов привязки)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_code_input))
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
