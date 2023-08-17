import os
import logging
from http import HTTPStatus
import time
import telegram
import sys
import requests
from dotenv import load_dotenv

from exceptions import (Error, HTTPRequestError, APIError)

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


def send_message(bot, message):
    """Функция отправки сообщений."""
    try:
        logger.info('Message start sending')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logger.error(f'There is an exception: {error}')
    logging.debug('Сообщение отправлено!')


def get_api_answer(timestamp):
    """Получает ответ от API."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        raise APIError('Что то не так с запросом API, попробуйте снова!')
    if response.status_code != HTTPStatus.OK:
        raise HTTPRequestError('Эндроинт упал, попробуйте позже!')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info("API check")
    if not isinstance(response, dict):
        raise TypeError(f"API вернул ответ в виде {type(response)}, "
                        "должен быть словарь")
    params = ('current_date', 'homeworks')
    for key in params:
        if key not in response:
            message = f"В ответе API нет ключа {key}"
            raise KeyError(message)
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError(f"API вернул неправильный ответ {type(homework)}, "
                        "должен быть список")
    return homework


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if "homework_name" not in homework:
        raise KeyError(f'Нет ожидаемового ключа {homework}')
    status = homework['status']
    homework_name = homework['homework_name']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Не ожидаемый статус:{status}')
    return (f'Изменился статус проверки '
            f'работы "{homework_name}",{HOMEWORK_VERDICTS[status]}')


def check_tokens():
    """Проверяет доступность переменных окружения."""
    logger.info("Проверка доступности переменных окружения")
    return all((TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID))


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
                logger.debug("В ответе API отсутсвуют новые статусы")
            current_timestamp = int(time.time())
        except Exception as error:
            message_error = f'Сбой в работе программы: {error}'
            logger.error(message_error)
            if not issubclass(error.__class__, Error):
                if message_error != previous_message_error:
                    send_message(bot, message_error)
                    previous_message_error = message_error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
