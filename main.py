import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
import logging
import random
from datetime import datetime
from io import BytesIO

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "7773941080:AAGXI7bDR4XdWwnioFYRb76VNl4I3GWRL4M"
RAWG_API_KEY = "47b8e3967f25451f833e6f184ce09c31"
LOGS_DIR = "user_logs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def ensure_logs_dir():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)


def log_user_interaction(user_id: int, user_message: str, bot_response: str):
    log_filename = os.path.join(LOGS_DIR, f"{user_id}.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_filename, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] User: {user_message}\n")
        log_file.write(f"[{timestamp}] Bot: {bot_response}\n\n")


async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    welcome_text = (
        f"Привет, {user.first_name}!\n"
        "🎮 Я GameInfoBot - твой помощник в мире видеоигр!\n\n"
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/game_info <название> - найти информацию об игре\n"
        "/latest_news - последние игровые новости\n"
        "/top_games - топ игр в Steam\n"
        "/random_game - случайная популярная игра"
    )

    await update.message.reply_text(welcome_text)
    log_user_interaction(user.id, "/start", welcome_text)


async def game_info(update: Update, context: CallbackContext) -> None:
    user = update.effective_user

    if not context.args:
        response = "Пожалуйста, укажите название игры, например:\n/game_info The Witcher 3"
        await update.message.reply_text(response)
        log_user_interaction(user.id, "/game_info without args", response)
        return

    game_name = " ".join(context.args)
    url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&search={game_name}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("count", 0) > 0 and data.get("results"):
            game = data["results"][0]

            platforms = ", ".join(
                p["platform"]["name"]
                for p in game.get("platforms", [])[:3]
            ) if game.get("platforms") else "Неизвестно"

            message = (
                f"🎮 <b>{game.get('name', 'Без названия')}</b>\n"
                f"📅 Дата выхода: {game.get('released', 'Неизвестно')}\n"
                f"⭐ Рейтинг: {game.get('rating', 0):.1f}/5\n"
                f"🏆 Платформы: {platforms}\n"
                f"🔗 {game.get('website', 'Нет официального сайта')}"
            )

            if game.get("background_image"):
                try:
                    img_data = requests.get(game["background_image"], headers=HEADERS, timeout=10).content
                    photo_file = BytesIO(img_data)
                    photo_file.name = "game.jpg"

                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo_file,
                        caption=message,
                        parse_mode="HTML"
                    )
                except Exception as img_error:
                    logger.error(f"Image error: {img_error}")
                    await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text(message, parse_mode="HTML")

            log_user_interaction(user.id, f"/game_info {game_name}", "Success")
        else:
            response = f"Игра '{game_name}' не найдена. Попробуйте другое название."
            await update.message.reply_text(response)
            log_user_interaction(user.id, f"/game_info {game_name}", "Game not found")

    except Exception as e:
        logger.error(f"Error in game_info: {e}", exc_info=True)
        response = "Произошла ошибка при поиске игры. Попробуйте позже."
        await update.message.reply_text(response)
        log_user_interaction(user.id, f"/game_info {game_name}", f"Error: {str(e)}")

async def latest_news(update: Update, context: CallbackContext) -> None:
        user = update.effective_user

        try:
            NEWS_API_KEY = "b72c732b08604790bb76009caa6deb06"
            url = f"https://newsapi.org/v2/everything?q=gaming&language=ru&sortBy=publishedAt&apiKey={NEWS_API_KEY}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok" or not data.get("articles"):
                await update.message.reply_text("Не удалось загрузить новости. Попробуйте позже.")
                return

            news_items = []
            for article in data["articles"][:5]:
                title = article.get("title", "Без названия")
                url = article.get("url", "")
                if title and url:
                    news_items.append(f"• <a href='{url}'>{title}</a>")

            if news_items:
                message = "<b>🎮 Последние игровые новости:</b>\n\n" + "\n".join(news_items)
                await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
                log_user_interaction(user.id, "/latest_news", "Success")
            else:
                await update.message.reply_text("Новости не найдены.")
                log_user_interaction(user.id, "/latest_news", "No news found")

        except Exception as e:
            logger.error(f"Error in latest_news: {str(e)}", exc_info=True)
            await update.message.reply_text("Ошибка при получении новостей. Попробуйте позже.")
            log_user_interaction(user.id, "/latest_news", f"Error: {str(e)}")



