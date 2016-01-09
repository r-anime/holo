from logging import debug, error
import sqlite3

from .models import Stream

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
			key		TEXT NOT NULL
		)""")
		self.q.executemany("INSERT OR IGNORE INTO ShowTypes (key) VALUES (?)", [("tv",), ("movie",), ("ova",)])
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Shows (
			id		INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			name	TEXT NOT NULL,
			length	INTEGER,
			type	INTEGER NOT NULL,
			FOREIGN KEY(type) REFERENCES ShowTypes(id)
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Services (
			id		INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			key		TEXT NOT NULL UNIQUE,
			enabled	INTEGER NOT NULL DEFAULT 0
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Streams (
			service		TEXT NOT NULL,
			show		INTEGER NOT NULL,
			show_key	TEXT NOT NULL,
			name		TEXT,
			remote_offset	INTEGER DEFAULT 0,
			display_offset	INTEGER DEFAULT 0,
			active		INTEGER NOT NULL DEFAULT 1,
			FOREIGN KEY(service) REFERENCES Services(id),
			FOREIGN KEY(show) REFERENCES Shows(id)
		)""")
		self.commit()
	
	def register_services(self, services):
		self.q.execute("UPDATE Services SET enabled = 0")
		for service in services:
			self.q.execute("INSERT OR IGNORE INTO Services (key) VALUES (?)", (service,))
			self.q.execute("UPDATE Services SET enabled = 1 WHERE key = ?", (service,))
		self.commit()
	
	def get_service_streams(self, service=None, service_key=None, active=True):
		if service:
			service_key = service.key
		debug("Getting all streams for service {}".format(service_key))
		if service_key is None:
			return list()
		
		# Get service ID
		self.q.execute("SELECT id FROM Services WHERE key = ?", (service_key,))
		service_id = self.q.fetchone()
		if service_id is None:
			error("Service \"{}\" not found".format(service_key))
			return list()
		service_id = service_id[0]
		
		# Get all streams with service ID
		self.q.execute("SELECT service, show, show_key, remote_offset, display_offset FROM Streams WHERE service = ? AND active = ?", (service_id, 1 if active else 0))
		streams = self.q.fetchall()
		streams = [Stream(stream[0], stream[1], stream[2], stream[3], stream[4]) for stream in streams]
		return streams
	
def living_in(the_database):
	# wow wow
	db = sqlite3.connect(the_database)
	db.execute("PRAGMA foreign_keys=ON")
	return DatabaseDatabase(db)
