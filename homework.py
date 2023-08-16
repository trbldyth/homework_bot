import os
import logging
from http import HTTPStatus
import time
import telegram
import sys
import requests
from dotenv import load_dotenv

from exceptions import (Error)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
fileHandler = logging.FileHandler("logfile.log", encoding='utf-8')
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger.setLevel(logging.INFO)
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.addHandler(fileHandler)


class APIError(Exception):
    """Исключение в API."""

    pass


class HTTPRequestError(Exception):
    """Исключение в HTTP."""

    pass


def send_message(bot, message):
    """Функция для отправки сообщений."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logger.error(f'There is an exception: {error}')
    logging.debug('Message was sent!')


def get_api_answer(timestamp):
    """Функция,получающая ответ от API."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        logger.error('There is an error at API request')
        raise APIError('Something wrong with API request, try again!')
    if response.status_code != HTTPStatus.OK:
        logger.error('Endpoint isnt OK!')
        raise HTTPRequestError('Endpoint isnt OK,try later')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info("API check")
    if not isinstance(response, dict):
        message = (f"API returns answer like {type(response)}, "
                   "but need to be a dict")
        raise TypeError(message)
    params = ['current_date', 'homeworks']
    for key in params:
        if key not in response:
            message = f"There is no key {key} in API answer"
            raise KeyError(message)
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        message = (f"API returns {type(homework)} with homeworks key, "
                   "but need to be a list")
        raise TypeError(message)
    return homework


def parse_status(homework):
    """Функция проверки статуса домашней работы."""
    if "homework_name" not in homework:
        raise KeyError(f'There is no expected key in {homework}')
    status = homework['status']
    homework_name = homework['homework_name']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Not expected status:{status}')
    message = (f'Status check changed: '
               f'"{homework_name}",{HOMEWORK_VERDICTS[status]}')
    return message


def check_tokens():
    """Проверяет доступность переменных окружения."""
    logger.info("Проверка доступности переменных окружения")
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = ("Доступны не все переменные окружения, которые "
                   "необходимы для работы программы: "
                   "PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID")
        logger.critical(message)
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_message_error = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                logger.debug("There is no new statuses")
            current_timestamp = int(time.time())
        except Exception as error:
            message_error = f'Program Error: {error}'
            logger.error(message_error)
            if not issubclass(error.__class__, Error):
                if message_error != previous_message_error:
                    send_message(bot, message_error)
                    previous_message_error = message_error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
