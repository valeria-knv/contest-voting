from __future__ import print_function

import telebot
import sqlite3
from datetime import date, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread

bot = telebot.TeleBot('6197503153:AAHX9Yz5w1bpDs7v3KlplIye1hg9JVrFQlc')

check = False
val = {}
quantity_check = {}

organizer_table_title = None
team_scores = []

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
criteria_points = []
current_criteria_points_idx = 0
current_part_name = None

CREDENTIALS_FILE = 'credentials2.json'

sa = gspread.service_account(filename=CREDENTIALS_FILE)
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


class TeamScore:
    def __init__(self, name, score):
        self.name = name
        self.score = score


class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def create_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, role TEXT)")
        self.connection.commit()

    def add_user(self, message, user_role):
        try:
            self.cursor.execute("INSERT INTO users (id, role) VALUES (?, ?)", (message.chat.id, user_role))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def get_role_from_users(self, message):
        result = self.cursor.execute("SELECT role FROM users WHERE id = ?", (message.chat.id,)).fetchone()
        if result:
            return result[0]
        return None

    def get_role_from_users_id(self, id_user):
        result = self.cursor.execute("SELECT role FROM users WHERE id = ?", (id_user,)).fetchone()
        if result:
            return result[0]
        return None

    def create_table_criteria(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS criteria (id INTEGER, name TEXT, contest_id INTEGER, PRIMARY KEY(id, contest_id))")
        self.connection.commit()

    def set_name_criteria(self, message, criteria, crit_id):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("INSERT INTO criteria (id, name, contest_id) VALUES (?, ?, ?)", (crit_id, criteria, contest_id))
        self.connection.commit()

    def create_table_contest(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS contests (id INTEGER PRIMARY KEY, name TEXT, "
                            "start_date TEXT, end_date TEXT, "
                            "registration_started INTEGER DEFAULT 0, voting_started INTEGER DEFAULT 0, max_score INTEGER DEFAULT 0,"
                            " sheet_id TEXT)")
        self.connection.commit()

    def start_registration(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("UPDATE contests SET registration_started = 1 WHERE id = ?", (contest_id,))
        self.connection.commit()

    def end_registration(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("UPDATE contests SET registration_started = 0 WHERE id = ?", (contest_id,))
        self.connection.commit()

    def start_voting(self, message, type_of_voting):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("UPDATE contests SET voting_started = ? WHERE id = ?", (type_of_voting, contest_id))
        self.connection.commit()

    def get_active_contests(self):
        self.cursor.execute("SELECT id, name, start_date FROM contests WHERE start_date < date('now') AND end_date > date('now') AND registration_started = 1")
        return self.cursor.fetchall()

    def get_voting_contest(self):
        self.cursor.execute("SELECT id, name, start_date FROM contests WHERE start_date < date('now') AND end_date > date('now') AND voting_started = 1")
        return self.cursor.fetchall()

    def get_number_organizer_of_contest(self, contest_id):
        return self.cursor.execute("SELECT id FROM organizers WHERE contest_id = ?", (contest_id,)).fetchall()

    def user_exists(self, message):
        try:
            result = self.cursor.execute("SELECT * FROM users WHERE id = ?", (message.chat.id,)).fetchall()
            return bool(result)
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_organizer(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS organizers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, "
                            "lastname TEXT, password TEXT, contest_id INTEGER)")
        self.connection.commit()

    def add_user_organizer(self, message):
        try:
            self.cursor.execute("INSERT INTO organizers (id) VALUES (?)",
                                (message.chat.id,))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_jury(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS jury (id INTEGER PRIMARY KEY, name TEXT, "
                            "lastname TEXT, company TEXT, nickname TEXT, contest_id INTEGER, password TEXT, all_crit INTEGER DEFAULT 0, "
                            "second_voting INTEGER DEFAULT 0)")
        self.connection.commit()

    def add_user_jury(self, message):
        try:
            self.cursor.execute("INSERT INTO jury (id) VALUES (?)",
                                (message.chat.id,))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_participant(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS participants (id INTEGER PRIMARY KEY, team TEXT, "
                            "contest_id INTEGER, password TEXT, end INTEGER DEFAULT 0, voting_scores INTEGER DEFAULT 0, "
                            "number_of_voters INTEGER DEFAULT 0, award INTEGER DEFAULT 0)")
        self.connection.commit()

    def add_user_participant(self, message):
        try:
            self.cursor.execute("INSERT INTO participants (id) VALUES (?)",
                                (message.chat.id,))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def create_table_viewer(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS viewer (id INTEGER PRIMARY KEY, nickname TEXT, "
                            "password TEXT, contest_id INTEGER, award INTEGER DEFAULT 0)")
        self.connection.commit()

    def add_user_viewer(self, message):
        try:
            self.cursor.execute("INSERT INTO viewer (id) VALUES (?)",
                                (message.chat.id,))
            self.connection.commit()
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, 'Ви вже зареєстровані!')

    def add_name(self, message, user_name):
        user_role = self.get_role_from_users(message)
        if user_role == 'organizer':
            self.cursor.execute("UPDATE organizers SET name = ? WHERE id = ?", (user_name, message.chat.id))
        elif user_role == 'jury':
            self.cursor.execute("UPDATE jury SET name = ? WHERE id = ?", (user_name, message.chat.id))
        self.connection.commit()

    def add_lastname(self, message, lastname):
        user_role = self.get_role_from_users(message)
        if user_role == 'organizer':
            self.cursor.execute("UPDATE organizers SET lastname = ? WHERE id = ?", (lastname, message.chat.id))
        elif user_role == 'jury':
            self.cursor.execute("UPDATE jury SET lastname = ? WHERE id = ?", (lastname, message.chat.id))
        self.connection.commit()

    def add_password(self, message, user_password):
        user_role = self.get_role_from_users(message)
        if user_role == 'organizer':
            self.cursor.execute("UPDATE organizers SET password = ? WHERE id = ?", (user_password, message.chat.id))
        elif user_role == 'jury':
            self.cursor.execute("UPDATE jury SET password = ? WHERE id = ?", (user_password, message.chat.id))
        elif user_role == 'participant':
            self.cursor.execute("UPDATE participants SET password = ? WHERE id = ?", (user_password, message.chat.id))
        elif user_role == 'viewer':
            self.cursor.execute("UPDATE viewer SET password = ? WHERE id = ?", (user_password, message.chat.id))
        self.connection.commit()

    def add_team(self, message, team):
        self.cursor.execute("UPDATE participants SET team = ? WHERE id = ?", (team, message.chat.id))
        self.connection.commit()

    def add_company(self, message, company):
        self.cursor.execute("UPDATE jury SET company = ? WHERE id = ?", (company, message.chat.id))
        self.connection.commit()

    def add_nickname(self, message, nickname):
        user_role = self.get_role_from_users(message)
        if user_role == 'viewer':
            self.cursor.execute("UPDATE viewer SET nickname = ? WHERE id = ?", (nickname, message.chat.id))
        elif user_role == 'jury':
            self.cursor.execute("UPDATE jury SET nickname = ? WHERE id = ?", (nickname, message.chat.id))
        self.connection.commit()

    def add_contest_name(self, contest_name):
        self.cursor.execute("INSERT INTO contests (name) VALUES (?)", (contest_name,))
        self.connection.commit()
        return self.cursor.execute("SELECT id FROM contests WHERE name = ?", (contest_name,)).fetchone()[0]

    def add_start_date(self, message, contest_start_date):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("UPDATE contests SET start_date = ? WHERE id = ?", (contest_start_date, contest_id))
        self.connection.commit()

    def add_end_date(self, message, contest_end_date):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("UPDATE contests SET end_date = ? WHERE id = ?", (contest_end_date, contest_id))
        self.connection.commit()

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
        return bool(self.cursor.execute("SELECT id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0])

    def is_jury(self, message):
        return bool(self.cursor.execute("SELECT id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0])

    def is_participant_or_viewer(self, message):
        user_role = self.get_role_from_users(message)
        if user_role == 'participant':
            return True
        elif user_role == 'viewer':
            return True
        else:
            return False

    def get_registration_status(self, contest_id):
        return bool(self.cursor.execute("SELECT registration_started FROM contests WHERE id = ?", (contest_id,)).fetchone()[0])

    def get_voting_status(self, contest_id):
        return self.cursor.execute("SELECT voting_started FROM contests WHERE id = ?", (contest_id,)).fetchone()[0]

    def get_jury_contest(self, message):
        return bool(self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0])

    def get_participant_contest(self, message):
        return bool(self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0])

    def delete_from_users(self, message):
        self.cursor.execute("DELETE FROM users WHERE id = ?", (message.chat.id,))
        self.connection.commit()

    def delete_from_users_id(self, user_id):
        self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.connection.commit()

    def delete_contest(self, contest_id):
        self.cursor.execute("DELETE FROM contests WHERE id = ?", (contest_id,))
        self.connection.commit()

    def delete_criteria_from_id(self, contest_id):
        self.cursor.execute("DELETE FROM criteria WHERE contest_id = ?", (contest_id,))
        self.connection.commit()

    def delete_from_tables(self, message):
        user_role = self.get_role_from_users(message)
        if user_role == 'organizer':
            self.cursor.execute("DELETE FROM organizers WHERE id = ?", (message.chat.id,))
        elif user_role == 'jury':
            self.cursor.execute("DELETE FROM jury WHERE id = ?", (message.chat.id,))
        elif user_role == 'participant':
            self.cursor.execute("DELETE FROM participants WHERE id = ?", (message.chat.id,))
        elif user_role == 'viewer':
            self.cursor.execute("DELETE FROM viewer WHERE id = ?", (message.chat.id,))
        self.connection.commit()

    def delete_from_tables_id(self, user_id):
        user_role = self.get_role_from_users_id(user_id)
        if user_role == 'organizer':
            self.cursor.execute("DELETE FROM organizers WHERE id = ?", (user_id,))
        elif user_role == 'jury':
            self.cursor.execute("DELETE FROM jury WHERE id = ?", (user_id,))
        elif user_role == 'participant':
            self.cursor.execute("DELETE FROM participants WHERE id = ?", (user_id,))
        elif user_role == 'viewer':
            self.cursor.execute("DELETE FROM viewer WHERE id = ?", (user_id,))
        self.connection.commit()

    def get_id_jury_from_contest(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM jury WHERE contest_id = ?", (contest_id,)).fetchall()

    def get_id_participants_from_contest(self, message):
        contest_id_row = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()
        if contest_id_row is not None:
            contest_id = contest_id_row[0]
            return self.cursor.execute("SELECT id FROM participants WHERE contest_id = ?", (contest_id,)).fetchall()
        else:
            return 0

    def get_number_of_participants(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT COUNT(id) FROM participants WHERE contest_id = ?", (contest_id,)).fetchone()[0]

    def get_number_of_criteria(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT COUNT(id) FROM criteria WHERE contest_id = ?", (contest_id,)).fetchone()[0]

    def get_number_of_jury(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT COUNT(id) FROM jury WHERE contest_id = ?", (contest_id,)).fetchone()[0]

    def get_list_of_participants(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT team FROM participants WHERE contest_id = ? AND end = 0", (contest_id,)).fetchall()

    def get_list_of_participants_not_all(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT team FROM participants WHERE contest_id = ? AND end = 1", (contest_id,)).fetchall()

    def get_list_of_participants_all(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT team FROM participants WHERE contest_id = ?", (contest_id,)).fetchall()

    def get_id_team_from_name(self, message, name_part):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM participants WHERE team = ? AND contest_id = ?", (name_part, contest_id)).fetchone()[0]

    def get_list_of_criteria(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT name FROM criteria WHERE contest_id = ?", (contest_id,)).fetchall()

    def get_list_of_jury(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT nickname FROM jury WHERE contest_id = ?", (contest_id,)).fetchall()

    def get_ids_of_participants(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM participants WHERE contest_id = ? AND end = 0", (contest_id,)).fetchall()

    def get_ids_of_participants_end(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM participants WHERE contest_id = ? AND end = 1", (contest_id,)).fetchall()

    def get_ids_of_participants_all(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM participants WHERE contest_id = ?", (contest_id,)).fetchall()

    def get_ids_of_viewer(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM viewer WHERE contest_id = ?", (contest_id,)).fetchall()

    def get_ids_of_viewer_to_score(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM viewer WHERE contest_id = ? AND award = 1", (contest_id,)).fetchall()

    def get_ids_of_participants_to_score(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM participants WHERE contest_id = ? AND award = 1", (contest_id,)).fetchall()

    def get_name_participants(self, part_id):
        return self.cursor.execute("SELECT team FROM participants WHERE id = ?", (part_id,)).fetchone()[0]

    def get_start_date(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT start_date FROM contests WHERE id = ?", (contest_id,)).fetchone()[0]

    def get_end_date(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT end_date FROM contests WHERE id = ?", (contest_id,)).fetchone()[0]

    def set_max_score(self, message, max_sc):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("UPDATE contests SET max_score = ? WHERE id = ?", (max_sc, contest_id))
        self.connection.commit()

    def get_ids_names_criteria(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        criteria_rows = self.cursor.execute("SELECT id, name FROM criteria WHERE contest_id = ?", (contest_id,)).fetchall()
        criteria = [(row[0], row[1]) for row in criteria_rows]
        return criteria

    def get_max_score(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'participant':
            contest_id = self.cursor.execute("SELECT contest_id FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            contest_id = self.cursor.execute("SELECT contest_id FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT max_score FROM contests WHERE id = ?", (contest_id,)).fetchone()[0]

    def set_sheet_id(self, message, sheet_id):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("UPDATE contests SET sheet_id = ? WHERE id = ?", (sheet_id, contest_id))
        self.connection.commit()

    def get_sheet_id(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT sheet_id FROM contests WHERE id = ?", (contest_id,)).fetchone()[0]

    def get_name_jury(self, id_jury):
        return self.cursor.execute("SELECT nickname FROM jury WHERE id = ?", (id_jury,)).fetchone()[0]

    def get_name_lastname_jury(self, id_jury):
        return self.cursor.execute("SELECT name, lastname FROM jury WHERE id = ?", (id_jury,)).fetchall()[0]

    def get_name_criteria(self, message, numb):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT name FROM criteria WHERE contest_id = ? AND id = ?", (contest_id, numb)).fetchone()[0]

    def set_end_for_participants(self, part_id):
        self.cursor.execute("UPDATE participants SET end = 1 WHERE id = ?", (part_id,))
        self.connection.commit()

    def get_id_organizer(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM organizers WHERE contest_id = ?", (contest_id,)).fetchone()[0]

    def get_id_participants_from_name(self, message, part_name):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        return self.cursor.execute("SELECT id FROM participants WHERE contest_id = ? AND team = ?", (contest_id, part_name)).fetchone()[0]

    def get_role_from_users_for_score(self, id_jury):
        self.cursor.execute("SELECT role FROM users WHERE id = ?", (id_jury,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return None

    def get_all_crit(self, id_jury):
        user_role = self.get_role_from_users_for_score(id_jury)
        contest_id = 0
        if user_role == 'organizer':
            return
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (id_jury,)).fetchone()[0]
        return self.cursor.execute("SELECT all_crit FROM jury WHERE contest_id = ? AND id = ?", (contest_id, id_jury)).fetchone()[0]

    def set_all_crit(self, message, numb, id_jury):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        self.cursor.execute("UPDATE jury SET all_crit = ? WHERE contest_id = ? AND id = ?", (numb, contest_id, id_jury))
        self.connection.commit()

    def get_second_voting(self, message):
        return self.cursor.execute("SELECT second_voting FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]

    def set_second_voting(self, message, number):
        self.cursor.execute("UPDATE jury SET second_voting = ? WHERE id = ?", (number, message.chat.id))

    def set_null_for_all_crit(self, id_jury):
        user_role = self.get_role_from_users_for_score(id_jury)
        contest_id = 0
        if user_role == 'organizer':
            return
        elif user_role == 'jury':
            contest_id = self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (id_jury,)).fetchone()[0]
        self.cursor.execute("UPDATE jury SET all_crit = 0 WHERE contest_id = ? AND id = ?", (contest_id, id_jury))
        self.connection.commit()

    def get_contest_id(self, message):
        user_role = db.get_role_from_users(message)
        if user_role == 'jury':
            return self.cursor.execute("SELECT contest_id FROM jury WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'organizer':
            return self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]

    def check_criteria_in_database(self, message):
        user_role = self.get_role_from_users(message)
        contest_id = 0
        if user_role == 'organizer':
            contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'jury':
            return 0
        return self.cursor.execute("SELECT name FROM criteria WHERE contest_id = ?", (contest_id,)).fetchall()

    def delete_criteria(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,))
        self.cursor.execute("DELETE FROM criteria WHERE contest_id = ?", (contest_id,))
        self.connection.commit()

    def set_award(self, message):
        user_role = db.get_role_from_users(message)
        if user_role == 'participant':
            self.cursor.execute("UPDATE participants SET award = 1 WHERE id = ?", (message.chat.id,))
        elif user_role == 'viewer':
            self.cursor.execute("UPDATE viewer SET award = 1 WHERE id = ?", (message.chat.id,))
        self.connection.commit()

    def get_award(self, message):
        user_role = db.get_role_from_users(message)
        if user_role == 'participant':
            return self.cursor.execute("SELECT award FROM participants WHERE id = ?", (message.chat.id,)).fetchone()[0]
        elif user_role == 'viewer':
            return self.cursor.execute("SELECT award FROM viewer WHERE id = ?", (message.chat.id,)).fetchone()[0]

    def get_voting_scores(self, part_id):
        return self.cursor.execute("SELECT voting_scores FROM participants WHERE id = ?", (part_id,)).fetchone()[0]

    def set_voting_scores(self, part_id, number):
        self.cursor.execute("UPDATE participants SET voting_scores = ? WHERE id = ?", (number, part_id))
        self.connection.commit()

    def get_number_of_voters(self, part_id):
        return self.cursor.execute("SELECT number_of_voters FROM participants WHERE id = ?", (part_id,)).fetchone()[0]

    def set_number_of_voters(self, part_id, number):
        self.cursor.execute("UPDATE participants SET number_of_voters = ? WHERE id = ?", (number, part_id))
        self.connection.commit()

    def get_contest(self, message):
        contest_id = self.cursor.execute("SELECT contest_id FROM organizers WHERE id = ?", (message.chat.id,))
        result = self.cursor.execute("SELECT id, name FROM contests WHERE id = ?", (contest_id,))
        if result.fetchall() is not None:
            return result.fetchall()
        return None


db = Database('test1.db')


def get_username(message):
    if message.from_user.username:
        return message.from_user.username.lower().endswith('bot')
    else:
        return None


@bot.message_handler(commands=['start'])
def handle_start_help(message):
    if get_username(message) or get_username(message) is None:
        bot.send_message(message.chat.id, 'Це бот, Ви не зможете продовжити!')
        return
    db.create_table()
    db.create_table_organizer()
    db.create_table_jury()
    db.create_table_participant()
    db.create_table_viewer()
    db.create_table_contest()
    db.create_table_criteria()
    if db.user_exists(message):
        bot.send_message(message.chat.id, 'Ви вже зареєстровані!')
    else:
        bot.reply_to(message, 'Привіт! Я бот реєстрації користувачів для конкурсів. Для реєстрації введіть /register')


@bot.message_handler(commands=['register'])
def handle_register(message):
    if get_username(message) or get_username(message) is None:
        bot.send_message(message.chat.id, 'Це бот, Ви не зможете продовжити!')
        return
    db.create_table()
    if db.user_exists(message):
        bot.send_message(message.chat.id, 'Ви вже зареєстровані!')
    else:
        bot.send_message(message.chat.id, 'Якщо вам знадобиться допомога, введіть /help після реєстрації')
        bot.send_message(message.chat.id, 'Організатор створює голосування та керує їм. Якщо у вас декілька організаторів, оберіть того, хто буде керувати конкурсом у боті.\n\n'
                                          'Жюрі може приєднатись тільки під час періоду "реєстрація". Організатору потрібно повідомити жюрі, коли почнеться та звкінчеться цей період.\n\n'
                                          'Команда (участник) також приєднується тільки під час періоду "реєстрація". Організатору потрібно повідомити учасників, коли почнеться та звкінчеться цей період. '
                                          'Якщо у вас команда, то приєднується тільки ЛІДЕР команди.\n\n'
                                          'Глядач приєднується тільки після того, як почнеться вже голосування!')
        markup = telebot.types.InlineKeyboardMarkup()
        user_button = telebot.types.InlineKeyboardButton('Глядач', callback_data='viewer')
        organizer_button = telebot.types.InlineKeyboardButton('Організатор', callback_data='organizer')
        jury_button = telebot.types.InlineKeyboardButton('Журі', callback_data='jury')
        participant_button = telebot.types.InlineKeyboardButton('Учасник', callback_data='participant')
        markup.add(user_button, organizer_button, jury_button, participant_button)
        bot.send_message(message.chat.id, 'Обери свою роль', reply_markup=markup)


@bot.message_handler(commands=['help'])
def handle_help(message):
    user_role = db.get_role_from_users(message)
    commands = None
    if not db.user_exists(message):
        bot.send_message(message.chat.id, 'Ви ще не зареєстровані!')
        commands = [
            "/start - Почати роботу бота",
            "/register - Зареєструватись"
        ]
        help_text = "Ось доступні команди для вас:\n" + "\n".join(commands)
        bot.send_message(message.chat.id, help_text)
    else:
        if user_role == 'viewer':
            commands = [
                "/start - Почати роботу бота",
                "/register - Зареєструватись",
                "/help - Отримати список команд",
                "/choice_award - Почати оцінювати",
                "/delete - Видалення акаунту"
            ]
        elif user_role == 'organizer':
            commands = [
                "/start - Почати роботу бота",
                "/register - Зареєструватись",
                "/help - Отримати список команд",
                "/startregistration - Початок реєстрації конкурсу",
                "/startvoting - Почати голосування",
                "/criteria - Критерії конкурсу",
                "/deletecontest - Видалення конкурсу",
                "/delete - Видалення акаунту"
            ]
        elif user_role == 'jury':
            commands = [
                "/start - Почати роботу бота",
                "/register - Зареєструватись",
                "/help - Отримати список команд",
                "/changescore - Змінити бал вже оціненій команді (учаснику) чи просто продивитись бали",
                "/delete - Видалення акаунту"
            ]
        elif user_role == 'participant':
            commands = [
                "/start - Почати роботу бота",
                "/register - Зареєструватись",
                "/help - Отримати список команд",
                "/choice_award - Почати оцінювати",
                "/delete - Видалення акаунту"
            ]
        help_text = "Доступні команди:\n" + "\n".join(commands)
        bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['startregistration'])
def handle_start_registration(message):
    if db.user_exists(message):
        if db.is_organizer(message):
            start_registration(message)
        else:
            bot.send_message(message.chat.id, "Ви не організатор!")
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


@bot.message_handler(commands=['startvoting'])
def handle_start_voting(message):
    if db.user_exists(message):
        if db.is_organizer(message):
            start_voting(message)
        else:
            bot.send_message(message.chat.id, "Ви не організатор!")
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


@bot.message_handler(commands=['addcontest'])
def handle_add_contest(message):
    if db.user_exists(message):
        if db.is_organizer(message):
            organizer_add_contest(message)
        else:
            bot.send_message(message.chat.id, "Ви не організатор!")
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


@bot.message_handler(commands=['criteria'])
def handle_start_criteria(message):
    if db.user_exists(message):
        if db.is_organizer(message):
            start_criteria(message)
        else:
            bot.send_message(message.chat.id, "Ви не організатор!")
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


@bot.message_handler(commands=['startvotingjury'])
def handle_start_voting_for_jury(message):
    if db.user_exists(message):
        if db.is_jury(message):
            start_registration(message)
        else:
            bot.send_message(message.chat.id, "Ви не жюрі!")
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


@bot.message_handler(commands=['choice_award'])
def handle_choice_award(message):
    if db.user_exists(message):
        if db.is_participant_or_viewer(message):
            send_messages_for_part_and_viewer_again(message)
        else:
            bot.send_message(message.chat.id, "Ви не можете зробити цю дію!")
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


@bot.message_handler(commands=['delete_contest'])
def handle_delete_contest(message):
    if db.user_exists(message):
        if db.is_organizer(message):
            all_contest = db.get_contest(message)
            markup = telebot.types.InlineKeyboardMarkup()
            for contest in all_contest:
                contest_button = telebot.types.InlineKeyboardButton(contest[1], callback_data=f'delete_contest_{str(contest[0])}')
                markup.add(contest_button)
            no_button = telebot.types.InlineKeyboardButton("Не видаляти", callback_data=f'delete_contest_{str(0)}')
            markup.add(no_button)
            bot.send_message(message.chat.id, 'Оберіть конкурс, який хочете видалити:', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Ви не організатор!")
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


@bot.message_handler(commands=['changescore'])
def handle_start_voting_for_jury(message):
    if db.user_exists(message):
        if db.is_jury(message):
            change_points(message)
        else:
            bot.send_message(message.chat.id, "Ви не жюрі!")
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


@bot.message_handler(commands=['delete'])
def handle_delete(message):
    if db.user_exists(message):
        db.delete_from_tables(message)
        db.delete_from_users(message)
    else:
        bot.send_message(message.chat.id, "Ви не зареєстровані!")


def process_name_step(message):
    user_name = message.text
    db.add_name(message, user_name)
    bot.reply_to(message, 'Введіть Ваше прізвище')
    bot.register_next_step_handler(message, process_lastname_step)


def process_lastname_step(message):
    lastname = message.text
    db.add_lastname(message, lastname)
    bot.reply_to(message, 'Введіть пароль')
    bot.register_next_step_handler(message, process_password_step)


def process_company_step(message):
    company = message.text
    db.add_company(message, company)
    bot.reply_to(message, 'Щоб Ваші бали на конкурсі були АНОНІМізовані, введіть нікмейм!')
    bot.register_next_step_handler(message, process_nickname_step)


def process_team_step(message):
    team = message.text
    db.add_team(message, team)
    bot.reply_to(message, 'Введіть пароль')
    bot.register_next_step_handler(message, process_password_step)


def process_nickname_step(message):
    nickname = message.text
    db.add_nickname(message, nickname)
    if db.get_role_from_users(message) == 'jury':
        process_contest_step(message)
    elif db.get_role_from_users(message) == 'viewer':
        bot.reply_to(message, 'Введіть пароль')
        bot.register_next_step_handler(message, process_password_step)


def process_contest_step(message):
    active_contests = db.get_active_contests()
    voting_contest = db.get_voting_contest()
    if len(active_contests) > 0:
        markup = telebot.types.InlineKeyboardMarkup()
        for contest in active_contests:
            contest_button = telebot.types.InlineKeyboardButton(contest[1], callback_data=f'join_contest_{contest[0]}')
            markup.add(contest_button)
        bot.send_message(message.chat.id, 'Оберіть конкурс, до якого хочете приєднатись:', reply_markup=markup)
    elif db.get_role_from_users(message) == 'viewer' and len(voting_contest) > 0:
        markup = telebot.types.InlineKeyboardMarkup()
        for contest in voting_contest:
            contest_button = telebot.types.InlineKeyboardButton(contest[1], callback_data=f'join_contest_{contest[0]}')
            markup.add(contest_button)
        bot.send_message(message.chat.id, 'Оберіть конкурс, до якого хочете приєднатись:', reply_markup=markup)

    else:
        bot.send_message(message.chat.id, 'Наразі немає активних конкурсів. Тому Ви не можете зареєструватись!')
        db.delete_from_tables(message)
        db.delete_from_users(message)


def process_password_step(message):
    password = message.text
    db.add_password(message, password)
    if db.get_role_from_users(message) == 'jury':
        markup = telebot.types.InlineKeyboardMarkup()
        yes_button = telebot.types.InlineKeyboardButton('Так', callback_data='yes')
        no_button = telebot.types.InlineKeyboardButton('Ні', callback_data='no')
        markup.add(yes_button, no_button)
        bot.send_message(message.chat.id, 'Ви представляєте якусь компанію?', reply_markup=markup)
    elif db.get_role_from_users(message) == 'organizer':
        organizer_add_contest(message)
    else:
        process_contest_step(message)


def organizer_add_contest(message):
    markup = telebot.types.InlineKeyboardMarkup()
    add_contest_button = telebot.types.InlineKeyboardButton('Додати конкурс', callback_data='add_contest')
    join_contest_button = telebot.types.InlineKeyboardButton('Не додавати', callback_data='no_contest')
    markup.add(add_contest_button, join_contest_button)
    bot.send_message(message.chat.id, 'Ви зареєстровані як організатор. Додайте конкурс:', reply_markup=markup)


def process_contest_name_step(message):
    db.create_table_contest()
    contest_name = message.text
    contest_id = db.add_contest_name(contest_name)
    db.set_id_organizer(message, contest_id)
    bot.reply_to(message, 'Введіть дату початку конкурсу у форматі "рік-місяць-день".\n\nУ період, який Ви зараз визначите, повинно входити період реєстрації та період голосування!')
    bot.register_next_step_handler(message, process_start_date_step)


def is_valid_date_format(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def process_start_date_step(message):
    contest_start_date = message.text
    if is_valid_date_format(contest_start_date):
        bot.reply_to(message, 'Введіть дату закінчення конкурсу у форматі "рік-місяць-день".')
        db.add_start_date(message, contest_start_date)
        bot.register_next_step_handler(message, process_end_date_step)
    else:
        bot.reply_to(message, 'Невірний формат дати. Будь ласка, введіть дату у форматі "РРРР-ММ-ДД" (наприклад, 2023-06-26):')
        bot.register_next_step_handler(message, process_start_date_step)


def process_end_date_step(message):
    contest_end_date = message.text
    if is_valid_date_format(contest_end_date):
        db.add_end_date(message, contest_end_date)
        add_contest(message)
    else:
        bot.reply_to(message, 'Невірний формат дати. Будь ласка, введіть дату у форматі "РРРР-ММ-ДД" (наприклад, 2023-06-26):')
        bot.register_next_step_handler(message, process_end_date_step)


def add_contest(message):
    bot.send_message(message.chat.id, 'Конкурс додано!')
    start_registration(message)


def check_date(message):
    start_date = db.get_start_date(message)
    end_date = db.get_end_date(message)

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


def add_criteria(message):
    markup = telebot.types.InlineKeyboardMarkup()
    start_button = telebot.types.InlineKeyboardButton('Додати критерії', callback_data='add_criteria')
    no_start_button = telebot.types.InlineKeyboardButton('Пізніше', callback_data='dont_add_criteria')
    markup.add(start_button, no_start_button)
    bot.send_message(message.chat.id, 'Чи хочете Ви додати критерії?', reply_markup=markup)


def start_criteria(message):
    markup = telebot.types.InlineKeyboardMarkup()
    if db.check_criteria_in_database(message) is None and db.check_criteria_in_database(message) != 0:
        bot.send_message(message.chat.id, "Критерії конкурсу:")
        info = ''
        for index, crit in db.check_criteria_in_database(message):
            info += f'{index + 1}. {crit[0]}\n'
        bot.send_message(message.chat.id, info)
        button_1 = telebot.types.InlineKeyboardButton('Так', callback_data='criteria_delete')
        button_2 = telebot.types.InlineKeyboardButton('Ні', callback_data='criteria_no_delete')
        markup.add(button_1, button_2)
        bot.send_message(message.chat.id, 'Чи хочете Ви видалити критерії?', reply_markup=markup)
    elif db.check_criteria_in_database(message) == 0:
        bot.send_message(message.chat.id, "Ви не огранізатор!")
    else:
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
    change_button = telebot.types.InlineKeyboardButton('Змінити один', callback_data='change_criteria')
    create_button = telebot.types.InlineKeyboardButton('Створити нові', callback_data='create_criteria')

    add_button = telebot.types.InlineKeyboardButton('Додати один', callback_data='add_criterion')
    remove_button = telebot.types.InlineKeyboardButton('Видалити один', callback_data='remove_criterion')

    buttons_to_show_if_theres_criteria = [
        leave_button,
        change_button,
        create_button,
        add_button,
        remove_button
    ]

    buttons_to_show_if_theres_no_criteria = [
        create_button,
        add_button
    ]

    if len(current_criteria) != 0:
        markup.add(*buttons_to_show_if_theres_criteria)
    else:
        markup.add(*buttons_to_show_if_theres_no_criteria)

    message_to_show_if_theres_criteria = 'Поточні критерії: \n\n' + criteria_as_string(criteria) + '\n\nЧи влаштовують вони Вас?'
    message_to_show_if_theres_no_criteria = 'Ви видалили усі критерії!'

    bot.send_message(
        message.chat.id,
        message_to_show_if_theres_criteria if len(current_criteria) != 0 else message_to_show_if_theres_no_criteria,
        reply_markup=markup
    )


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


def remove_message_buttons(message):
    bot.edit_message_reply_markup(message.chat.id, message.id)


def set_new_message_text(message, text):
    bot.edit_message_text(text, message.chat.id, message.id)


def request_criterion_to_add(message):
    msg = bot.send_message(message.chat.id, 'Введіть новий критерій, який хочете додати:')
    bot.register_next_step_handler(msg, save_added_criterion)


def save_added_criterion(message):
    global current_criteria
    current_criteria += [message.text]
    msg = bot.send_message(message.chat.id, f'Критерій збережено: \n{len(current_criteria)}. {message.text}')
    show_current_criteria(msg, current_criteria)


def request_criterion_number_to_remove(message):
    global current_criteria

    if len(current_criteria) == 1:
        del current_criteria[0]
        msg = bot.send_message(message.chat.id, 'Останній критерій видалено!')
        show_current_criteria(msg, current_criteria)
        return

    msg = bot.send_message(message.chat.id, 'Введіть номер критерію, який хочете видалити:')
    bot.register_next_step_handler(msg, remove_criterion)


def remove_criterion(message):
    global current_criteria
    try:
        criterion_to_remove_number = int(message.text)
        if criterion_to_remove_number <= 0 or criterion_to_remove_number > len(current_criteria):
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, 'Введений номер критерію не валідний, спробуйте ще раз:')
        bot.register_next_step_handler(msg, remove_criterion)
        return

    del current_criteria[criterion_to_remove_number - 1]

    msg = bot.send_message(message.chat.id, 'Критерій видалено!')
    show_current_criteria(msg, current_criteria)


def add_criteria_to_db(message):
    global current_criteria
    i = 0
    for criteria in current_criteria:
        i += 1
        db.set_name_criteria(message, str(criteria), i)
    start_voting(message)


def types_of_voting(message):
    markup = telebot.types.InlineKeyboardMarkup()
    if not check_date(message):
        return
    first_voting_button = telebot.types.InlineKeyboardButton('З виступами', callback_data='voting_1')
    second_voting_button = telebot.types.InlineKeyboardButton('Звичайне (без виступів)', callback_data='voting_2')
    markup.add(first_voting_button, second_voting_button)
    bot.send_message(message.chat.id, 'Оберіть тип голосування!', reply_markup=markup)


def start_voting(message):
    markup = telebot.types.InlineKeyboardMarkup()
    if not check_date(message):
        return
    start_registration_button = telebot.types.InlineKeyboardButton('Почати голосування', callback_data='start_voting')
    dont_start_registration_button = telebot.types.InlineKeyboardButton('Пізніше', callback_data='dont_start_voting')
    markup.add(start_registration_button, dont_start_registration_button)
    bot.send_message(message.chat.id, 'Чи хочете Ви почати конкурсне голосування?', reply_markup=markup)


def send_messages(message):
    ids_jury = db.get_id_jury_from_contest(message)
    ids_participants = db.get_id_participants_from_contest(message)
    for id_jury in ids_jury:
        bot.send_message(int(id_jury[0]), 'Голосування почалось!')
    for id_part in ids_participants:
        bot.send_message(int(id_part[0]), 'Голосування почалось!')

    create('contest voting', message)


def send_messages_jury_about_team(message, part_id, part_name):
    ids_jury = db.get_id_jury_from_contest(message)
    for id_jury in ids_jury:
        bot.send_message(int(id_jury[0]), f'Зараз виступає команда {part_name}!\nПоставте свої бали, будь ласка.')
    criteria_scores(message, part_id, part_name)


def send_messages_for_part_and_viewer(message):
    ids_participants = db.get_ids_of_participants(message)
    ids_viewer = db.get_ids_of_viewer(message)
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton('Так', callback_data='choice_award_1')
    no_button = telebot.types.InlineKeyboardButton('Ні', callback_data='choice_award_0')
    markup.add(yes_button, no_button)
    for id_part in ids_participants:
        bot.send_message(int(id_part[0]), 'Чи хочете Ви поставити бали командам (учасникам) для призу глядацьких симпатій?', reply_markup=markup)
    for id_viewer in ids_viewer:
        bot.send_message(int(id_viewer[0]), 'Чи хочете Ви поставити бали командам (учасникам) для призу глядацьких симпатій?', reply_markup=markup)


def send_messages_for_part_and_viewer_again(message):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton('Так', callback_data='choice_award_1')
    no_button = telebot.types.InlineKeyboardButton('Ні', callback_data='choice_award_0')
    markup.add(yes_button, no_button)
    bot.send_message(message.chat.id, 'Чи хочете Ви поставити бали командам (учасникам) для призу глядацьких симпатій?', reply_markup=markup)


def performed_teams(message):
    list_of_participants = db.get_list_of_participants_not_all(message)
    if len(list_of_participants) > 0:
        markup = telebot.types.InlineKeyboardMarkup()
        for part in list_of_participants:
            contest_button = telebot.types.InlineKeyboardButton(part[0], callback_data=f'award_team_{db.get_id_team_from_name(message, str(part[0]))}')
            markup.add(contest_button)
        bot.send_message(message.chat.id, 'Оберіть команду, якій хочете поставити бал!\nЯкщо не хочете голосувати, просто пропустіть.', reply_markup=markup)


def send_scores(id_message, id_part, max_sc):
    markup = telebot.types.InlineKeyboardMarkup()
    for i in range(1, max_sc + 1):
        score_button = telebot.types.InlineKeyboardButton(
            str(i),
            callback_data=f'award_choice_score_{str(i)}_{id_part}'
        )
        markup.add(score_button)
    bot.send_message(id_message, "Оберіть бал:", reply_markup=markup)


def criteria_scores(message, part_id, part_name):
    global val
    global quantity_check
    criteria = db.get_ids_names_criteria(message)
    ids_jury = db.get_id_jury_from_contest(message)
    max_sc = db.get_max_score(message)
    for id_jury in ids_jury:
        val[f'{int(id_jury[0])}'] = 0
        quantity_check[f'{int(id_jury[0])}'] = True
    send_next_criterion(message, criteria, ids_jury, part_id, max_sc, part_name)


def send_next_criterion(message, criteria, ids_jury, part_id, max_sc, part_name):
    global val
    global quantity_check
    global criteria_points

    if len(criteria_points) == 0:
        criteria_points = [None for _ in range(len(db.get_ids_names_criteria(message)))]

    check_again = [0] * len(ids_jury)
    i = 0
    for id_jury in ids_jury:
        if db.get_all_crit(int(id_jury[0])) >= len(criteria):
            check_again[i] = 1
        else:
            check_again[i] = 0
        i += 1
    if all(item == 1 for item in check_again):
        db.set_end_for_participants(part_id)
        ids_viewer = db.get_ids_of_viewer_to_score(message)
        ids_participants = db.get_ids_of_participants_to_score(message)
        for id_viewer in ids_viewer:
            bot.send_message(int(id_viewer[0]), f"Проголосуйте за команду (учасника) {part_name}!")
            send_scores(int(id_viewer[0]), part_id, db.get_max_score(message))
        for id_part in ids_participants:
            bot.send_message(int(id_part[0]), f"Проголосуйте за команду (учасника) {part_name}!")
            send_scores(int(id_part[0]), part_id, db.get_max_score(message))
        team_selection(message)
        return

    for id_jury in ids_jury:
        current_criterion_index = int(db.get_all_crit(int(id_jury[0])))

        if current_criterion_index >= len(criteria):
            # bot.send_message(int(id_jury[0]), 'Це останній критерій')
            propose_juri_to_change_points(message, int(id_jury[0]))
            return

        if current_criterion_index == val[f'{int(id_jury[0])}'] and current_criterion_index < len(criteria) and quantity_check[f'{int(id_jury[0])}']:
            crit = criteria[current_criterion_index]
            bot.send_message(int(id_jury[0]), f'{int(crit[0])}. {crit[1]}')
            quantity_check[f'{int(id_jury[0])}'] = False

            markup = telebot.types.InlineKeyboardMarkup()
            for i in range(1, max_sc + 1):
                score_button = telebot.types.InlineKeyboardButton(
                    str(i),
                    callback_data=f'_{str(i)}_{str(id_jury[0])}_{part_name}_{str(crit[0])}'
                )
                markup.add(score_button)

            bot.send_message(int(id_jury[0]), "Оберіть бал:", reply_markup=markup)


def add_score_to_sheet(message, id_jury, sc, part_name, crit):
    start_col = 1
    start_row = 1
    number_of_jury = db.get_number_of_jury(message)
    number_of_criteria = db.get_number_of_criteria(message)
    number_of_participants = db.get_number_of_participants(message)
    spreadsheet_id = db.get_sheet_id(message)
    name_jury = db.get_name_jury(id_jury)
    service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    ))
    range_names = [f"B1:B{(2 + number_of_jury) * number_of_participants}"]
    result = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=range_names).execute()
    ranges = result.get('valueRanges', [])
    for range_data in ranges:
        values = range_data.get('values', [])
        for row in range(len(values)):
            for col in range(len(values[row])):
                if values[row][col] == part_name:
                    start_row = row + 1

    temp = int(start_row + 2)
    range_names = [f"A{temp}:A{temp - 1 + number_of_jury}"]
    result = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=range_names).execute()
    ranges = result.get('valueRanges', [])
    for range_data in ranges:
        values = range_data.get('values', [])
        for row in range(len(values)):
            for col in range(len(values[row])):
                if values[row][col] == name_jury:
                    temp += int(row)

    range_names = [f"B2:{chr(1 + number_of_criteria + 64)}2"]
    result = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=range_names).execute()
    ranges = result.get('valueRanges', [])
    for range_data in ranges:
        values = range_data.get('values', [])
        for row in range(len(values)):
            for col in range(len(values[row])):
                if values[row][col] == crit:
                    start_col = col + 2

    start_row = int(temp)
    data = [
        {
            'range': f"{chr(start_col + 64)}{start_row}",
            'values': [[sc]]
        }
    ]
    body = {
        'valueInputOption': 'USER_ENTERED',
        'data': data
    }
    service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()


def change_points(message):
    ids_participants = db.get_ids_of_participants(message)
    markup = telebot.types.InlineKeyboardMarkup()
    for id_part in ids_participants:
        contest_button = telebot.types.InlineKeyboardButton(int(id_part[0]), callback_data=f'change_points_jury_{int(id_part[0])}')
        markup.add(contest_button)
    bot.send_message(message.chat.id, 'Оберіть команду (учасника), якій хочете змінити бали чи просто продивитись їх:', reply_markup=markup)


def get_points_part(message, data):
    start_row = 1
    values = None
    number_of_jury = db.get_number_of_jury(message)
    number_of_criteria = db.get_number_of_criteria(message)
    number_of_participants = db.get_number_of_participants(message)
    spreadsheet_id = db.get_sheet_id(message)
    name_jury = db.get_name_jury(int(message.chat.id))
    part_name = db.get_name_participants(int(data))
    service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    ))
    range_names = [f"B1:B{(2 + number_of_jury) * number_of_participants}"]
    result = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=range_names).execute()
    ranges = result.get('valueRanges', [])
    for range_data in ranges:
        values = range_data.get('values', [])
        for row in range(len(values)):
            for col in range(len(values[row])):
                if values[row][col] == part_name:
                    start_row = row + 1

    temp = int(start_row + 2)
    range_names = [f"A{temp}:A{temp - 1 + number_of_jury}"]
    result = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=range_names).execute()
    ranges = result.get('valueRanges', [])
    for range_data in ranges:
        values = range_data.get('values', [])
        for row in range(len(values)):
            for col in range(len(values[row])):
                if values[row][col] == name_jury:
                    temp += int(row)

    range_names = [f"B{temp}:{chr(1 + number_of_criteria + 64)}{temp}"]
    result = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=range_names).execute()
    ranges = result.get('valueRanges', [])
    for range_data in ranges:
        values = range_data.get('values', [])

    propose_to_change(message, values)


def propose_to_change(message, values):
    criteria = db.get_ids_names_criteria(message)
    max_sc = db.get_max_score(message)
    markup = telebot.types.InlineKeyboardMarkup()
    change_button = telebot.types.InlineKeyboardButton('Змінити', callback_data='change_points')
    leave_button = telebot.types.InlineKeyboardButton('Залишити', callback_data='leave_points')
    markup.add(change_button, leave_button)

    criterion_as_string = '\n'.join([f'{i + 1}. {criterion[1]} - *{values[i]}/{max_sc}*;' for i, criterion in enumerate(criteria)])

    bot.send_message(message.chat.id, f'{criterion_as_string} \n\nЯкщо Ви переглянули своє рішення щодо одного з критеріїв, Ви можете змінити його, натиснувши кнопку "Змінити". Якщо Вас усе влаштовує, натисніть кнопку "Залишити".', reply_markup=markup, parse_mode='Markdown')


def propose_juri_to_change_points(message, id_jury):
    global criteria_points

    criteria = db.get_ids_names_criteria(message)
    max_sc = db.get_max_score(message)
    markup = telebot.types.InlineKeyboardMarkup()
    change_button = telebot.types.InlineKeyboardButton('Змінити', callback_data='change_points')
    leave_button = telebot.types.InlineKeyboardButton('Залишити', callback_data='leave_points')
    markup.add(change_button, leave_button)

    criterion_as_string = '\n'.join([f'{i + 1}. {criterion[1]} - *{criteria_points[i]}/{max_sc}*;' for i, criterion in enumerate(criteria)])

    bot.send_message(id_jury, f'Ви проставили бали по всім критеріям: \n\n{criterion_as_string} \n\nЯкщо Ви переглянули своє рішення щодо одного з критеріїв, Ви можете змінити його, натиснувши кнопку "Змінити". Якщо Вас усе влаштовує, натисніть кнопку "Залишити".', reply_markup=markup, parse_mode='Markdown')


def ask_criterion_to_change(message):
    bot.send_message(message.chat.id, 'Введіть номер критерію, бал якого хочете змінити:')
    bot.register_next_step_handler(message, ask_new_score_for_criterion)


def reask_criterion_to_change(message):
    bot.send_message(message.chat.id, 'Даний номер критерію не валідний, спробуйте ще раз:')
    bot.register_next_step_handler(message, ask_new_score_for_criterion)


def ask_new_score_for_criterion(message):
    global current_part_name
    global current_criteria_points_idx

    criteria = db.get_ids_names_criteria(message)

    try:
        criterion_idx = int(message.text)
        if criterion_idx <= 0 or criterion_idx > len(criteria):
            raise
    except ValueError:
        bot.send_message(message.chat.id, "Неправильне значення!")
        reask_criterion_to_change(message)
        return

    max_sc = db.get_max_score(message)
    crit = criteria[criterion_idx - 1]
    current_criteria_points_idx = criterion_idx - 1

    markup = telebot.types.InlineKeyboardMarkup()
    for i in range(1, max_sc + 1):
        score_button = telebot.types.InlineKeyboardButton(
            str(i),
            callback_data=f'_{str(i)}_{str(message.chat.id)}_{current_part_name}_{str(crit[0])}'
        )
        markup.add(score_button)
    bot.send_message(message.chat.id, "Оберіть бал:", reply_markup=markup)


def max_score(message):
    try:
        max_sc = int(message.text)
        if max_sc <= 0:
            raise ValueError
        else:
            db.set_max_score(message, max_sc)
            team_selection(message)
            send_messages_for_part_and_viewer(message)
    except ValueError:
        bot.reply_to(message, 'Вказана кількість не валідна, спробуйте ще раз:')
        bot.register_next_step_handler(message, max_score)


def create(title, message):
    global organizer_table_title
    organizer_table_title = title

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
        db.set_sheet_id(message, spreadsheet_id)

        drive = build("drive", "v3", credentials=creds)
        permission = {
            "type": "anyone",
            "role": "writer",
        }
        drive.permissions().create(fileId=spreadsheet_id, body=permission).execute()

        link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=0"
        add_value_to_sheet(message, spreadsheet_id, service)
        bot.send_message(message.chat.id, f"Посилання на Google таблицю: {link}")
        bot.send_message(message.chat.id, "Ви можете поділитись цим посиланням з іншими організаторами, якщо вони є!")
        bot.send_message(message.chat.id, "Напишіть, який максимальний балл на цьому конкурсі!")
        bot.register_next_step_handler(message, max_score)
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error


def add_value_to_sheet(message, spreadsheet_id, service):
    number_of_participants = db.get_number_of_participants(message)
    number_of_criteria = db.get_number_of_criteria(message)
    number_of_jury = db.get_number_of_jury(message)

    list_of_participants = db.get_list_of_participants(message)
    list_of_criteria = db.get_list_of_criteria(message)
    list_of_jury = db.get_list_of_jury(message)

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


def team_selection(message):
    if db.get_voting_status(db.get_contest_id(message)) == 2:
        second_type_of_voting(message)
    elif db.get_voting_status(db.get_contest_id(message)) == 1:
        ids_jury = db.get_id_jury_from_contest(message)
        for id_jury in ids_jury:
            db.set_null_for_all_crit(int(id_jury[0]))

        list_of_participants_all = db.get_list_of_participants_all(message)
        list_of_participants = db.get_list_of_participants(message)
        ids_of_participants = db.get_ids_of_participants(message)
        id_org = db.get_id_organizer(message)
        if len(list_of_participants) > 0:
            markup = telebot.types.InlineKeyboardMarkup()
            for i in range(len(list_of_participants)):
                contest_button = telebot.types.InlineKeyboardButton(list_of_participants[i][0], callback_data=f'team_{ids_of_participants[i][0]}')
                markup.add(contest_button)
            bot.send_message(id_org, 'Оберіть команду, яка зараз буде виступати:', reply_markup=markup)
        else:
            bot.send_message(id_org, 'Учасників немає!')
            if len(list_of_participants_all) > 0:
                score_rating(message)
    else:
        bot.send_message(message.chat.id, "Голосування ще не почалось! Натисніть на /startvoting")


def second_type_of_voting(message):
    ids_jury = db.get_id_jury_from_contest(message)
    for id_jury in ids_jury:
        markup = telebot.types.InlineKeyboardMarkup()
        yes_button = telebot.types.InlineKeyboardButton("Так", callback_data='jury_voting_1')
        no_button = telebot.types.InlineKeyboardButton("Ні", callback_data='jury_voting_0')
        markup.add(yes_button, no_button)
        bot.send_message(int(id_jury[0]), 'Чи хочете Ви почати голосування?', reply_markup=markup)


def jury_awarding_score(message):
    list_of_participants = db.get_list_of_participants(message)
    ids_of_participants = db.get_ids_of_participants(message)
    if len(list_of_participants) > 0 and db.get_second_voting(message) < len(list_of_participants):
        markup = telebot.types.InlineKeyboardMarkup()
        for i in range(len(list_of_participants)):
            contest_button = telebot.types.InlineKeyboardButton(list_of_participants[i][0], callback_data=f'team_{ids_of_participants[i][0]}')
            markup.add(contest_button)
        bot.send_message(message.chat.id, 'Оберіть команду чи учасника, яку хочете оцінити!\n'
                                          'Якщо хочете змінити бал, знову нажміть на потрібну команду '
                                          '(учасника).', reply_markup=markup)
    elif db.get_second_voting(message) >= len(list_of_participants):
        markup = telebot.types.InlineKeyboardMarkup()
        yes_button = telebot.types.InlineKeyboardButton("Завершити", callback_data=f'secondvoting_0')
        no_button = telebot.types.InlineKeyboardButton("Повернутись", callback_data=f'secondvoting_1')
        markup.add(yes_button, no_button)
        bot.send_message(message.chat.id, 'Ви можете завершити голосування або повернутись, щоб змінити бали!', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, 'Учасників немає!')


def jury_criteria(message, part_name, current_criteria_index):
    criteria = db.get_ids_names_criteria(message)
    if current_criteria_index < len(criteria):
        crit = criteria[current_criteria_index]
        bot.send_message(message.chat.id, f'{int(crit[0])}. {crit[1]}')
        markup = telebot.types.InlineKeyboardMarkup()
        for i in range(1, db.get_max_score(message) + 1):
            score_button = telebot.types.InlineKeyboardButton(
                str(i),
                callback_data=f'_{str(i)}_{message.chat.id}_{part_name}_{str(crit[0])}'
            )
            markup.add(score_button)
        bot.send_message(message.chat.id, "Оберіть бал:", reply_markup=markup)
    else:
        db.set_null_for_all_crit(message.chat.id)
        jury_awarding_score(message)


def check_all_jury(message):
    number_of_participants = db.get_number_of_participants(message)
    number_of_criteria = db.get_number_of_criteria(message)
    number_of_jury = db.get_number_of_jury(message)

    start_col = 1
    start_row = 1

    spreadsheet_id = db.get_sheet_id(message)
    service = build('sheets', 'v4', credentials=service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    ))

    for i in range(number_of_participants):
        range_names = [f"B{start_row + 2}:{chr(start_col + number_of_criteria + 64)}{start_row + 1 + int(number_of_jury)}"]
        result = service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id, ranges=range_names).execute()
        ranges = result.get('valueRanges', [])
        for range_data in ranges:
            values = range_data.get('values', [])
            for row in range(len(values)):
                for col in range(len(values[row])):
                    if not (int(values[row][col]) > 0):
                        return False
        start_row += 2 + number_of_jury
    return True


def score_rating(message):
    markup = telebot.types.InlineKeyboardMarkup()
    button = telebot.types.InlineKeyboardButton("Завершити", callback_data='end_contest')
    markup.add(button)
    bot.send_message(message.chat.id, 'Якщо Ви готові завершити голосування, натисніть на кнопку:', reply_markup=markup)


def end_contest(message):
    global team_scores

    sh = sa.open(organizer_table_title)
    wks = sh.worksheet('Sheet1')

    number_of_criteria = db.get_number_of_criteria(message)
    number_of_juries = db.get_number_of_jury(message)
    number_of_participants = db.get_number_of_participants(message)

    indent = 0
    for i in range(number_of_participants):
        team_name = wks.get(f'B{indent + 1}')
        points = wks.get(f'B{indent + 3}:{ALPHABET[1 + number_of_criteria]}{indent + 2 + number_of_juries}')

        team_name = team_name[0][0]

        team_score = 0
        for juri_points in points:
            team_score += sum([int(point) for point in juri_points])

        team_scores += [TeamScore(team_name, team_score)]
        indent += 2 + number_of_juries

    rated = sorted(team_scores, key=lambda team_sc: team_sc.score, reverse=True)

    temp = indent + 2
    wks.update(f'B{indent + 1}', 'Рейтинг')
    wks.update(f'D{indent + 1}', 'Приз глядацький симпатій')
    wks.update(f'A{indent + 2}', 'Місце')
    wks.update(f'B{indent + 2}', 'Команда')
    wks.update(f'C{indent + 2}', 'Кількість балів')
    indent += 3
    for i, team_score in enumerate(rated):
        wks.update(f'A{indent}', i + 1)
        wks.update(f'B{indent}', team_score.name)
        wks.update(f'C{indent}', team_score.score)
        indent += 1

    if int(db.get_voting_status(db.get_contest_id(message))) == 2:
        win = people_choice_award(message)
        wks.update(f'D{temp}', win)

    bot.send_message(message.chat.id, 'Рейтинг складено, перевірте таблицю.')

    team_scores = []
    delete_all(message)


def people_choice_award(message):
    ids_participants = db.get_ids_of_participants_end(message)
    max_average = 0
    win = 0
    for id_part in ids_participants:
        temp = db.get_voting_scores(int(id_part[0])) / db.get_number_of_voters(int(id_part[0]))
        if temp > max_average:
            max_average = float(temp)
            win = int(id_part[0])

    return str(db.get_name_participants(win))


def delete_all(message):
    ids_jury = db.get_id_jury_from_contest(message)
    for id_jury in ids_jury:
        db.delete_from_tables_id(int(id_jury[0]))
        db.delete_from_users_id(int(id_jury[0]))

    ids_participants = db.get_ids_of_participants_all(message)
    for id_part in ids_participants:
        db.delete_from_tables_id(int(id_part[0]))
        db.delete_from_users_id(int(id_part[0]))

    ids_viewer = db.get_ids_of_viewer(message)
    for id_viewer in ids_viewer:
        db.delete_from_tables_id(int(id_viewer[0]))
        db.delete_from_users_id(int(id_viewer[0]))

    db.delete_contest(db.get_contest_id(message))
    db.delete_from_tables(message)
    db.delete_from_users(message)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global check
    global project_type
    global current_criteria
    global default_startup_criteria
    global default_design_criteria
    global criteria_points
    global current_part_name
    global current_criteria_points_idx

    if call.data == 'viewer':
        db.add_user(call.message, "viewer")
        db.create_table_viewer()
        db.add_user_viewer(call.message)
        bot.send_message(call.message.chat.id, 'Введіть Ваш нікнейм.')
        bot.register_next_step_handler(call.message, process_nickname_step)
        remove_message_buttons(call.message)
    elif call.data == 'organizer':
        db.add_user(call.message, "organizer")
        db.create_table_organizer()
        db.add_user_organizer(call.message)
        db.create_table_organizer()
        bot.send_message(call.message.chat.id, 'Введіть Ваше ім\'я!')
        bot.register_next_step_handler(call.message, process_name_step)
        remove_message_buttons(call.message)
        return
    elif call.data == 'jury':
        db.add_user(call.message, "jury")
        db.create_table_jury()
        db.add_user_jury(call.message)
        bot.send_message(call.message.chat.id, 'Введіть Ваше ім\'я!')
        bot.register_next_step_handler(call.message, process_name_step)
        remove_message_buttons(call.message)
        return
    elif call.data == 'participant':
        db.add_user(call.message, "participant")
        db.create_table_participant()
        db.add_user_participant(call.message)
        bot.send_message(call.message.chat.id, 'Введіть команду, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_team_step)
        remove_message_buttons(call.message)
        return

    if call.data == 'yes':
        check = True
        bot.send_message(call.message.chat.id, 'Введіть компанію, яку Ви представляєте.')
        bot.register_next_step_handler(call.message, process_company_step)
        remove_message_buttons(call.message)
        return
    elif call.data == 'no':
        bot.reply_to(call.message, 'Щоб Ваші бали на конкурсі були АНОНІМізовані, введіть нікмейм!')
        bot.register_next_step_handler(call.message, process_nickname_step)
        remove_message_buttons(call.message)
        return

    if call.data == 'add_contest':
        bot.send_message(call.message.chat.id, 'Введіть назву конкурсу.')
        bot.register_next_step_handler(call.message, process_contest_name_step)
        remove_message_buttons(call.message)
    elif call.data == 'no_contest':
        bot.send_message(call.message.chat.id, "Коли захочете додати конкурс, натисніть /addcontest")

    if call.data == 'start_registration':
        if db.is_organizer(call.message):
            db.start_registration(call.message)
            bot.send_message(call.message.chat.id, 'Реєстрація на цей конкурс почалась!')
            add_criteria(call.message)
        else:
            bot.send_message(call.message.chat.id, 'Тільки організатори можуть почати реєстрацію.')
        remove_message_buttons(call.message)
    elif call.data == 'dont_start_registration':
        bot.send_message(call.message.chat.id, 'Введіть /startregistration , коли захочете почати реєстрацію!')
        remove_message_buttons(call.message)

    if call.data == 'start_voting':
        if db.is_organizer(call.message):
            db.end_registration(call.message)
            bot.send_message(call.message.chat.id, "Є два види голосувань:\n"
                                                   "Голосування з виступами - це голосування, в якому команди чи "
                                                   "учасники представляють свій проєкт на конкурсі та в якому організатор сам обирає,"
                                                   " яка команда чи учасник зараз буде виступати!\n"
                                                   "Голосування звичайне (без виступів) - це голосування, де немає публічних виступів, "
                                                   "в якому жюрі самі обирають команду чи учаснику, яким хочуть поставити бали!")
            types_of_voting(call.message)
        else:
            bot.send_message(call.message.chat.id, 'Тільки організатори можуть почати реєстрацію.')
        remove_message_buttons(call.message)
    elif call.data == 'dont_start_voting':
        bot.send_message(call.message.chat.id, 'Введіть /startvoting , коли захочете почати голосування!')
        remove_message_buttons(call.message)

    if call.data.startswith('join_contest_') and call.data[-1].isdigit() and db.get_role_from_users(call.message) == 'jury':
        contest_id = int(call.data.split('_')[2])
        if db.get_registration_status(contest_id):
            db.set_id_jury(call.message, contest_id)
            bot.send_message(call.message.chat.id, 'Ви зареєстровані')
        else:
            bot.send_message(call.message.chat.id, "Реєстрація на цей конкурс недоступна!")
            db.delete_from_tables(call.message)
            db.delete_from_users(call.message)
        remove_message_buttons(call.message)
    elif call.data.startswith('join_contest_') and call.data[-1].isdigit() and db.get_role_from_users(call.message) == 'participant':
        contest_id = int(call.data.split('_')[2])
        if db.get_registration_status(contest_id):
            db.set_id_participant(call.message, contest_id)
            bot.send_message(call.message.chat.id, 'Ви зареєстровані')
        else:
            bot.send_message(call.message.chat.id, "Реєстрація на цей конкурс недоступна!")
            db.delete_from_tables(call.message)
            db.delete_from_users(call.message)
        remove_message_buttons(call.message)
    elif call.data.startswith('join_contest_') and call.data[-1].isdigit() and db.get_role_from_users(call.message) == 'viewer':
        contest_id = int(call.data.split('_')[2])
        if db.get_voting_status(contest_id) > 0:
            db.set_id_viewer(call.message, contest_id)
            bot.send_message(call.message.chat.id, 'Ви зареєстровані')
        else:
            bot.send_message(call.message.chat.id, "Ви зможете приєднатись до цього конкурсу тільки під час голосування!")
            db.delete_from_tables(call.message)
            db.delete_from_users(call.message)
        remove_message_buttons(call.message)

    if call.data.startswith('voting_'):
        type_of_voting = int(call.data.split('_')[1])
        db.start_voting(call.message, type_of_voting)
        bot.send_message(call.message.chat.id, 'Голосування почалось!')
        send_messages(call.message)
        remove_message_buttons(call.message)

    if call.data == 'add_criteria':
        db.create_table_criteria()
        start_criteria(call.message)
        remove_message_buttons(call.message)
    elif call.data == 'dont_add_criteria':
        bot.send_message(call.message.chat.id, 'Введіть /criteria , коли захочете додати критерії!')
        remove_message_buttons(call.message)
    elif call.data == 'process_startup_criteria':
        project_type = 'startup'
        current_criteria = default_startup_criteria
        show_current_criteria(call.message, current_criteria)
        remove_message_buttons(call.message)
    elif call.data == 'process_design_criteria':
        project_type = 'design'
        current_criteria = default_design_criteria
        show_current_criteria(call.message, current_criteria)
        remove_message_buttons(call.message)
    elif call.data == 'create_criteria':
        request_count_of_criteria(call.message)
        remove_message_buttons(call.message)
    elif call.data == 'change_criteria':
        request_criteria_number(call.message)
        remove_message_buttons(call.message)
    elif call.data == 'leave_criteria':
        db.create_table_criteria()
        add_criteria_to_db(call.message)
        remove_message_buttons(call.message)
    elif call.data == 'add_criterion':
        request_criterion_to_add(call.message)
        remove_message_buttons(call.message)
    elif call.data == 'remove_criterion':
        request_criterion_number_to_remove(call.message)
        remove_message_buttons(call.message)

    if call.data.startswith('team_'):
        data = call.data.split('_')
        part_id = int(data[1])
        part_name = db.get_name_participants(part_id)
        if db.get_voting_status(db.get_contest_id(call.message)) == 1:
            send_messages_jury_about_team(call.message, part_id, part_name)
        elif db.get_voting_status(db.get_contest_id(call.message)) == 2:
            current_criteria_index = 0
            db.set_second_voting(call.message, db.get_second_voting(call.message) + 1)
            jury_criteria(call.message, part_name, current_criteria_index)

        set_new_message_text(call.message, 'Виступає команда: ' + part_name)

    if call.data.startswith('_'):
        data = call.data.split('_')
        id_jury = int(data[2])
        sc = int(data[1])
        criteria_points[current_criteria_points_idx] = sc
        current_criteria_points_idx += 1
        part_name = str(data[3])
        current_part_name = part_name
        part_id = db.get_id_participants_from_name(call.message, part_name)
        criteria = db.get_ids_names_criteria(call.message)
        crit = db.get_name_criteria(call.message, data[4])

        add_score_to_sheet(call.message, id_jury, sc, part_name, crit)
        current_criterion_index = int(db.get_all_crit(id_jury)) + 1

        if current_criterion_index <= len(criteria):
            db.set_all_crit(call.message, current_criterion_index, id_jury)

        if db.get_voting_status(db.get_contest_id(call.message)) == 1:
            criteria = db.get_ids_names_criteria(call.message)
            ids_jury = db.get_id_jury_from_contest(call.message)

            # current_criterion_index = db.get_all_crit(id_jury) + 1
            val[f'{id_jury}'] = current_criterion_index
            quantity_check[f'{id_jury}'] = True

            send_next_criterion(call.message, criteria, ids_jury, part_id, db.get_max_score(call.message), part_name)
        elif db.get_voting_status(db.get_contest_id(call.message)) == 2:
            jury_criteria(call.message, part_name, current_criterion_index)
        remove_message_buttons(call.message)
        set_new_message_text(call.message, 'Обраний бал - ' + str(sc))

    if call.data.startswith('jury_voting_'):
        if call.data.split('_')[2]:
            jury_awarding_score(call.message)
        elif not call.data.split('_')[2]:
            bot.send_message(call.message.chat.id, "Натисніть /startvotingjury , щоб почати голосування!")
        remove_message_buttons(call.message)

    if call.data.startswith('secondvoting_'):
        data = call.data.split('_')
        if int(data[1]) == 1:
            db.set_second_voting(call.message, db.get_second_voting(call.message) - 1)
            jury_awarding_score(call.message)
        elif int(data[1]) == 0:
            if check_all_jury(call.message):
                score_rating(call.message)
        remove_message_buttons(call.message)

    if call.data == 'change_points':
        ask_criterion_to_change(call.message)
        remove_message_buttons(call.message)
    if call.data == 'leave_points':
        criteria_points = []
        current_criteria_points_idx = 0
        current_part_name = None
        remove_message_buttons(call.message)

    if call.data.startswith('criteria_'):
        if call.data.split('_')[1] == 'delete':
            db.delete_criteria(call.message)
        elif call.data.split('_')[1] == 'no':
            pass
        remove_message_buttons(call.message)

    if call.data.startswith('choice_award_'):
        data = call.data.split('_')[2]
        if bool(data):
            db.set_award(call.message)
            performed_teams(call.message)
        elif not bool(data):
            bot.send_message(call.message.chat.id, "Натисніть /choice_award , якщо будете готові проголосувати!")
        remove_message_buttons(call.message)

    if call.data.startswith('award_team_'):
        data = call.data.split('_')[2]
        send_scores(call.message.chat.id, data, db.get_max_score(call.message))
        remove_message_buttons(call.message)

    if call.data.startswith('award_choice_score_'):
        score = call.data.split('_')[3]
        id_part = call.data.split('_')[4]
        db.set_voting_scores(id_part, int(db.get_voting_scores(id_part)) + int(score))
        db.set_number_of_voters(id_part, int(db.get_number_of_voters(id_part)) + 1)
        remove_message_buttons(call.message)

    if call.data.startswith('delete_contest_'):
        data = call.data.split('_')[2]
        if int(data) == 0:
            pass
        else:
            db.delete_criteria_from_id(int(data))
            db.delete_contest(int(data))
            bot.send_message(call.message.chat.id, "Конкурс видалено!")
        remove_message_buttons(call.message)

    if call.data.startswith('change_points_jury_'):
        data = call.data.split('_')[3]
        get_points_part(call.message, data)

    if call.data == 'end_contest':
        end_contest(call.message)


bot.polling()
