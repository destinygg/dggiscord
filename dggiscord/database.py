from config import cfg
from log import logging
import sqlite3
import datetime

con = sqlite3.connect(cfg['db'])
cur = con.cursor()
