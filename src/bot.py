import os
import telebot 
from telebot.types import ReplyKeyboardRemove
from telebot import types
import time
from flask import Flask, request 
import json
from datetime import datetime

# ==================== КОНФИГУРАЦИЯ ПЕРЕМЕННЫХ RAILWAY ====================
# Получаем переменные из окружения Railway с fallback значениями
TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
MASTER_PASSWORD = os.environ.get('MASTER_PASSWORD', 'default_password')
MASTER_CONTACT = os.environ.get('MASTER_CONTACT', 'Контакты не настроены')

# Настройки сервера
PORT = int(os.environ.get('PORT', 5000))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
RAILWAY_ENVIRONMENT = os.environ.get('RAILWAY_ENVIRONMENT', 'production')


# ==================== ПРОВЕРКА ПЕРЕМЕННЫХ ====================
def validate_environment_variables():
    """Проверка обязательных переменных окружения"""
    missing_vars = []
    
    if not TOKEN:
        missing_vars.append('TELEGRAM_TOKEN')
    if not MASTER_PASSWORD:
        missing_vars.append('MASTER_PASSWORD')
    
    if missing_vars:
        print(f"❌ Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
        print("💡 Установите их в настройках Railway:")
        return False
    
    print("✅ Все обязательные переменные настроены")
    return True

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
bot = telebot.TeleBot(token=TOKEN, threaded=True)
app = Flask(__name__)


PRICE_DIR = "price_photo"
os.makedirs(PRICE_DIR, exist_ok=True)

REVIEWS_DIR = "reviews"
os.makedirs(REVIEWS_DIR, exist_ok=True)
FLASH_DIR = "welcome"
os.makedirs(FLASH_DIR, exist_ok=True)

RECORDS_DIR = "records"
os.makedirs(RECORDS_DIR, exist_ok=True)

REVIEWS_FILE = os.path.join(REVIEWS_DIR, "reviews.json")

BACKUP_DIR = os.path.join(REVIEWS_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def get_environment_info():
    """Получение информации о среде выполнения"""
    return {
        'environment': RAILWAY_ENVIRONMENT,
        'webhook_url': WEBHOOK_URL,
        'port': PORT
    }

def setup_webhook():
    """Настройка вебхука для Railway"""
    if WEBHOOK_URL:
        try:
            bot.remove_webhook()
            time.sleep(1)
            webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
            bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook установлен: {webhook_url}")
            return True
        except Exception as e:
            print(f"❌ Ошибка настройки webhook: {e}")
            return False
    else:
        print("ℹ️ WEBHOOK_URL не установлен, используем polling")
        return False

def start_polling():
    """Запуск polling с обработкой ошибок"""
    while True:
        try:
            print("🔄 Запуск бота в режиме polling...")
            bot.polling(none_stop=True, timeout=30, long_polling_timeout=10)
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)

# ==================== FLASK ROUTES ====================
@app.route('/')
def home():
    """Корневой маршрут для проверки работы"""
    env_info = get_environment_info()
    return f"""
    <h1>🤖</h1>
    <p><strong>Статус:</strong> ✅ Работает</p>
    <p><strong>Среда:</strong> {env_info['environment']}</p>
    <p><strong>Webhook:</strong> {env_info['webhook_url'] or 'Не используется'}</p>
    <p><strong>Версия:</strong> 1.0</p>
    <hr>
    <p><a href="/env">Просмотр переменных окружения</a></p>
    <p><a href="/health">Проверка здоровья</a></p>
    """

@app.route('/env')
def show_environment():
    """Показать переменные окружения (без чувствительных данных)"""
    env_info = get_environment_info()
    return {
        'bot_name': env_info['bot_name'],
        'environment': env_info['environment'],
        'webhook_enabled': bool(WEBHOOK_URL),
        'max_reviews_per_page': env_info['max_reviews'],
        'backup_retention_days': env_info['backup_retention_days'],
        'master_contact_configured': bool(MASTER_CONTACT)
    }

@app.route('/health')
def health_check():
    """Health check для Railway"""
    try:
        # Проверяем доступность основных директорий
        required_dirs = [PRICE_DIR, REVIEWS_DIR, RECORDS_DIR, BACKUP_DIR]
        dirs_status = all(os.path.exists(dir_path) for dir_path in required_dirs)
        
        # Проверяем наличие основных файлов
        files_status = all([
            os.path.exists(REVIEWS_FILE) or not reviews_list,
            True  # Фото файлы могут отсутствовать изначально
        ])
        
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "directories": dirs_status,
            "files": files_status,
            "reviews_count": len(reviews_list),
            "environment": RAILWAY_ENVIRONMENT
        }
        
        return status, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Обработчик вебхука для Railway"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'OK'


