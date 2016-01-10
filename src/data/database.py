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
		self.q.executemany("INSERT OR IGNORE INTO ShowTypes (id, key) VALUES (?, ?)", [(1, "tv",), (2, "movie",), (3, "ova",)])
		
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
			id			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			service		TEXT NOT NULL,
			show		INTEGER NOT NULL,
			show_key	TEXT NOT NULL,
			name		TEXT,
			remote_offset	INTEGER NOT NULL DEFAULT 0,
			display_offset	INTEGER NOT NULL DEFAULT 0,
			active		INTEGER NOT NULL DEFAULT 1,
			FOREIGN KEY(service) REFERENCES Services(id),
			FOREIGN KEY(show) REFERENCES Shows(id)
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Episodes (
			show		INTEGER NOT NULL,
			episode		INTEGER NOT NULL,
			post_url	TEXT,
			FOREIGN KEY(show) REFERENCES Shows(id)
		)""")
		
		self.commit()
	
	def setup_test_data(self):
		self.q.execute("""INSERT OR IGNORE INTO Shows (id, name, length, type)
			VALUES (1, 'GATE', 12, 1)""")
		self.q.execute("""INSERT OR IGNORE INTO Streams (id, service, show, show_key, name)
			VALUES (1, 1, ?, 'gate', 'GATE')""", (self.q.lastrowid,))
		
		self.q.execute("""INSERT OR IGNORE INTO Shows (id, name, length, type)
			VALUES (2, 'Myriad Colors Phantom World', 12, 1)""")
		self.q.execute("""INSERT OR IGNORE INTO Streams (id, service, show, show_key, name)
			VALUES (2, 1, ?, 'myriad-colors-phantom-world', 'Myriad Colors Phantom World')""", (self.q.lastrowid,))
	
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
	
	def stream_has_episode(self, stream, episode_num):
		self.q.execute("SELECT count(*) FROM Episodes WHERE show = ? AND episode = ?", (stream.show, episode_num))
		num_found = self.q.fetchone()[0]
		debug("Found {} entries matching show {}, episode {}".format(num_found, stream.show, episode_num))
		return num_found > 0
	
	def store_episode(self, show_id, episode_num, post_url):
		debug("Inserting episode {} for show {} ({})".format(episode_num, show_id, post_url))
		self.q.execute("INSERT INTO Episodes (show, episode, post_url) VALUES (?, ?, ?)", (show_id, episode_num, post_url))
		self.commit()
	
def living_in(the_database):
	# wow wow
	try:
		db = sqlite3.connect(the_database)
		db.execute("PRAGMA foreign_keys=ON")
	except sqlite3.OperationalError:
		error("Failed to open database, {}".format(the_database))
	return DatabaseDatabase(db)
