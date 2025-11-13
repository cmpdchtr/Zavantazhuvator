# 🚀 Налаштування локального Bot API Server

Локальний Bot API Server дозволяє завантажувати файли до **2 ГБ** замість стандартних 50 МБ!

## 📋 Вимоги

- Docker (рекомендовано) або Linux сервер
- Telegram API ID та API Hash
- Ваш бот токен

## 🐳 Метод 1: Docker (Найпростіше)

### Крок 1: Отримайте API ID та API Hash

1. Відкрийте https://my.telegram.org/auth
2. Увійдіть у свій акаунт Telegram
3. Перейдіть у "API development tools"
4. Створіть додаток і збережіть:
   - `api_id` (число)
   - `api_hash` (рядок)

### Крок 2: Запустіть Bot API Server через Docker

```bash
docker run -d \
  --name telegram-bot-api \
  -p 8081:8081 \
  -e TELEGRAM_API_ID=YOUR_API_ID \
  -e TELEGRAM_API_HASH=YOUR_API_HASH \
  -v $(pwd)/telegram-bot-api-data:/var/lib/telegram-bot-api \
  aiogram/telegram-bot-api:latest
```

Замініть:
- `YOUR_API_ID` - ваш API ID
- `YOUR_API_HASH` - ваш API Hash

### Крок 3: Налаштуйте бота

У файлі `.env` додайте:

```env
BOT_API_SERVER="http://localhost:8081"
```

### Крок 4: Запустіть бота

```bash
python main.py
```

Ви побачите:
```
Using local Bot API server: http://localhost:8081
File size limit: up to 2 GB
```

## 💻 Метод 2: Встановлення на Linux сервері

### Крок 1: Встановіть залежності

```bash
sudo apt-get update
sudo apt-get install -y \
  make git zlib1g-dev libssl-dev gperf cmake g++
```

### Крок 2: Клонуйте та зберіть Bot API

```bash
git clone --recursive https://github.com/tdlib/telegram-bot-api.git
cd telegram-bot-api
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --target install
```

### Крок 3: Запустіть сервер

```bash
telegram-bot-api --api-id=YOUR_API_ID \
  --api-hash=YOUR_API_HASH \
  --local
```

### Крок 4: Налаштуйте бота

У файлі `.env`:

```env
BOT_API_SERVER="http://localhost:8081"
```

## 🌐 Метод 3: Віддалений сервер (VPS)

Якщо ви встановили Bot API на VPS:

```env
BOT_API_SERVER="http://YOUR_SERVER_IP:8081"
```

Або з HTTPS:

```env
BOT_API_SERVER="https://bot-api.yourdomain.com"
```

## ✅ Перевірка роботи

Після запуску бота надішліть `/start` - ви побачите:

```
📊 Статус: Локальний Bot API Server
📦 Ліміт файлів: 2 ГБ 🚀
```

## 🔧 Налаштування Docker Compose (Рекомендовано для постійної роботи)

Створіть `docker-compose.yml`:

```yaml
version: '3.8'

services:
  telegram-bot-api:
    image: aiogram/telegram-bot-api:latest
    container_name: telegram-bot-api
    restart: unless-stopped
    environment:
      - TELEGRAM_API_ID=YOUR_API_ID
      - TELEGRAM_API_HASH=YOUR_API_HASH
    ports:
      - "8081:8081"
    volumes:
      - ./telegram-bot-api-data:/var/lib/telegram-bot-api
```

Запустіть:

```bash
docker-compose up -d
```

## 📊 Переваги локального Bot API Server

✅ **Файли до 2 ГБ** замість 50 МБ
✅ **Швидша швидкість** завантаження
✅ **Більше контролю** над API
✅ **Локальне зберігання** файлів
✅ **Менше обмежень** від Telegram

## ⚠️ Важливі примітки

1. **Порт 8081** повинен бути відкритий
2. **API ID та Hash** отримуються з https://my.telegram.org
3. **Дані зберігаються локально** у `telegram-bot-api-data/`
4. **Бот працюватиме** і без локального API (з лімітом 50 МБ)

## 🐛 Проблеми?

**Бот не підключається до локального API:**
- Перевірте, чи працює Docker контейнер: `docker ps`
- Перевірте логи: `docker logs telegram-bot-api`
- Переконайтесь, що порт 8081 відкритий

**Все одно ліміт 50 МБ:**
- Перевірте `.env` файл - чи вказано `BOT_API_SERVER`
- Перезапустіть бота
- Перевірте логи при запуску бота

## 📚 Додаткові ресурси

- [Офіційна документація Telegram Bot API](https://core.telegram.org/bots/api)
- [GitHub репозиторій Bot API](https://github.com/tdlib/telegram-bot-api)
- [Docker образ aiogram](https://hub.docker.com/r/aiogram/telegram-bot-api)

---

**Готово!** Тепер ваш бот може завантажувати файли до 2 ГБ! 🎉
