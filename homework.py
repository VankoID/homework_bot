import os
import logging
import time
import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import InvalidAPI

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

logging.basicConfig(
    level=logging.DEBUG,
    filename='praktikum_HW.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def send_message(bot, message):
    """Отправка сообщения пользователю."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Ответ API сервера."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT,
                                     headers=HEADERS,
                                     params=params)
    if homework_statuses.status_code != HTTPStatus.OK:
        raise InvalidAPI('Ошибка ответа API сервера')
    api_answer = homework_statuses.json()
    return api_answer


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Запрос не соответвует формату')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Нет ключа homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Ответ не является списком')
    return homeworks


def parse_status(homework):
    """Провеерка статуса домащней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None and homework_status is None:
        raise KeyError('Нет данных о работе')
    else:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        if verdict is None:
            raise KeyError('Ошибка статуса работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical('Ошибка токенов')
        return True
    return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            response = check_response(response)
            if len(response) > 0:
                homework_status = parse_status(response[0])
                if homework_status is None:
                    send_message(bot, homework_status)
            else:
                logging.debug('Новых статусов нет')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)

        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
