import sqlite3

class DatabaseDatabase:
	def __init__(self, db):
		self._db = db
		self.q = db.cursor()
		self._verify_tables()
	
	def __getattr__(self, attr):
		if attr in self.__dict__:
			return getattr(self, attr)
		return getattr(self._db, attr)
	
	def _verify_tables(self):
		self.q.execute("""CREATE TABLE IF NOT EXISTS ShowTypes (
			id		INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			name	TEXT NOT NULL
		);""")
		self.q.execute("""CREATE TABLE IF NOT EXISTS Shows (
			id		INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			name	TEXT NOT NULL,
			length	INTEGER,
			type	INTEGER NOT NULL,
			FOREIGN KEY(type) REFERENCES ShowTypes(id)
		);""")
		self.commit()
	
def living_in(the_database):
	# wow wow
	db = sqlite3.connect(the_database)
	db.execute("PRAGMA foreign_keys=ON")
	return DatabaseDatabase(db)
