import telebot
import sqlite3

bot = telebot.TeleBot('6197503153:AAHX9Yz5w1bpDs7v3KlplIye1hg9JVrFQlc')
# role = None
name = None
lastname = None
password = None
company = None
team = None
nickname = None


class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def create_table_user(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "lastname TEXT NOT NULL, password TEXT NOT NULL)")
        self.connection.commit()

    def add_user(self, message):
        try:
            self.cursor.execute("INSERT INTO users (id, name, lastname, password) VALUES (?, ?, ?, ?)",
                                (message.chat.id, name, lastname, password))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

        bot.send_message(message.chat.id, 'Ви зареєстровані!')

    def create_table_organizer(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS organizers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "lastname TEXT NOT NULL, password TEXT NOT NULL)")
        self.connection.commit()

    def add_user_organizer(self, message):
        try:
            self.cursor.execute("INSERT INTO organizers (id, name, lastname, password) VALUES (?, ?, ?, ?)",
                                (message.chat.id, name, lastname, password))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

        bot.send_message(message.chat.id, 'Ви зареєстровані!')

    def create_table_jury(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS jury (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "lastname TEXT NOT NULL, company TEXT, contest_id INTEGER, password TEXT NOT NULL)")
        self.connection.commit()

    def add_user_jury(self, message, check):
        try:
            if check:
                self.cursor.execute("INSERT INTO jury (id, name, lastname, company, password) VALUES (?, ?, ?, ?, ?)",
                                    (message.chat.id, name, lastname, company, password))
            else:
                self.cursor.execute("INSERT INTO jury (id, name, lastname, password) VALUES (?, ?, ?, ?)",
                                    (message.chat.id, name, lastname, password))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

        bot.send_message(message.chat.id, 'Ви зареєстровані!')

    def create_table_participant(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS participants (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "lastname TEXT NOT NULL, team TEXT NOT NULL, contest_id INTEGER, password TEXT NOT NULL)")
        self.connection.commit()

    def add_user_participant(self, message):
        try:
            self.cursor.execute("INSERT INTO participants (id, name, lastname, team, password) VALUES (?, ?, ?, ?, ?)",
                                (message.chat.id, name, lastname, team, password))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

        bot.send_message(message.chat.id, 'Ви зареєстровані!')

    def get_users(self):
        self.cursor.execute("SELECT * FROM users")
        return self.cursor.fetchall()

    def get_organizers(self):
        self.cursor.execute("SELECT * FROM organizers")
        return self.cursor.fetchall()

    def get_jury(self):
        self.cursor.execute("SELECT * FROM jury")
        return self.cursor.fetchall()

    def get_participants(self):
        self.cursor.execute("SELECT * FROM participants")
        return self.cursor.fetchall()


db = Database('test1.db')


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    bot.reply_to(message, 'Привіт! Я бот реєстрації користувачів для змагань. Для реєстрації введи /register')


@bot.message_handler(commands=['register'])
def handle_register(message):
    bot.reply_to(message, 'Введіть Ваше ім\'я')
    bot.register_next_step_handler(message, process_name_step)


def process_name_step(message):
    global name
    name = message.text
    bot.reply_to(message, 'Введіть Ваше прізвище')
    bot.register_next_step_handler(message, process_lastname_step)


def process_lastname_step(message):
    global lastname
    lastname = message.text
    bot.reply_to(message, 'Введіть пароль')
    bot.register_next_step_handler(message, process_password_step)


def process_password_step(message):
    global password
    password = message.text
    # bot.reply_to(message, 'Обери роль')
    markup = telebot.types.InlineKeyboardMarkup()
    user_button = telebot.types.InlineKeyboardButton('Користувач', callback_data='user')
    organizer_button = telebot.types.InlineKeyboardButton('Організатор', callback_data='organizer')
    jury_button = telebot.types.InlineKeyboardButton('Журі', callback_data='jury')
    participant_button = telebot.types.InlineKeyboardButton('Учасник', callback_data='participant')
    markup.add(user_button, organizer_button, jury_button, participant_button)
    bot.send_message(message.chat.id, 'Обери свою роль', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    if call.data == 'user':
        db.add_user(call.message)
    elif call.data == 'organizer':
        db.add_user_organizer(call.message)
    elif call.data == 'jury':
        db.add_user_jury(call.message, False)
    elif call.data == 'participant':
        db.add_user_participant(call.message)


# @bot.callback_query_handler(func=lambda call: call.data in ['users', 'organizers', 'jury', 'participants'])
# def handle_users_callback_query(call):
#     role = call.data
#     users = None
#     if role == 'users':
#         users = db.get_users()
#     elif role == 'organizers':
#         users = db.get_organizers()
#     elif role == 'jury':
#         users = db.get_jury()
#     elif role == 'participants':
#         users = db.get_participants()
#
#     info = 'Список користувачів::\n'
#     if users:
#         for u in users:
#             info += f'Ім\'я: {u[1]}, Прізвище: {u[2]}\n'
#     else:
#         info = 'No users found.'
#
#     bot.send_message(call.message.chat.id, info)


bot.polling()
