import json
import logging
import os
import time

from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import InvalidAPI, TokenError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'praktikum_HW.log',
    maxBytes=50000000,
    backupCount=5)

logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s -  %(levelname)s - %(message)s')
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено')
    except telegram.TelegramError:
        logger.info('Ошибка отправки сообщения')


def get_api_answer(current_timestamp):
    """Ответ API сервера."""
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise InvalidAPI('Ошибка ответа API сервера')
        try:
            api_answer = homework_statuses.json()
            return api_answer
        except json.decoder.JSONDecodeError as json_error:
            logger.error('Ошибка преобразования')
            raise json_error
    except ConnectionError as conn_error:
        logger.error('Ошибка соединения')
        raise conn_error


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Запрос не соответвует формату')
    homework = response.get('homeworks')
    if homework is None:
        raise KeyError('Нет ключа homeworks')
    if not isinstance(homework, list):
        raise TypeError('Ответ не является списком')
    return homework


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if isinstance(homework, dict):
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_name is None:
            raise KeyError('Нет данных о имени работы')
        elif homework_status is None:
            raise KeyError('Нет данных о статусе работы')
        verdict = HOMEWORK_STATUSES.get(homework_status)
        if verdict is None:
            raise KeyError('Ошибка статуса работы')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise TypeError('В ответ пришёл не словарь')


def check_tokens():
    """Проверка доступности токенов."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        if PRACTICUM_TOKEN is None:
            logger.critical(f'Ошибка токена {PRACTICUM_TOKEN}')
        if TELEGRAM_TOKEN is None:
            logger.critical(f'Ошибка токена {TELEGRAM_TOKEN}')
        if TELEGRAM_CHAT_ID is None:
            logger.critical(f'Ошибка токена {TELEGRAM_CHAT_ID}')
    return False


def main():
    """Основная логика работы бота."""
    error_text = ''
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - RETRY_TIME
    if not check_tokens():
        raise TokenError('Ошибка проверки токена')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            for work in homework:
                message = parse_status(work)
                send_message(bot, message)
                current_timestamp = response.get(
                    'current_date', int(time.time()))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if error_text != message:
                send_message(bot, message)
                logger.error(message)
                error_text = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
