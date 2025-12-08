import tkinter as tk
from tkinter import messagebox, simpledialog
import sqlite3

class DatabaseManager:
    """Clase para manejar la base de datos de usuarios."""
    def __init__(self, db_name="users.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT UNIQUE NOT NULL,
                                password TEXT NOT NULL,
                                is_admin INTEGER NOT NULL,
                                first_name TEXT,
                                last_name TEXT,
                                dni TEXT,
                                email TEXT,
                                phone TEXT,
                                street TEXT,
                                number TEXT,
                                city TEXT
                              )''')
        self.connection.commit()

    def add_user(self, username, password, is_admin, first_name, last_name, dni, email, phone, street, number, city):
        try:
            self.cursor.execute('''INSERT INTO users (username, password, is_admin, first_name, last_name, dni, email, phone, street, number, city)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                (username, password, is_admin, first_name, last_name, dni, email, phone, street, number, city))
            self.connection.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "El nombre de usuario ya existe.")

    def get_user(self, username):
        self.cursor.execute('''SELECT * FROM users WHERE username = ?''', (username,))
        return self.cursor.fetchone()

    def fetch_all_users(self):
        self.cursor.execute('''SELECT * FROM users''')
        return self.cursor.fetchall()

    def update_user(self, user_id, first_name, last_name, dni, email, phone, street, number, city):
        self.cursor.execute('''UPDATE users SET first_name = ?, last_name = ?, dni = ?, email = ?, phone = ?, street = ?, number = ?, city = ? WHERE id = ?''',
                            (first_name, last_name, dni, email, phone, street, number, city, user_id))
        self.connection.commit()

    def delete_user(self, user_id):
        self.cursor.execute('''DELETE FROM users WHERE id = ?''', (user_id,))
        self.connection.commit()
    def get_user_by_id(self, user_id):
        
        self.cursor.execute('''SELECT * FROM users WHERE id = ?''', (user_id,))
        return self.cursor.fetchone()