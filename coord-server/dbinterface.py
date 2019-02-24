import mysql.connector as mysqlc
import custom_config

class DatabaseInterface(object):
  def __init__(self):
    self._cnx = mysqlc.connect(**custom_config.Config.dbinfo())
    self._cursor = self._cnx.cursor()

  def query(self, query, params):
    return self._cursor.execute(query, params)

  def query_one(self, query, params):
    self.query(query, params)
    res = self._cursor.fetchone()
    self._cursor.fetchall() # Clear the cursor
    return res

  def query_all(self, query, params):
    self.query(query, params)
    return self._cursor.fetchall()

  def update(self, query, params):
    self.query(query, params)
    self._cnx.commit()
    return self._cursor.rowcount

  def __del__(self):
    self._cnx.close()