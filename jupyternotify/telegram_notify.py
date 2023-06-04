import os
import sys

import requests


def notify(message: str, api_key: str, chat_id: str) -> None:
    response = requests.post(
        'https://api.telegram.org/' +
        'bot{}/sendMessage'.format(api_key),
        params={'chat_id': chat_id, 'text': message},
        timeout=5
    )

    if response.status_code != 200:
        print(f'ERROR: could not send the notification successfully to telegram (ERROR: {response.status_code})')

def main():
    message = sys.argv[1]
    api_key = os.environ['TELEGRAM_API_KEY']
    chat_id = os.environ['TELEGRAM_CHAT_ID']

    notify(message, api_key, chat_id)


if __name__ == '__main__':
    main()