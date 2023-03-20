import sqlite3
import sys

con = sqlite3.connect(sys.argv[1])

cur = con.cursor()

tables = cur.execute(
    "select name from sqlite_master where type = 'table' and name like 'opencivicdata_%'"
).fetchall()

for (table_name,) in tables:
    cur.execute(f"select * from {table_name} limit 1")
    res = cur.fetchall()
    if not res:
        cur.execute(f"drop table {table_name}")
