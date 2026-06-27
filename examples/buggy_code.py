import os
import sqlite3

PASSWORD = "admin123" 

def get_user(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()

def divide(a, b):
    return a / b  

def read_file(filename):
    f = open(filename, "r")  
    return f.read()

def risky():
    try:
        result = 10 / 0
    except:       
        pass