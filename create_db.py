import sqlite3

db = sqlite3.connect('recordings.sqlite')

cursor = db.cursor()
cursor.execute('''
    CREATE TABLE recordings(name TEXT UNIQUE NOT NULL, meetingname TEXT, status TEXT)''')
db.commit()
db.close()