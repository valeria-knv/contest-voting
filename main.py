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
check = Falseimport telebot
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
contest_name = None
start_date = None
end_date = None
max_organizers = 1


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

    def create_table_contest(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS contests (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "start_date TEXT NOT NULL, end_date TEXT NOT NULL, max_organizers INTEGER DEFAULT 1, "
                            "registration_started INTEGER DEFAULT 0)")
        self.connection.commit()

    def start_registration(self):
        contest_id_row = self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            self.cursor.execute("UPDATE contests SET registration_started = 1 WHERE id = ?", (contest_id,))
            self.connection.commit()

    def add_contest(self):
        self.cursor.execute("INSERT INTO contests (name, start_date, end_date, max_organizers) VALUES (?, ?, ?, ?)",
                            (contest_name, start_date, end_date, max_organizers))
        self.connection.commit()

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

            markup = telebot.types.InlineKeyboardMarkup()
            add_contest_button = telebot.types.InlineKeyboardButton('Додати конкурс', callback_data='add_contest')
            join_contest_button = telebot.types.InlineKeyboardButton('Приєднатись', callback_data='join_contest')
            markup.add(add_contest_button, join_contest_button)
            bot.send_message(message.chat.id, 'Ви зареєстровані як організатор. Додайте конкурс чи приєднайтесь до існуючого конкурсу:', reply_markup=markup)
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

    def set_id_organizer(self, message):
        self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date))
        result = self.cursor.fetchone()
        if result:
            contest_id = result[0]
            self.cursor.execute("UPDATE organizers SET contest_id = ? WHERE id = ?", (contest_id, message.chat.id))
            self.connection.commit()
        else:
            bot.send_message(message.chat.id, 'Конкурс не знайдено!')

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
    elif role == 'participant' or role == 'viewer':
        process_contest_step(message)
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


def add_contest(message):
    db.create_table_contest()
    db.add_contest()
    bot.send_message(message.chat.id, 'Конкурс додано!')
    db.set_id_organizer(message)
    start_registration(message)


def start_registration(message):
    markup = telebot.types.InlineKeyboardMarkup()
    start_registration_button = telebot.types.InlineKeyboardButton('Почати реєстрацію', callback_data='start_registration')
    dont_start_registration_button = telebot.types.InlineKeyboardButton('Пізніше', callback_data='dont_start_registration')
    markup.add(start_registration_button, dont_start_registration_button)
    bot.send_message(message.chat.id, 'Чи хочете Ви почати реєстрацію для жюрі та учасників?', reply_markup=markup)


def list_contests(message):
    contests = db.get_active_contests()
    i = 0
    info = ''
    for contest in contests:
        i += 1
        info += str(i) + f'. {contest[0]}\n'

    bot.send_message(message.chat.id, info)
    bot.register_next_step_handler(message, join_contest, contests)
    # join_contest(message, contests)


def join_contest(message, contests):
    global contest_name
    global start_date
    try:
        number = int(message.text)
        contest_name = contests[number - 1][0]
        start_date = contests[number - 1][1]
        if opportunity_join() and db.get_registration_status():
            if role == 'organizer':
                db.set_id_organizer(message)
            elif role == 'jury':
                db.set_id_jury(message)
            elif role == 'participant':
                db.set_id_participant(message)
            bot.send_message(message.chat.id, 'Вас додано до конкурсу!')
        elif db.get_registration_status():
            bot.send_message(message.chat.id, "Реєстрація на цей конкурс ще не почалась!")
        else:
            bot.send_message(message.chat.id, "Ви не можете бути доданим до цього конкурсу!\n"
                                              "Оберіть інший варіант!")
            list_contests(message)
    except ValueError:
        bot.send_message(message.chat.id, 'Невірне значення!')