# Функция для загрузки отзывов
def load_reviews():
    try:
        with open(REVIEWS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Функция для сохранения отзывов
def save_reviews(reviews):
    with open(REVIEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)

master_list = []

master_data = {}
user_data = {}
reviews_list = load_reviews()
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Клиент")
    btn2 = types.KeyboardButton("Мастер")
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id, "Здравствуйте, выберете роль", reply_markup=markup)

@bot.message_handler(func=lambda message:message.text == "Мастер")
def password_request(message):
    password = bot.send_message(message.chat.id, "Авторизируйтесь", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(password, masterauto)
def masterauto(message):
    password = message.text
    if password == MASTER_PASSWORD:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn = types.KeyboardButton("🏠 Зайти в меню мастера")
        markup.add(btn)
        bot.send_message(message.chat.id, "Успешно" ,reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Авторизация не пройдена")
        start(message)

@bot.message_handler(func=lambda message:message.text == "🏠 Зайти в меню мастера")
def master_menu(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("💸 Установить прайс")
        btn2 = types.KeyboardButton("✍️ Обновить свободные места")
        btn3 = types.KeyboardButton("📅 Посмотреть текущие свободные места и прайс")
        btn4 = types.KeyboardButton("⭐️ Отзывы")
        markup.add(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(message.chat.id, "Выберите действие", reply_markup=markup)

@bot.message_handler(func=lambda message:message.text == "✍️ Обновить свободные места")
def request_place(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("🏠 Выйти в меню мастера")
    markup.add(btn)
    msg = bot.send_message(message.chat.id, "Отправьте фото с обновленными местами или выйдите в меню мастера", reply_markup=markup)
    bot.register_next_step_handler(msg, process_request_place)
def process_request_place(message):
    if message.text == "🏠 Выйти в меню мастера":
        master_menu(message)
    else:
        place(message)

@bot.message_handler(content_types=['photo'])
def place(message):
    try:
        if message.photo:
            # Получаем фото с наилучшим качеством (последний элемент в списке)
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Фиксированное имя файла
            file_extension = file_info.file_path.split('.')[-1]
            filename = f"place.{file_extension}"  # Полностью фиксированное имя
            file_path = os.path.join(RECORDS_DIR, filename)
            
            # Удаляем старое фото если оно существует
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Удалено старое фото: {filename}")
                except Exception as e:
                    print(f"Ошибка при удалении старого фото: {e}")
            
            # Сохраняем новое фото
            with open(file_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            # Обновляем информацию в master_data
            # Теперь храним только одно фото для всех
            master_data['current_place'] = {
                'filename': filename,
                'file_path': file_path,
                'timestamp': message.date,
                'set_by': message.from_user.id
            }
            
            bot.reply_to(message, "✅ Места обновлены")
            master_menu(message)
        else:
            bot.reply_to(message, "❌ Пожалуйста, отправьте фото.")
            master_menu(message)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при сохранении фото: {str(e)}")
        master_menu(message)


@bot.message_handler(func=lambda message:message.text == "📅 Посмотреть текущие свободные места и прайс")
def see(message):
    with open('records/place.jpg', 'rb') as photo1:
        bot.send_photo(message.chat.id, photo1, "📅 Текущие свободные места")
    with open('price_photo/price.jpg', 'rb') as photo2:
            bot.send_photo(message.chat.id, photo2, "Текущий прайс 💸")
    master_menu(message)

@bot.message_handler(func=lambda message:message.text == "💸 Установить прайс")
def request_price(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("🏠 Выйти в меню мастера")
    markup.add(btn)
    msg = bot.send_message(message.chat.id, "Отправьте фото с прайсом или выйдите в меню мастера", reply_markup=markup)
    bot.register_next_step_handler(msg, process_request_price)

def process_request_price(message):
    if message.text == "🏠 Выйти в меню мастера":
        master_menu(message)
    else:
        price(message)

@bot.message_handler(content_types=['photo'])
def price(message):
    try:
        if message.photo:
            # Получаем фото с наилучшим качеством (последний элемент в списке)
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Фиксированное имя файла
            file_extension = file_info.file_path.split('.')[-1]
            filename = f"price.{file_extension}"  # Полностью фиксированное имя
            file_path = os.path.join(PRICE_DIR, filename)
            
            # Удаляем старое фото если оно существует
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Удалено старое фото: {filename}")
                except Exception as e:
                    print(f"Ошибка при удалении старого фото: {e}")
            
            # Сохраняем новое фото
            with open(file_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            # Обновляем информацию в master_data
            # Теперь храним только одно фото для всех
            master_data['current_price'] = {
                'filename': filename,
                'file_path': file_path,
                'timestamp': message.date,
                'set_by': message.from_user.id
            }
            
            bot.reply_to(message, "✅ Прайс установлен")
            master_menu(message)
        else:
            bot.reply_to(message, "❌ Пожалуйста, отправьте фото.")
            master_menu(message)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при сохранении фото: {str(e)}")
        master_menu(message)

@bot.message_handler(func=lambda message: message.text == "⭐️ Отзывы")
def master_reviews_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📊 Статистика отзывов")
    btn2 = types.KeyboardButton("📝 Посмотреть все отзывы")
    btn3 = types.KeyboardButton("🏠 Выйти в меню мастера")
    btn4 = types.KeyboardButton("🗑️ Удалить все отзывы")
    markup.add(btn1, btn2)
    markup.row(btn4)
    markup.row(btn3)
    
    total_reviews = len(reviews_list)
    if total_reviews > 0:
        avg_rating = sum(r.get('rating', 5) for r in reviews_list) / total_reviews
        bot.send_message(
            message.chat.id,
            f"📊 У вас {total_reviews} отзывов\n"
            f"⭐ Средний рейтинг: {avg_rating:.1f}/5",
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "📝 У вас пока нет отзывов", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🏠 Выйти в меню мастера")
def back_master(message):
    master_menu(message)
@bot.message_handler(func=lambda message: message.text == "📊 Статистика отзывов")
def show_statistics(message):
    if not reviews_list:
        bot.send_message(message.chat.id, "📝 Отзывов пока нет")
        master_reviews_menu(message)
        return
    
    total = len(reviews_list)
    rating_counts = {1:0, 2:0, 3:0, 4:0, 5:0}
    
    for review in reviews_list:
        rating = review.get('rating', 5)
        rating_counts[rating] = rating_counts.get(rating, 0) + 1
    
    stats_text = f"📊 **Статистика отзывов:**\n\n"
    stats_text += f"📝 Всего отзывов: {total}\n"
    
    if any(review.get('rating') for review in reviews_list):
        avg_rating = sum(r.get('rating', 5) for r in reviews_list) / total
        stats_text += f"⭐ Средний рейтинг: {avg_rating:.1f}/5\n\n"
        
        for rating in range(5, 0, -1):
            count = rating_counts[rating]
            percentage = (count / total) * 100
            stats_text += f"{'⭐' * rating}: {count} ({percentage:.1f}%)\n"
    
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')
    master_reviews_menu(message)





@bot.message_handler(func=lambda message: message.text == "📝 Посмотреть все отзывы")
def see_rating(message):
    if not reviews_list:  
        bot.send_message(message.chat.id, "📝 Отзывов пока нет")
        master_reviews_menu(message)
        return
    
    for i, review in enumerate(reversed(reviews_list), 1):  # Новые первыми
        user_name = review.get('user_name', 'Аноним')
        rating = review.get('rating', 5)
        text = review.get('text', '')
        date = review.get('date', 'Неизвестно')
        
        review_text = (
            f"**Отзыв #{i}**\n"
            f"⭐ Оценка: {rating}/5\n"
            f"💬 {text}\n"
            f"👤 {user_name}\n"
            f"📅 {date}\n"
            f"────────────────────"
        )
        
        bot.send_message(message.chat.id, review_text, parse_mode='Markdown')
    
    # После показа всех отзывов возвращаем в меню
    master_reviews_menu(message)

@bot.message_handler(func=lambda message: message.text == "🗑️ Удалить все отзывы")
def request_delete_all_reviews(message):
    if not reviews_list:
        bot.send_message(message.chat.id, "📝 Нет отзывов для удаления")
        master_reviews_menu(message)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("✅ Да, удалить все")
    btn2 = types.KeyboardButton("❌ Нет, отменить")
    markup.add(btn1, btn2)
    
    bot.send_message(
        message.chat.id,
        f"⚠️ **ВНИМАНИЕ!**\n\n"
        f"Вы собираетесь удалить ВСЕ отзывы ({len(reviews_list)} шт.).\n"
        f"Это действие нельзя отменить!\n\n"
        f"Вы уверены?",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "✅ Да, удалить все")
def confirm_delete_all_reviews(message):
    # Создаем резервную копию перед удалением
    backup_file = os.path.join(BACKUP_DIR, f"reviews_backup_{int(time.time())}.json")
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(reviews_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка создания бэкапа: {e}")
    
    # Сохраняем количество отзывов для сообщения
    deleted_count = len(reviews_list)
    
    # Очищаем список
    reviews_list.clear()
    save_reviews(reviews_list)
    
    bot.send_message(
        message.chat.id,
        f"✅ Удалено {deleted_count} отзывов\n"
        f"📁 Создана резервная копия: {backup_file}",
        reply_markup=ReplyKeyboardRemove()
    )
    master_reviews_menu(message)

@bot.message_handler(func=lambda message: message.text == "❌ Нет, отменить")
def cancel_delete_reviews(message):
    bot.send_message(
        message.chat.id,
        "❌ Удаление отменено",
        reply_markup=ReplyKeyboardRemove()
    )
    master_reviews_menu(message)


@bot.message_handler(func=lambda message:message.text == "Клиент")
def client(message):
    with open('welcome/flash.jpg', 'rb') as photo:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn = types.KeyboardButton("🏠 Зайти в главное меню")
        markup.add(btn)
        bot.send_photo(message.chat.id, photo, "Добро пожаловать", reply_markup=markup) 
@bot.message_handler(func=lambda message:message.text == "🏠 Зайти в главное меню")
def client_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("💸 Ознакомиться с прайсом")
    btn2 = types.KeyboardButton("✍️ Записаться на ресницы")
    btn3 = types.KeyboardButton("⭐️ Оставить отзыв")
    btn4 = types.KeyboardButton("📅 Свободные места")
    markup.add(btn1)
    markup.row(btn4)
    markup.row(btn2)
    markup.row(btn3)
    bot.send_message(message.chat.id, "Выберите действие", reply_markup=markup)

@bot.message_handler(func=lambda message:message.text == "💸 Ознакомиться с прайсом")
def learn_price(message):
    with open('price_photo/price.jpg', 'rb') as photo:
        bot.send_photo(message.chat.id, photo)
    client_menu(message)    

@bot.message_handler(func=lambda message:message.text == "📅 Свободные места")
def see_place(message):
    with open('records/place.jpg', 'rb') as photo:
        bot.send_photo(message.chat.id, photo, "Текущая информация может быть не акутальна, при записи уточните")
    client_menu(message)

@bot.message_handler(func=lambda message:message.text == "✍️ Записаться на ресницы")
def sign_up(message):
    bot.send_message(message.chat.id, f"Держите контакты мастера, для записи☺️:{MASTER_CONTACT}")
    client_menu(message)



@bot.message_handler(func=lambda message: message.text == "⭐️ Оставить отзыв")
def request_review(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🏠 Отмена")
    markup.add(btn1)
    
    # Создаем инлайн-клавиатуру для оценки
    rating_markup = types.InlineKeyboardMarkup(row_width=5)
    ratings = []
    for i in range(1, 6):
        ratings.append(types.InlineKeyboardButton("⭐" * i, callback_data=f"rating_{i}"))
    rating_markup.add(*ratings)
    
    bot.send_message(
        message.chat.id, 
        "📝 Оцените работу мастера от 1 до 5 звезд:",
        reply_markup=markup
    )
    bot.send_message(message.chat.id, "Выберите оценку:", reply_markup=rating_markup)

@bot.message_handler(func=lambda message:message.text == "🏠 Отмена")
def back_client_menu(message):
    client_menu(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rating_"))
def process_rating(call):
    rating = int(call.data.split("_")[1])
    user_data[call.from_user.id] = {'rating': rating}
    
    bot.edit_message_text(
        f"✅ Вы поставили {rating} ⭐\n\nТеперь напишите текстовый отзыв:",
        call.message.chat.id,
        call.message.message_id
    )
    
    msg = bot.send_message(call.message.chat.id, "💬 Ваш отзыв:")
    bot.register_next_step_handler(msg, process_review_with_rating)

def process_review_with_rating(message):
    user_id = message.from_user.id
    if user_id not in user_data or 'rating' not in user_data[user_id]:
        client_menu(message)
        return
    
    rating = user_data[user_id]['rating']
    
    review = {
        'user_id': user_id,
        'user_name': f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip(),
        'rating': rating,
        'text': message.text,
        'date': datetime.now().strftime("%d.%m.%Y %H:%M"),
        'timestamp': time.time()
    }
    

    reviews_list.append(review)
    save_reviews(reviews_list)
    
    # Очищаем временные данные
    if user_id in user_data:
        del user_data[user_id]
    
    bot.send_message(
        message.chat.id, 
        f"✅ Спасибо за ваш отзыв ({rating}⭐)! Он очень важен для нас!",
        reply_markup=ReplyKeyboardRemove()
    )
    client_menu(message)

bot.polling(non_stop=True)
# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
def run_bot():
    """Запуск бота в зависимости от среды"""
    print("🚀 Запуск бота...")
    print(f"🔑 Токен: {'✅' if TOKEN else '❌'}")
    print(f"🌐 Среда: {RAILWAY_ENVIRONMENT}")
    
    # Проверяем обязательные переменные
    if not validate_environment_variables():
        print("❌ Не могу запустить бота без обязательных переменных")
        return
    
    # Создаем необходимые директории
    required_dirs = [PRICE_DIR, REVIEWS_DIR, FLASH_DIR, RECORDS_DIR]
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"📁 Создана папка: {dir_path}")
    
    # Запускаем в зависимости от среды
    if WEBHOOK_URL and setup_webhook():
        print("🌐 Запуск в режиме WEBHOOK")
        app.run(host='0.0.0.0', port=PORT, debug=False)
    else:
        print("🔄 Запуск в режиме POLLING")
        start_polling()

if __name__ == '__main__':
    run_bot()
