from __future__ import print_function

import telebot
from google.oauth2 import service_account

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

bot = telebot.TeleBot('6197503153:AAHX9Yz5w1bpDs7v3KlplIye1hg9JVrFQlc')

CREDENTIALS_FILE = 'credentials2.json'


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    markup = telebot.types.InlineKeyboardMarkup()
    title = 'project1'
    link_button = telebot.types.InlineKeyboardButton("Get Spreadsheet Link", callback_data='get_link')
    markup.add(link_button)
    bot.send_message(message.chat.id,
                     'Click the button to get the link to an empty Google Spreadsheet', reply_markup=markup)


def create(title, message):
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    try:
        service = build('sheets', 'v4', credentials=creds)
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = spreadsheet.get("spreadsheetId")

        drive = build("drive", "v3", credentials=creds)
        permission = {
            "type": "anyone",
            "role": "writer",
        }
        drive.permissions().create(fileId=spreadsheet_id, body=permission).execute()

        link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=0"
        bot.send_message(message.chat.id, f"Here's the link to the empty table: {link}")
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    create('project1', call.message)


bot.polling()