def opportunity_join():
    number = db.get_max_organizers()
    length = db.get_number_organizer_of_contest()
    if number <= length:
        return False
    return True


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global role
    global check
    global name
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
        return
    elif call.data == 'participant':
        role = 'participant'
        db.create_table_participant()
        bot.send_message(call.message.chat.id, 'Введіть команду, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_team_step)
        return
    elif call.data == 'yes':
        check = True
        bot.send_message(call.message.chat.id, 'Введіть компанію, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_company_step)
        return
    elif call.data == 'no':
        process_contest_step(call.message)
        return
    elif call.data == 'add_contest':
        bot.send_message(call.message.chat.id, 'Введіть назву конкурсу.')
        bot.register_next_step_handler(call.message, process_contest_name_step)
    elif call.data == 'join_contest':
        bot.send_message(call.message.chat.id, 'Виберіть конкурс. Надішліть число із списку!')
        list_contests(call.message)
    elif call.data == 'start_registration':
        if db.is_organizer(call.message):
            db.start_registration()
            bot.send_message(call.message.chat.id, 'Реєстрація на цей конкурс почалась!')
        else:
            bot.send_message(call.message.chat.id, 'Тільки організатори можуть почати реєстрацію.')
    elif call.data == 'dont_start_registration':
        bot.send_message(call.message.chat.id, 'Введіть /startregistration , коли захочете почати реєстрацію!')
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


bot.polling()

contest_name = None
start_date = None
end_date = None
max_organizers = 1


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

    def create_table_contest(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS contests (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                            "start_date TEXT NOT NULL, end_date TEXT NOT NULL, max_organizers INTEGER DEFAULT 1, "
                            "registration_started INTEGER DEFAULT 0)")
        self.connection.commit()

    def start_registration(self):
        contest_id_row = self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            self.cursor.execute("UPDATE contests SET registration_started = 1 WHERE id = ?", (contest_id,))
            self.connection.commit()

    def add_contest(self):
        self.cursor.execute("INSERT INTO contests (name, start_date, end_date, max_organizers) VALUES (?, ?, ?, ?)",
                            (contest_name, start_date, end_date, max_organizers))
        self.connection.commit()

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

            markup = telebot.types.InlineKeyboardMarkup()
            add_contest_button = telebot.types.InlineKeyboardButton('Додати конкурс', callback_data='add_contest')
            join_contest_button = telebot.types.InlineKeyboardButton('Приєднатись', callback_data='join_contest')
            markup.add(add_contest_button, join_contest_button)
            bot.send_message(message.chat.id, 'Ви зареєстровані як організатор. Додайте конкурс чи приєднайтесь до існуючого конкурсу:', reply_markup=markup)
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

    def set_id_organizer(self, message):
        self.cursor.execute("SELECT id FROM contests WHERE name = ? AND start_date = ?", (contest_name, start_date))
        result = self.cursor.fetchone()
        if result:
            contest_id = result[0]
            self.cursor.execute("UPDATE organizers SET contest_id = ? WHERE id = ?", (contest_id, message.chat.id))
            self.connection.commit()
        else:
            bot.send_message(message.chat.id, 'Конкурс не знайдено!')

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


# def process_contest_step(message):
#     list_contests(message)
#     if db.get_jury_contest(message):
#         add(message)
#     elif db.get_participant_contest(message):
#         add(message)


def process_contest_step(message):
    active_contests = db.get_active_contests()
    if len(active_contests) > 0:
        markup = telebot.types.InlineKeyboardMarkup()
        for contest in active_contests:
            contest_button = telebot.types.InlineKeyboardButton(contest[1], callback_data=f'join_contest_{contest[0]}')
            markup.add(contest_button)
        bot.send_message(message.chat.id, 'Оберіть конкурс, до якого хочете приєднатись:', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, 'Наразі немає активних конкурсів.')


# def list_contests(message):
#     contests = db.get_active_contests()
#     i = 0
#     info = ''
#     for contest in contests:
#         i += 1
#         info += str(i) + f'. {contest[0]}\n'
#
#     bot.send_message(message.chat.id, info)
#     bot.register_next_step_handler(message, join_contest, contests)
#     # join_contest(message, contests)


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
    elif role == 'participant' or role == 'viewer':
        process_contest_step(message)
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


def add_contest(message):
    db.create_table_contest()
    db.add_contest()
    bot.send_message(message.chat.id, 'Конкурс додано!')
    db.set_id_organizer(message)
    start_registration(message)


def start_registration(message):
    markup = telebot.types.InlineKeyboardMarkup()
    start_registration_button = telebot.types.InlineKeyboardButton('Почати реєстрацію', callback_data='start_registration')
    dont_start_registration_button = telebot.types.InlineKeyboardButton('Пізніше', callback_data='dont_start_registration')
    markup.add(start_registration_button, dont_start_registration_button)
    bot.send_message(message.chat.id, 'Чи хочете Ви почати реєстрацію для жюрі та учасників?', reply_markup=markup)


def list_contests(message):
    contests = db.get_active_contests()
    i = 0
    info = ''
    for contest in contests:
        i += 1
        info += str(i) + f'. {contest[0]}\n'

    bot.send_message(message.chat.id, info)
    bot.register_next_step_handler(message, join_contest, contests)
    # join_contest(message, contests)


def join_contest(message, contests):
    global contest_name
    global start_date
    try:
        number = int(message.text)
        contest_name = contests[number - 1][0]
        start_date = contests[number - 1][1]
        if opportunity_join() and db.get_registration_status():
            if role == 'organizer':
                db.set_id_organizer(message)
            elif role == 'jury':
                db.set_id_jury(message)
            elif role == 'participant':
                db.set_id_participant(message)
            bot.send_message(message.chat.id, 'Вас додано до конкурсу!')
        elif db.get_registration_status():
            bot.send_message(message.chat.id, "Реєстрація на цей конкурс ще не почалась!")
        else:
            bot.send_message(message.chat.id, "Ви не можете бути доданим до цього конкурсу!\n"
                                              "Оберіть інший варіант!")
            list_contests(message)
    except ValueError:
        bot.send_message(message.chat.id, 'Невірне значення!')


def opportunity_join():
    number = db.get_max_organizers()
    length = db.get_number_organizer_of_contest()
    if number <= length:
        return False
    return True


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global role
    global check
    global name
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
        return
    elif call.data == 'participant':
        role = 'participant'
        db.create_table_participant()
        bot.send_message(call.message.chat.id, 'Введіть команду, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_team_step)
        return
    elif call.data == 'yes':
        check = True
        bot.send_message(call.message.chat.id, 'Введіть компанію, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_company_step)
        return
    elif call.data == 'no':
        bot.reply_to(call.message, 'Виберіть конкурс, до якого хочете доєднатись.\nНадішліть число із списку!')
        process_contest_step(call.message)
        return
    elif call.data == 'add_contest':
        bot.send_message(call.message.chat.id, 'Введіть назву конкурсу.')
        bot.register_next_step_handler(call.message, process_contest_name_step)
    elif call.data == 'join_contest':
        bot.send_message(call.message.chat.id, 'Виберіть конкурс. Надішліть число із списку!')
        list_contests(call.message)
    elif call.data == 'start_registration':
        if db.is_organizer(call.message):
            db.start_registration()
            bot.send_message(call.message.chat.id, 'Реєстрація на цей конкурс почалась!')
        else:
            bot.send_message(call.message.chat.id, 'Тільки організатори можуть почати реєстрацію.')
    elif call.data == 'dont_start_registration':
        bot.send_message(call.message.chat.id, 'Введіть /startregistration , коли захочете почати реєстрацію!')
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


bot.polling()
