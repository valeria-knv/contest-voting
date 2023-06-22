import telebot
import sqlite3

bot = telebot.TeleBot('6197503153:AAHX9Yz5w1bpDs7v3KlplIye1hg9JVrFQlc')
role = None
name = None
lastname = None
password = None
company = None
team = None
nickname = None
check = False


class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def create_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
        self.connection.commit()

    def add_user(self, message):
        try:
            self.cursor.execute("INSERT INTO users (id) VALUES (?)", (message.chat.id,))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def user_exists(self, message):
        try:
            result = self.cursor.execute("SELECT * FROM users WHERE id = ?", (message.chat.id,)).fetchall()
            return bool(result)
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_organizer(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS organizers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "lastname TEXT NOT NULL, password TEXT NOT NULL)")
        self.connection.commit()

    def add_user_organizer(self, message):
        try:
            self.cursor.execute("INSERT INTO organizers (id, name, lastname, password) VALUES (?, ?, ?, ?)",
                                (message.chat.id, name, lastname, password))
            self.connection.commit()
            bot.send_message(message.chat.id, 'Ви зареєстровані!')
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_jury(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS jury (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "lastname TEXT NOT NULL, company TEXT, contest_id INTEGER, password TEXT NOT NULL)")
        self.connection.commit()

    def add_user_jury(self, message):
        try:
            if check:
                self.cursor.execute("INSERT INTO jury (id, name, lastname, company, password) VALUES (?, ?, ?, ?, ?)",
                                    (message.chat.id, name, lastname, company, password))
            else:
                self.cursor.execute("INSERT INTO jury (id, name, lastname, password) VALUES (?, ?, ?, ?)",
                                    (message.chat.id, name, lastname, password))
            self.connection.commit()
            bot.send_message(message.chat.id, 'Ви зареєстровані!')
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_participant(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS participants (id INTEGER PRIMARY KEY, team TEXT NOT NULL, contest_id INTEGER, password TEXT NOT NULL)")
        self.connection.commit()

    def add_user_participant(self, message):
        try:
            self.cursor.execute("INSERT INTO participants (id, team, password) VALUES (?, ?, ?)",
                                (message.chat.id, team, password))
            self.connection.commit()
            bot.send_message(message.chat.id, 'Ви зареєстровані!')
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_viewer(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS viewer (id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, "
                            "password TEXT NOT NULL)")
        self.connection.commit()

    def add_user_viewer(self, message):
        try:
            self.cursor.execute("INSERT INTO viewer (id, nickname, password) VALUES (?, ?, ?)",
                                (message.chat.id, nickname, password))
            self.connection.commit()
            bot.send_message(message.chat.id, 'Ви зареєстровані!')
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

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

    def get_viewer(self):
        self.cursor.execute("SELECT * FROM viewer")
        return self.cursor.fetchall()


db = Database('test1.db')


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    db.create_table()
    if db.user_exists(message):
        bot.send_message(message.chat.id, 'Ви вже зареєстровані!')
    else:
        bot.reply_to(message, 'Привіт! Я бот реєстрації користувачів для конкурсів. Для реєстрації введіть /register')


@bot.message_handler(commands=['register'])
def handle_register(message):
    db.create_table()
    if db.user_exists(message):
        bot.send_message(message.chat.id, 'Ви вже зареєстровані!')
    else:
        db.add_user(message)
        markup = telebot.types.InlineKeyboardMarkup()
        user_button = telebot.types.InlineKeyboardButton('Глядач', callback_data='viewer')
        organizer_button = telebot.types.InlineKeyboardButton('Організатор', callback_data='organizer')
        jury_button = telebot.types.InlineKeyboardButton('Журі', callback_data='jury')
        participant_button = telebot.types.InlineKeyboardButton('Учасник', callback_data='participant')
        markup.add(user_button, organizer_button, jury_button, participant_button)
        bot.send_message(message.chat.id, 'Обери свою роль', reply_markup=markup)


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


def process_company_step(message):
    global company
    company = message.text
    add(message)


def process_team_step(message):
    global team
    team = message.text
    bot.reply_to(message, 'Введіть пароль')
    bot.register_next_step_handler(message, process_password_step)


def process_nickname_step(message):
    global nickname
    nickname = message.text
    bot.reply_to(message, 'Введіть пароль')
    bot.register_next_step_handler(message, process_password_step)


def process_password_step(message):
    global password
    global role
    password = message.text
    if role == 'jury':
        markup = telebot.types.InlineKeyboardMarkup()
        yes_button = telebot.types.InlineKeyboardButton('Так', callback_data='yes')
        no_button = telebot.types.InlineKeyboardButton('Ні', callback_data='no')
        markup.add(yes_button, no_button)
        bot.send_message(message.chat.id, 'Ви представляєте якусь компанію?', reply_markup=markup)
    else:
        add(message)


def add(message):
    global role
    if role == 'viewer':
        db.add_user_viewer(message)
    elif role == 'organizer':
        db.add_user_organizer(message)
    elif role == 'jury':
        db.add_user_jury(message)
    elif role == 'participant':
        db.add_user_participant(message)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global role
    global check
    if call.data == 'viewer':
        role = 'viewer'
        db.create_table_viewer()
        bot.send_message(call.message.chat.id, 'Введіть Ваш нікнейм.')
        bot.register_next_step_handler(call.message, process_nickname_step)
    elif call.data == 'organizer':
        role = 'organizer'
        db.create_table_organizer()
        bot.send_message(call.message.chat.id, 'Введіть Ваше ім\'я!')
        bot.register_next_step_handler(call.message, process_name_step)
    elif call.data == 'jury':
        role = 'jury'
        db.create_table_jury()
        bot.send_message(call.message.chat.id, 'Введіть Ваше ім\'я!')
        bot.register_next_step_handler(call.message, process_name_step)
    elif call.data == 'participant':
        role = 'participant'
        db.create_table_participant()
        bot.send_message(call.message.chat.id, 'Введіть команду, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_team_step)
    elif call.data == 'yes':
        check = True
        bot.send_message(call.message.chat.id, 'Введіть компанію, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_company_step)
    elif call.data == 'no':
        add(call.message)


bot.polling()
