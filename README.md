# Flash Telegram Bot

Telegram бот для мастера по наращиванию ресниц с системой отзывов и управления расписанием.

## 🚀 Установка

### Deploy на Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/ZrCwYh?referralCode=U4r7qg)

1. Нажмите кнопку выше
2. Установите переменные окружения:
   - `TELEGRAM_TOKEN` - токен от @BotFather
   - `MASTER_PASSWORD` - пароль для доступа мастера
3. Бот готов к работе

### Локальная установка

```bash
git clone <your-repo>
cd beauty-master-bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

pip install -r requirements.txt

# Создайте .env файл
echo "TELEGRAM_TOKEN=your_token_here" > .env
echo "MASTER_PASSWORD=your_password_here" >> .env

python bot.py
```

## ⚙️ Переменные окружения

**Обязательные:**
- `TELEGRAM_TOKEN` - токен бота
- `MASTER_PASSWORD` - пароль мастера

**Опциональные:**
- `MASTER_CONTACT` - контакты для записи
- `WEBHOOK_URL` - для Railway деплоя

## 📁 Структура

```
bot.py
requirements.txt
.price_photo/     # прайс-листы
.records/         # расписание  
.welcome/         # приветственное фото
.reviews/         # отзывы
  └── backups/    # резервные копии
```

## 💡 Функции

**Для клиентов:**
- Просмотр прайса
- Запись к мастеру  
- Просмотр свободных мест
- Оставление отзывов

**Для мастера:**
- Обновление прайса
- Управление расписанием
- Просмотр статистики отзывов
- Удаление отзывов

## 🔧 Технологии

- Python + pyTelegramBotAPI
- Flask для вебхуков
- JSON для хранения данных
- Railway для деплоя