async def top_games(update: Update, context: CallbackContext) -> None:
    user = update.effective_user

    try:
        url = "https://store.steampowered.com/api/featuredcategories"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data.get("top_sellers", {}).get("items"):
            await update.message.reply_text("Не удалось загрузить топ игр. Попробуйте позже.")
            return

        top_games = []
        for game in data["top_sellers"]["items"][:10]:
            name = game.get("name", "Без названия")

            final_price = game.get("final_price", 0) / 100
            original_price = game.get("original_price", 0) / 100
            discount = game.get("discount_percent", 0)

            if final_price > 0:
                price_text = f"{final_price:.2f}₽"
                if discount > 0:
                    price_text += f" (вместо {original_price:.2f}₽, -{discount}%)"
            else:
                price_text = "Бесплатно" if game.get("is_free", False) else "Цена не указана"

            top_games.append(f"• {name} - {price_text}")

        if top_games:
            message = "<b>🏆 Топ-10 игр в Steam:</b>\n\n" + "\n".join(top_games)
            await update.message.reply_text(message, parse_mode="HTML")
            log_user_interaction(user.id, "/top_games", "Success")
        else:
            await update.message.reply_text("Топ игр не найден.")
            log_user_interaction(user.id, "/top_games", "No games found")

    except Exception as e:
        logger.error(f"Error in top_games: {str(e)}", exc_info=True)
        await update.message.reply_text("Ошибка при получении топ-игр. Попробуйте позже.")
        log_user_interaction(user.id, "/top_games", f"Error: {str(e)}")


async def random_game(update: Update, context: CallbackContext) -> None:
    user = update.effective_user

    try:
        url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&ordering=-rating&page_size=50"
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("results"):
            game = random.choice(data["results"])

            platforms = ", ".join(
                p["platform"]["name"]
                for p in game.get("platforms", [])[:3]
            ) if game.get("platforms") else "Неизвестно"

            message = (
                "🎲 <b>Случайная игра из топа:</b>\n\n"
                f"🎮 <b>{game.get('name', 'Без названия')}</b>\n"
                f"📅 Дата выхода: {game.get('released', 'Неизвестно')}\n"
                f"⭐ Рейтинг: {game.get('rating', 0):.1f}/5\n"
                f"🖥️ Платформы: {platforms}\n"
                f"🔗 {game.get('website', 'Нет официального сайта')}"
            )

            if game.get("background_image"):
                try:
                    img_data = requests.get(game["background_image"], headers=HEADERS, timeout=10).content
                    photo_file = BytesIO(img_data)
                    photo_file.name = "game.jpg"

                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo_file,
                        caption=message,
                        parse_mode="HTML"
                    )
                except Exception as img_error:
                    logger.error(f"Image error: {img_error}")
                    await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text(message, parse_mode="HTML")

            log_user_interaction(user.id, "/random_game", "Success")
        else:
            response = "Не удалось получить список игр. Попробуйте позже."
            await update.message.reply_text(response)
            log_user_interaction(user.id, "/random_game", "No games found")

    except Exception as e:
        logger.error(f"Error in random_game: {e}", exc_info=True)
        response = "Произошла ошибка при выборе случайной игры. Попробуйте позже."
        await update.message.reply_text(response)
        log_user_interaction(user.id, "/random_game", f"Error: {str(e)}")


async def unknown(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    response = (
        "Извините, я не понимаю эту команду.\n"
        "Используйте /start для просмотра доступных команд."
    )
    await update.message.reply_text(response)
    log_user_interaction(user.id, update.message.text, response)


def main() -> None:
    ensure_logs_dir()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("game_info", game_info))
    application.add_handler(CommandHandler("latest_news", latest_news))
    application.add_handler(CommandHandler("top_games", top_games))
    application.add_handler(CommandHandler("random_game", random_game))

    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    application.run_polling()


if __name__ == "__main__":
    main()