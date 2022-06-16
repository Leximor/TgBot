import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (FailAnswerConnectionError, IncorrectMessageError,
                        NoResponseReceivedError, WrongAPIAnswerError)

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

TRY_MSG = 'Попытка {what}{where}'
TRY_SEND_MSG = 'отправки сообщения '
FAIL_ERROR_MSG = 'Сбой. Ошибка: {error}'
SUCCEED_TRY_MSG = 'Удачная попытка {what}.'


def send_message(bot, message):
    """Функция отправки сообщения в чат."""
    logging.info(TRY_MSG.format(what=TRY_SEND_MSG, where='в чат'))
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except IncorrectMessageError as error:
        error_msg = (FAIL_ERROR_MSG.format(error=error))
        logging.error(error_msg)
        raise(error_msg)
    else:
        logging.info(SUCCEED_TRY_MSG.format(what=TRY_SEND_MSG))


def get_api_answer(current_timestamp):
    """Функция get_api_answer проверяет API Ya.Practicum на доступность."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': current_timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            error_msg = FAIL_ERROR_MSG.format(error=response.status_code)
            logging.error(error_msg)
            raise NoResponseReceivedError(error_msg)
    except requests.exceptions.RequestException as status_code:
        error_msg = FAIL_ERROR_MSG.format(error=status_code)
        logging.error(error_msg)
        raise ConnectionError(error_msg)
    except requests.exceptions.ConnectionError as status_code:
        error_msg = FAIL_ERROR_MSG.format(error=status_code)
        raise FailAnswerConnectionError(error_msg)
    return response.json()


def check_response(api_dict):
    """Функция проверяет наличие и статус домашней работы."""
    if not isinstance(api_dict, dict):
        error_msg = FAIL_ERROR_MSG.format(
            error='На вход функции ожидается словарь')
        logging.error(error_msg)
        raise TypeError(error_msg)
    if not api_dict.get('current_date'):
        error_msg = FAIL_ERROR_MSG.format(
            error='current_date is None')
        logging.error(error_msg)
        raise TypeError(error_msg)
    if api_dict.get('homeworks') is None:
        error_msg = FAIL_ERROR_MSG.format(
            error='homeworks is None')
        logging.error(error_msg)
        raise TypeError(error_msg)
    homeworks = api_dict.get('homeworks')
    if not isinstance(homeworks, list):
        error_msg = FAIL_ERROR_MSG.format(
            error='Ожидается, что '
                  '"homeworks" будет списком!')
        logging.error(error_msg)
        raise TypeError(error_msg)
    if not homeworks:
        info_msg = FAIL_ERROR_MSG.format(error='Не обнаружено последного ДЗ')
        logging.info(info_msg)
    return homeworks


def parse_status(last_homework):
    """Функция проверяет, изменился ли статус домашней работы."""
    logging.info('Проверка, изменился ли статус домашней работы.')
    status = last_homework.get('status')
    homework_name = last_homework.get('homework_name')
    if status is None:
        error_msg = FAIL_ERROR_MSG.format(error='В ДЗ нет значения status')
        logging.error(error_msg)
        raise WrongAPIAnswerError(error_msg)
    if last_homework is None:
        error_msg = FAIL_ERROR_MSG.format(
            error='В ДЗ нет значения homework_name')
        logging.error(error_msg)
        raise WrongAPIAnswerError(error_msg)
    status_from_dict = HOMEWORK_STATUSES[status]
    send_status = ('Изменился статус '
                   'проверки работы "{}". {}'.format(
                       homework_name, status_from_dict))
    logging.info(send_status)
    return (send_status)


def check_tokens():
    """Функция проверки доступности Токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная функция опроса API Ya.Practicum."""
    tokens = check_tokens()
    if not tokens:
        error_msg = FAIL_ERROR_MSG.format(
            error='Не обнаружена одна или несколько '
            'переменных оркужения: '
            'PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID !')
        logging.critical(error_msg)
        raise sys.exit(error_msg)
    prev_report = ''
    current_report = ''
    current_timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            api_dict = get_api_answer(current_timestamp)
            homeworks = check_response(api_dict)
            if homeworks:
                current_report = 'Список ДЗ пуст !'
                logging.info(current_report)
            else:
                last_homework = homeworks[0]
                current_report = parse_status(last_homework)
            if current_report != prev_report:
                send_message(bot, current_report)
                prev_report = current_report
            logging.DEBUG('отсутствие в ответе новых статусов')
        except Exception as error:
            current_report = f'Сбой в работе программы: {error}'
            logging.error(error, exc_info=True)
            if current_report != prev_report:
                send_message(bot, current_report)
                prev_report = current_report
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.INFO,
        format=('%(asctime)s, '
                '%(levelname)s, '
                '%(name)s, '
                'Function:"%(funcName)s",'
                'Line:"%(lineno)s", '
                'Description: "%(message)s"'),
        handlers=[
            logging.FileHandler("main.log", "a", encoding="UTF-8"),
            logging.StreamHandler()
        ]
    )
    main()
