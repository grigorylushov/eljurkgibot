import os
import logging
import requests
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация - ИСПРАВЛЕННЫЙ ТОКЕН
BOT_TOKEN = "7994222730:AAGFUG52uZtk6H7M0FWwrWGZFKm0QxMKgEk"
API_BASE_URL = "https://eljurkgi.great-site.net/api/bot"
API_KEY = "your-secret-api-key-123"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

class EljurBot:
    def __init__(self):
        self.api_url = API_BASE_URL
        
    async def call_api(self, action, data):
        """Вызов API элжура"""
        try:
            payload = {"action": action, **data}
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
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
        user_info = await self.call_api('get_user_info', {
            'telegram_user_id': telegram_user_id
        })
        
        if user_info and user_info.get('is_linked'):
            user_data = user_info['user']
            message = (
                f"👋 Привет, {user_data['full_name']}!\n\n"
                f"✅ Ваш аккаунт Элжур привязан\n"
                f"🎯 Роль: {self.get_role_name(user_data['role'])}\n\n"
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
        
        # Генерируем код
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        message = (
            f"🔐 <b>Привязка аккаунта</b>\n\n"
            f"Чтобы привязать ваш Telegram к аккаунту Элжур:\n\n"
            f"1. Перейдите в ваш профиль на сайте\n"
            f"2. Найдите раздел \"Telegram бот\"\n"
            f"3. Введите этот код:\n\n"
            f"<code>{code}</code>\n\n"
            f"⏰ Код действителен 10 минут\n"
            f"🔒 После ввода кода ваш аккаунт будет автоматически привязан"
        )
        
        # Здесь должен быть код для сохранения code в базу через API
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def grades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ оценок"""
        user = update.effective_user
        telegram_user_id = user.id
        
        # Проверяем привязку
        user_info = await self.call_api('get_user_info', {
            'telegram_user_id': telegram_user_id
        })
        
        if not user_info or not user_info.get('is_linked'):
            await self.send_not_linked_message(update)
            return
        
        # Получаем оценки через API
        grades_data = await self.call_api('get_grades', {
            'telegram_user_id': telegram_user_id
        })
        
        if not grades_data:
            await update.message.reply_text("📊 Оценок пока нет")
            return
        
        message = "📊 <b>Последние оценки</b>\n\n"
        
        for grade in grades_data:
            emoji = self.get_grade_emoji(float(grade['grade']))
            student_name = grade.get('student_name', '')
            student_text = f" ({student_name})" if student_name else ""
            
            message += f"{emoji} <b>{grade['subject_name']}</b>{student_text}\n"
            message += f"Оценка: <b>{grade['grade']}</b> • {grade['date']}\n"
            
            if grade.get('comment'):
                message += f"💬 {grade['comment']}\n"
            
            message += "\n"
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="refresh_grades")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
    
    async def homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ домашних заданий"""
        user = update.effective_user
        telegram_user_id = user.id
        
        user_info = await self.call_api('get_user_info', {
            'telegram_user_id': telegram_user_id
        })
        
        if not user_info or not user_info.get('is_linked'):
            await self.send_not_linked_message(update)
            return
        
        homework_data = await self.call_api('get_homework', {
            'telegram_user_id': telegram_user_id
        })
        
        if not homework_data:
            await update.message.reply_text("📚 Активных заданий нет")
            return
        
        message = "📚 <b>Ближайшие задания</b>\n\n"
        
        for hw in homework_data:
            due_date = hw['due_date']
            days_left = self.get_days_until(due_date)
            days_text = self.get_days_text(days_left)
            
            if 'class_name' in hw:  # Для учителей
                message += f"👨‍🏫 <b>{hw['subject_name']}</b> - {hw['class_name']}\n"
            else:  # Для учеников
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
        
        user_info = await self.call_api('get_user_info', {
            'telegram_user_id': telegram_user_id
        })
        
        if not user_info or not user_info.get('is_linked'):
            await self.send_not_linked_message(update)
            return
        
        schedule_data = await self.call_api('get_schedule', {
            'telegram_user_id': telegram_user_id
        })
        
        if not schedule_data:
            await update.message.reply_text("📅 На сегодня занятий нет")
            return
        
        day_name = self.get_day_name()
        message = f"📅 <b>Расписание на сегодня</b>\n\n"
        message += f"📅 <b>{day_name}</b>\n\n"
        
        for lesson in schedule_data:
            start_time = lesson['start_time'][:5]
            end_time = lesson['end_time'][:5]
            
            message += f"🕒 <b>{start_time} - {end_time}</b>\n"
            message += f"📚 {lesson['subject_name']}\n"
            message += f"👨‍🏫 {lesson['teacher_name']}\n"
            
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
        
        user_info = await self.call_api('get_user_info', {
            'telegram_user_id': telegram_user_id
        })
        
        if not user_info or not user_info.get('is_linked'):
            await self.send_not_linked_message(update)
            return
        
        user_data = user_info['user']
        message = (
            f"👤 <b>Информация о профиле</b>\n\n"
            f"👤 <b>{user_data['full_name']}</b>\n"
            f"🎯 Роль: <b>{self.get_role_name(user_data['role'])}</b>\n"
            f"📧 Логин: <code>{user_data['username']}</code>\n"
        )
        
        if user_data.get('email'):
            message += f"📨 Email: {user_data['email']}\n"
        
        if user_data.get('last_login'):
            message += f"🕒 Последний вход: {user_data['last_login']}\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def unlink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отвязка аккаунта"""
        user = update.effective_user
        telegram_user_id = user.id
        
        result = await self.call_api('unlink_account', {
            'telegram_user_id': telegram_user_id
        })
        
        if result:
            message = "✅ Аккаунт успешно отвязан"
        else:
            message = "❌ Ошибка при отвязке аккаунта"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
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
        
        # Создаем фиктивный update для вызова соответствующих методов
        class MockUpdate:
            def __init__(self, query):
                self.callback_query = query
                self.effective_user = query.from_user
                self.message = query.message
        
        mock_update = MockUpdate(query)
        
        action = query.data
        
        if action == "refresh_grades":
            await self.grades(mock_update, context)
        elif action == "refresh_homework":
            await self.homework(mock_update, context)
        elif action == "refresh_schedule":
            await self.schedule(mock_update, context)
    
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
        
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text(message, parse_mode='HTML')
        elif hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text(message, parse_mode='HTML')
    
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
            due_date = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now()
            return (due_date - today).days
        except ValueError:
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
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("login", bot.login))
    application.add_handler(CommandHandler("grades", bot.grades))
    application.add_handler(CommandHandler("homework", bot.homework))
    application.add_handler(CommandHandler("schedule", bot.schedule))
    application.add_handler(CommandHandler("profile", bot.profile))
    application.add_handler(CommandHandler("unlink", bot.unlink))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
