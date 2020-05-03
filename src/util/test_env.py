# coding=UTF-8
import ujson
import pymysql
import retrying
from bs4 import BeautifulSoup
import requests
from src.util import settings

connection = pymysql.connect(host=settings.MySQL["host"],
                             user=settings.MySQL["user"],
                             password=settings.MySQL["password"],
                             db=settings.MySQL["db"],
                             charset=settings.MySQL["charset"],
                             cursorclass=pymysql.cursors.DictCursor)
connection.close()
