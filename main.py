from __future__ import print_function

import telebot
import sqlite3
from datetime import date, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

bot = telebot.TeleBot('6197503153:AAHX9Yz5w1bpDs7v3KlplIye1hg9JVrFQlc')

role = None
name = None
lastname = None
password = None
company = None
team = None
nickname = None
check = False
contest_name = None
start_date = None
end_date = None
max_organizers = 1

project_type = None
custom_criteria_count = None

default_startup_criteria = [
    'Актуальність і соціальна значимість проєкту',
    'Детальне технічне опрацювання проєкту',
    'Конкретність, значимість і досяжність результатів проєкту',
    'Реалістичність і обґрунтованість представленого проєкту',
    'Економічна ефективність',
    'Інвестиційна привабливість проєкту'
]

default_design_criteria = [
    'Композиція',
    'Кольорова гама',
    'Чистота виконаної роботи',
    'Деталізація',
    'Перспектива',
    'Актуальність',
    'Складність',
    'Креативність',
    'Презентація',
    'Оригінальність'
]

current_criteria = []
criterion_index = 0

CREDENTIALS_FILE = 'credentials2.json'


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

    def create_table_criteria(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS criteria (id INTEGER, name TEXT, contest_id INTEGER, PRIMARY KEY(id, contest_id))")
        self.connection.commit()

    def set_name_criteria(self, message, criteria, crit_id):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("INSERT INTO criteria (id, name, contest_id) VALUES (?, ?, ?)", (crit_id, criteria, contest_id))
        self.connection.commit()

    def create_table_contest(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS contests (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "start_date TEXT NOT NULL, end_date TEXT NOT NULL, max_organizers INTEGER DEFAULT 1, "
                            "registration_started INTEGER DEFAULT 0, voting_started INTEGER DEFAULT 0)")
        self.connection.commit()

    def start_registration(self):
        contest_id_row = self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            self.cursor.execute("UPDATE contests SET registration_started = 1 WHERE id = ?", (contest_id,))
            self.connection.commit()

    def end_registration(self):
        contest_id_row = self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            self.cursor.execute("UPDATE contests SET registration_started = 0 WHERE id = ?", (contest_id,))
            self.connection.commit()

    def start_voting(self):
        contest_id_row = self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            self.cursor.execute("UPDATE contests SET voting_started = 1 WHERE id = ?", (contest_id,))
            self.connection.commit()

    def add_contest(self):
        self.cursor.execute("INSERT INTO contests (name, start_date, end_date, max_organizers) VALUES (?, ?, ?, ?)",
                            (contest_name, start_date, end_date, max_organizers))
        self.connection.commit()

    def get_contest_id(self):
        return self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)).fetchone()[0]

    def get_active_contests(self):
        self.cursor.execute("SELECT id, name, start_date FROM contests WHERE start_date < date('now') AND end_date > date('now') AND registration_started = 1")
        return self.cursor.fetchall()

    def get_number_organizer_of_contest(self):
        contest_id_row = self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            result = self.cursor.execute("SELECT id FROM organizers WHERE contest_id = ?", (contest_id,)).fetchall()
            return len(result)
        else:
            return 0

    def get_max_organizers(self):
        return self.cursor.execute("SELECT max_organizers FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)).fetchone()[0]

    def user_exists(self, message):
        try:
            result = self.cursor.execute("SELECT * FROM users WHERE id = ?", (message.chat.id,)).fetchall()
            return bool(result)
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_organizer(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS organizers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
                            "lastname TEXT NOT NULL, password TEXT NOT NULL, contest_id INTEGER)")
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
                            "password TEXT NOT NULL, contest_id INTEGER)")
        self.connection.commit()

    def add_user_viewer(self, message):
        try:
            self.cursor.execute("INSERT INTO viewer (id, nickname, password) VALUES (?, ?, ?)",
                                (message.chat.id, nickname, password))
            self.connection.commit()
            bot.send_message(message.chat.id, 'Ви зареєстровані!')
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def set_id_organizer(self, message, contest_id):
        self.cursor.execute("UPDATE organizers SET contest_id = ? WHERE id = ?", (contest_id, message.chat.id))
        self.connection.commit()

    def set_id_jury(self, message, contest_id):
        self.cursor.execute("UPDATE jury SET contest_id = ? WHERE id = ?", (contest_id, message.chat.id))
        self.connection.commit()

    def set_id_participant(self, message, contest_id):
        self.cursor.execute("UPDATE participants SET contest_id = ? WHERE id = ?", (contest_id, message.chat.id))
        self.connection.commit()

    def set_id_viewer(self, message, contest_id):
        self.cursor.execute("UPDATE viewer SET contest_id = ? WHERE id = ?", (contest_id, message.chat.id))
        self.connection.commit()

    def is_organizer(self, message):
        return bool(self.cursor.execute("SELECT id FROM organizers WHERE id = ?", (message.chat.id,)))

    def get_registration_status(self):
        return bool(self.cursor.execute("SELECT registration_status FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)))

    def get_jury_contest(self, message):
        return bool(self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)))

    def get_participant_contest(self, message):
        return bool(self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)))

    def delete_from_users(self, message):
        self.cursor.execute("DELETE FROM users WHERE id = ?", (message.chat.id,))
        self.connection.commit()

    def get_id_jury_from_contest(self, message):
        contest_id_row = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            return self.cursor.execute("SELECT id FROM jury WHERE contest_id = ?", (contest_id,)).fetchall()
        else:
            return 0

    def get_id_participants_from_contest(self, message):
        contest_id_row = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            return self.cursor.execute("SELECT id FROM participants WHERE contest_id = ?", (contest_id,)).fetchall()
        else:
            return 0

    def get_number_of_participants(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT COUNT(id) FROM participants WHERE contest_id = ?", (contest_id,)).fetchone()[0]

    def get_number_of_criteria(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT COUNT(id) FROM criteria WHERE contest_id = ?", (contest_id,)).fetchone()[0]

    def get_number_of_jury(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT COUNT(id) FROM jury WHERE contest_id = ?", (contest_id,)).fetchone()[0]

    def get_list_of_participants(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT team FROM participants WHERE contest_id = ?", (contest_id,)).fetchall()

    def get_list_of_criteria(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT name FROM criteria WHERE contest_id = ?", (contest_id,)).fetchall()

    def get_list_of_jury(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT lastname FROM jury WHERE contest_id = ?", (contest_id,)).fetchall()


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


@bot.message_handler(commands=['startregistration'])
def handle_start_registration(message):
    start_registration(message)


@bot.message_handler(commands=['startvoting'])
def handle_start_voting(message):
    start_voting(message)


@bot.message_handler(commands=['criteria'])
def handle_start_voting(message):
    start_criteria(message)


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
    process_contest_step(message)


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


def process_contest_step(message):
    active_contests = db.get_active_contests()
    if len(active_contests) > 0:
        markup = telebot.types.InlineKeyboardMarkup()
        for contest in active_contests:
            contest_button = telebot.types.InlineKeyboardButton(contest[1], callback_data=f'join_contest_{contest[0]}')
            markup.add(contest_button)
        bot.send_message(message.chat.id, 'Оберіть конкурс, до якого хочете приєднатись:', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, 'Наразі немає активних конкурсів. Тому Ви не можете зареєструватись!')
        db.delete_from_users(message)


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
    elif role == 'organizer':
        organizer_add_contest(message)
    else:
        process_contest_step(message)


def organizer_add_contest(message):
    markup = telebot.types.InlineKeyboardMarkup()
    add_contest_button = telebot.types.InlineKeyboardButton('Додати конкурс', callback_data='add_contest')
    join_contest_button = telebot.types.InlineKeyboardButton('Приєднатись', callback_data='join_contest')
    markup.add(add_contest_button, join_contest_button)
    bot.send_message(message.chat.id, 'Ви зареєстровані як організатор. Додайте конкурс чи приєднайтесь до існуючого конкурсу:', reply_markup=markup)


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


def process_contest_name_step(message):
    global contest_name
    contest_name = message.text
    bot.reply_to(message, 'Введіть дату початку конкурсу у форматі "рік-місяць-день".')
    bot.register_next_step_handler(message, process_start_date_step)


def process_start_date_step(message):
    global start_date
    start_date = message.text
    bot.reply_to(message, 'Введіть дату закінчення конкурсу у форматі "рік-місяць-день".')
    bot.register_next_step_handler(message, process_end_date_step)


def process_end_date_step(message):
    global end_date
    end_date = message.text
    bot.reply_to(message, 'Введіть кількість організаторів, які можуть приєднатись до конкурсу:')
    bot.register_next_step_handler(message, process_max_organizers_step)


def process_max_organizers_step(message):
    global max_organizers
    try:
        max_organizers = int(message.text)
        add_contest(message)
    except ValueError:
        bot.send_message(message.chat.id, 'Невірне значення кількості організаторів!')
        process_max_organizers_step(message)


def add_contest(message):
    db.create_table_contest()
    db.add_contest()
    contest_id = db.get_contest_id()
    db.add_user_organizer(message)
    bot.send_message(message.chat.id, 'Конкурс додано!')
    db.set_id_organizer(message, contest_id)
    start_registration(message)


def check_date(message):
    global start_date
    global end_date

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date_obj > date.today() or end_date_obj < date.today():
        bot.send_message(message.chat.id, 'Ви не можете зробити цю дію, бо сьогоднішній день не входить в проміжок конкурсу, який ви визначили!')
        return False
    else:
        return True


def start_registration(message):
    markup = telebot.types.InlineKeyboardMarkup()
    if not check_date(message):
        return
    start_registration_button = telebot.types.InlineKeyboardButton('Почати реєстрацію', callback_data='start_registration')
    dont_start_registration_button = telebot.types.InlineKeyboardButton('Пізніше', callback_data='dont_start_registration')
    markup.add(start_registration_button, dont_start_registration_button)
    bot.send_message(message.chat.id, 'Чи хочете Ви почати реєстрацію для жюрі та учасників?', reply_markup=markup)


def opportunity_join():
    number = db.get_max_organizers()
    length = db.get_number_organizer_of_contest()
    if number <= length:
        return False
    return True


def add_criteria(message):
    markup = telebot.types.InlineKeyboardMarkup()
    start_button = telebot.types.InlineKeyboardButton('Додати критерії', callback_data='add_criteria')
    no_start_button = telebot.types.InlineKeyboardButton('Пізніше', callback_data='dont_add_criteria')
    markup.add(start_button, no_start_button)
    bot.send_message(message.chat.id, 'Чи хочете Ви додати критерії?', reply_markup=markup)


def start_criteria(message):
    markup = telebot.types.InlineKeyboardMarkup()
    startup_button = telebot.types.InlineKeyboardButton('Критерії стартапу', callback_data='process_startup_criteria')
    design_button = telebot.types.InlineKeyboardButton('Критерії дизайну', callback_data='process_design_criteria')
    create_button = telebot.types.InlineKeyboardButton('Створити нові', callback_data='create_criteria')
    markup.add(startup_button, design_button, create_button)
    bot.send_message(message.chat.id, 'Налаштуйте критерії конкурсу:', reply_markup=markup)


def criteria_as_string(criteria):
    return "\n".join([f"{i + 1}. {cri_name};" for i, cri_name in enumerate(criteria)])


def show_current_criteria(message, criteria):
    markup = telebot.types.InlineKeyboardMarkup()
    leave_button = telebot.types.InlineKeyboardButton('Залишити поточні', callback_data='leave_criteria')
    change_button = telebot.types.InlineKeyboardButton('Змінити', callback_data='change_criteria')
    create_button = telebot.types.InlineKeyboardButton('Створити нові', callback_data='create_criteria')
    markup.add(leave_button, change_button, create_button)
    bot.send_message(message.chat.id, 'Поточні критерії: \n\n' + criteria_as_string(criteria) + '\n\nЧи влаштовують вони Вас?', reply_markup=markup)


def request_count_of_criteria(message):
    global current_criteria
    current_criteria = []
    bot.reply_to(message, 'Введіть кількість критеріїв:')
    bot.register_next_step_handler(message, save_count_of_criteria)


def save_count_of_criteria(message):
    global custom_criteria_count
    try:
        custom_criteria_count = int(message.text)
        if custom_criteria_count <= 0:
            raise
    except ValueError:
        bot.reply_to(message, 'Вказана кількість критеріїв не валідна, спробуйте ще раз:')
        bot.register_next_step_handler(message, save_count_of_criteria)
        return

    ask_criterion(message)


def ask_criterion(message):
    global criterion_index
    msg = bot.send_message(message.chat.id, f'Введіть критерій під номером {criterion_index + 1}:')
    bot.register_next_step_handler(msg, save_criterion)


def save_criterion(message):
    global criterion_index
    global current_criteria
    current_criteria += [message.text]

    criterion_index += 1
    msg = bot.send_message(message.chat.id, f'Критерій збережено: \n{criterion_index}. {message.text}')
    if criterion_index == custom_criteria_count:
        criterion_index = 0
        show_current_criteria(msg, current_criteria)
    else:
        ask_criterion(message)


def request_criteria_number(message):
    global current_criteria
    msg = bot.send_message(message.chat.id, f'Введіть номер критерію, який хочете змінити:')
    bot.register_next_step_handler(msg, get_new_criterion_value)


def get_new_criterion_value(message):
    global current_criteria
    global criterion_index
    try:
        criterion_index = int(message.text)
        if criterion_index - 1 >= len(current_criteria) or criterion_index - 1 < 0:
            raise
    except ValueError:
        bot.reply_to(message, 'Вказаний номер критерію не валідний, спробуйте ще раз:')
        bot.register_next_step_handler(message, get_new_criterion_value)
        return

    bot.reply_to(message, f'Введіть нове значення для критерію за номером {criterion_index}:')
    bot.register_next_step_handler(message, set_new_value_to_criterion)


def set_new_value_to_criterion(message):
    global current_criteria
    global criterion_index
    current_criteria[criterion_index - 1] = message.text
    msg = bot.send_message(message.chat.id, f'Критерій збережено: \n{criterion_index}. {message.text}')
    criterion_index = 0
    show_current_criteria(msg, current_criteria)


def add_criteria_to_db(message):
    global current_criteria
    i = 0
    for criteria in current_criteria:
        i += 1
        db.set_name_criteria(message, str(criteria), i)
    start_voting(message)


def start_voting(message):
    markup = telebot.types.InlineKeyboardMarkup()
    if not check_date(message):
        return
    start_registration_button = telebot.types.InlineKeyboardButton('Почати голосування', callback_data='start_voting')
    dont_start_registration_button = telebot.types.InlineKeyboardButton('Пізніше', callback_data='dont_start_voting')
    markup.add(start_registration_button, dont_start_registration_button)
    bot.send_message(message.chat.id, 'Чи хочете Ви почати конкурсне голосування?', reply_markup=markup)


def send_messages(message):
    # ids_jury = db.get_id_jury_from_contest(message)
    # ids_participants = db.get_id_participants_from_contest(message)
    # for id_jury in ids_jury:
    #     bot.send_message(int(id_jury[0]), 'Голосування почалось!')
    # for id_part in ids_participants:
    #     bot.send_message(int(id_part[0]), 'Голосування почалось!')
    create('contest voting', message)


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
        add_value_to_sheet(message, link, spreadsheet_id, service)
        bot.send_message(message.chat.id, f"Посилання на Google таблицю: {link}")
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error


def add_value_to_sheet(message, link, spreadsheet_id, service):
    number_of_participants = db.get_number_of_participants(message)
    number_of_criteria = db.get_number_of_criteria(message)
    number_of_jury = db.get_number_of_jury(message)

    list_of_participants = db.get_list_of_participants(message)
    list_of_criteria = db.get_list_of_criteria(message)
    list_of_jury = db.get_list_of_jury(message)
    data = []

    temp = 1
    start_col = 2
    start_row = 1
    data = [
        {
            'range': f"{chr(start_col + 64)}{start_row}",
            'values': [list_of_participants[0]]
        }
    ]
    for i in range(number_of_participants - 1):
        start_row += 2 + number_of_jury
        data.append(
            {
                'range': f"{chr(start_col + 64)}{start_row}",
                'values': [list_of_participants[temp]]
            }
        )
        temp += 1

    start_col = 1
    start_row = 3
    values = []
    for jury in list_of_jury:
        values.append(jury)

    for i in range(number_of_participants):
        end_row = start_row + len(values) - 1
        data.append(
            {
                'range': f"{chr(start_col + 64)}{start_row}:{chr(start_col + 64)}{end_row}",
                'values': values
            }
        )
        start_row += len(values) + 2

    start_col = 2
    start_row = 2
    values = [list(criteria[0] for criteria in list_of_criteria)]

    end_col = start_col + number_of_criteria - 1
    for i in range(number_of_participants):
        data.append(
            {
                'range': f"{chr(start_col + 64)}{start_row}:{chr(end_col + 64)}{start_row}",
                'values': values
            }
        )
        start_row += number_of_jury + 2

    body = {
        'valueInputOption': 'USER_ENTERED',
        'data': data
    }
    service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global role
    global check
    global name
    global project_type
    global current_criteria
    global default_startup_criteria
    global default_design_criteria
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
        return
    elif call.data == 'jury':
        role = 'jury'
        db.create_table_jury()
        bot.send_message(call.message.chat.id, 'Введіть Ваше ім\'я!')
        bot.register_next_step_handler(call.message, process_name_step)
        return
    elif call.data == 'participant':
        role = 'participant'
        db.create_table_participant()
        bot.send_message(call.message.chat.id, 'Введіть команду, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_team_step)
        return
    if call.data == 'yes':
        check = True
        bot.send_message(call.message.chat.id, 'Введіть компанію, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_company_step)
        return
    elif call.data == 'no':
        process_contest_step(call.message)
        return

    if call.data == 'add_contest':
        bot.send_message(call.message.chat.id, 'Введіть назву конкурсу.')
        bot.register_next_step_handler(call.message, process_contest_name_step)
    elif call.data == 'join_contest':
        process_contest_step(call.message)

    if call.data == 'start_registration':
        if db.is_organizer(call.message):
            db.start_registration()
            bot.send_message(call.message.chat.id, 'Реєстрація на цей конкурс почалась!')
            add_criteria(call.message)
        else:
            bot.send_message(call.message.chat.id, 'Тільки організатори можуть почати реєстрацію.')
    elif call.data == 'dont_start_registration':
        bot.send_message(call.message.chat.id, 'Введіть /startregistration , коли захочете почати реєстрацію!')

    if call.data == 'start_voting':
        if db.is_organizer(call.message):
            db.end_registration()
            db.start_voting()
            bot.send_message(call.message.chat.id, 'Голосування почалось!')
            send_messages(call.message)
        else:
            bot.send_message(call.message.chat.id, 'Тільки організатори можуть почати реєстрацію.')
    elif call.data == 'dont_start_voting':
        bot.send_message(call.message.chat.id, 'Введіть /startvoting , коли захочете почати голосування!')

    if call.data.startswith('join_contest_') and call.data[-1].isdigit() and role == 'jury':
        contest_id = int(call.data.split('_')[2])
        add(call.message)
        db.set_id_jury(call.message, contest_id)
    elif call.data.startswith('join_contest_') and call.data[-1].isdigit() and role == 'participant':
        contest_id = int(call.data.split('_')[2])
        add(call.message)
        db.set_id_participant(call.message, contest_id)
    elif call.data.startswith('join_contest_') and call.data[-1].isdigit() and role == 'viewer':
        contest_id = int(call.data.split('_')[2])
        add(call.message)
        db.set_id_viewer(call.message, contest_id)
    elif call.data.startswith('join_contest_') and call.data[-1].isdigit() and role == 'organizer':
        contest_id = int(call.data.split('_')[2])
        add(call.message)
        db.set_id_organizer(call.message, contest_id)

    if call.data == 'add_criteria':
        start_criteria(call.message)
    elif call.data == 'dont_add_criteria':
        bot.send_message(call.message.chat.id, 'Введіть /criteria , коли захочете додати критерії!')
    elif call.data == 'process_startup_criteria':
        project_type = 'startup'
        current_criteria = default_startup_criteria
        show_current_criteria(call.message, current_criteria)
    elif call.data == 'process_design_criteria':
        project_type = 'design'
        current_criteria = default_design_criteria
        show_current_criteria(call.message, current_criteria)
    elif call.data == 'create_criteria':
        request_count_of_criteria(call.message)
    elif call.data == 'change_criteria':
        request_criteria_number(call.message)
    elif call.data == 'leave_criteria':
        db.create_table_criteria()
        add_criteria_to_db(call.message)


bot.polling()
