import pymysql


def get_connection():
    return pymysql.connect(host="localhost", user="root", password="qwz220106", database="kezig", charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)
