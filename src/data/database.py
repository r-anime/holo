from logging import debug, error, exception
import sqlite3
from functools import wraps

from .models import Show, Stream, Service, LinkSite, Link

def db_error_default(default_value):
	value = default_value
	
	def decorate(f):
		@wraps(f)
		def protected(*args, **kwargs):
			nonlocal value
			try:
				return f(*args, **kwargs)
			except:
				exception("Database exception thrown")
				return value
		return protected
	return decorate

class DatabaseDatabase:
	def __init__(self, db):
		self._db = db
		self.q = db.cursor()
	
	def __getattr__(self, attr):
		if attr in self.__dict__:
			return getattr(self, attr)
		return getattr(self._db, attr)
	
	# Setup
	
	def setup_tables(self):
		self.q.execute("""CREATE TABLE IF NOT EXISTS ShowTypes (
			id		INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			key		TEXT NOT NULL
		)""")
		self.q.executemany("INSERT OR IGNORE INTO ShowTypes (id, key) VALUES (?, ?)", [(1, "tv",), (2, "movie",), (3, "ova",)])
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Shows (
			id			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			name		TEXT NOT NULL,
			length		INTEGER,
			type		INTEGER NOT NULL,
			has_source	INTEGER NOT NULL DEFAULT 0,
			FOREIGN KEY(type) REFERENCES ShowTypes(id)
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Services (
			id			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			key			TEXT NOT NULL UNIQUE,
			name		TEXT NOT NULL,
			enabled		INTEGER NOT NULL DEFAULT 0
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Streams (
			id			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			service		TEXT NOT NULL,
			show		INTEGER NOT NULL,
			site_key	TEXT NOT NULL,
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
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS LinkSites (
			id			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			key			TEXT NOT NULL UNIQUE,
			name		TEXT NOT NULL,
			enabled		INTEGER NOT NULL DEFAULT 1
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Links (
			link_site	INTEGER NOT NULL,
			show		INTEGER NOT NULL,
			site_key	TEXT NOT NULL,
			FOREIGN KEY(link_site) REFERENCES LinkSites(id)
			FOREIGN KEY(show) REFERENCES Shows(id)
		)""")
		
		self.commit()
	
	def register_services(self, services):
		self.q.execute("UPDATE Services SET enabled = 0")
		for service_key in services:
			service = services[service_key]
			self.q.execute("INSERT OR IGNORE INTO Services (key) VALUES (?)", (service.key,))
			self.q.execute("UPDATE Services SET name = ?, enabled = 1 WHERE key = ?", (service.name, service.key))
		self.commit()
		
	def register_link_sites(self, sites):
		self.q.execute("UPDATE LinkSites SET enabled = 0")
		for site_key in sites:
			site = sites[site_key]
			self.q.execute("INSERT OR IGNORE INTO LinkSites (key) VALUES (?)", (site.key,))
			self.q.execute("UPDATE LinkSites SET name = ?, enabled = 1 WHERE key = ?", (site.name, site.key))
		self.commit()
	
	# Services
	
	@db_error_default(None)
	def get_service(self, id=None, key=None):
		if id is not None:
			self.q.execute("SELECT id, key, name, enabled FROM Services WHERE id = ?", (id,))
		elif key is not None:
			self.q.execute("SELECT id, key, name, enabled FROM Services WHERE key = ?", (key,))
		else:
			error("ID or key required to get service")
			return None
		service = self.q.fetchone()
		return Service(*service)
	
	@db_error_default(None)
	def get_services(self, enabled=True, disabled=False):
		services = list()
		if enabled:
			self.q.execute("SELECT id, key, name, enabled FROM Services WHERE enabled = 1")
			for service in self.q.fetchall():
				services.append(Service(*service))
		if disabled:
			self.q.execute("SELECT id, key, name, enabled FROM Services WHERE enabled = 0")
			for service in self.q.fetchall():
				services.append(Service(*service))
		return services
	
	@db_error_default(None)
	def get_streams(self, service=None, show=None, active=True):
		if service is not None:
			debug("Getting all streams for service {}".format(service.key))
			
			# Get service ID
			self.q.execute("SELECT id FROM Services WHERE key = ?", (service.key,))
			service_id = self.q.fetchone()
			if service_id is None:
				error("Service \"{}\" not found".format(service.key))
				return list()
			service_id = service_id[0]
			
			# Get all streams with service ID
			self.q.execute("SELECT service, show, site_key, name, remote_offset, display_offset, active FROM Streams WHERE service = ? AND active = ?", (service_id, 1 if active else 0))
			streams = self.q.fetchall()
			streams = [Stream(*stream) for stream in streams]
			return streams
		elif show is not None:
			debug("Getting all streams for show {}".format(show.id))
			
			# Get all streams with show ID
			self.q.execute("SELECT service, show, site_key, name, remote_offset, display_offset, active FROM Streams WHERE show = ? AND active = ?", (show.id, 1 if active else 0))
			streams = self.q.fetchall()
			streams = [Stream(*stream) for stream in streams]
			return streams
		else:
			error("A service or show must be provided to get streams")
			return list()
	
	# Links
	
	@db_error_default(None)
	def get_link_site(self, id=None, key=None):
		if id is not None:
			self.q.execute("SELECT id, key, name, enabled FROM Services WHERE id = ?", (id,))
		elif key is not None:
			self.q.execute("SELECT id, key, name, enabled FROM Services WHERE key = ?", (key,))
		else:
			error("ID or key required to get link site")
			return None
		site = self.q.fetchone()
		return LinkSite(*site)
	
	@db_error_default(None)
	def get_link_sites(self, enabled=True, disabled=False):
		sites = list()
		if enabled:
			self.q.execute("SELECT id, key, name, enabled FROM LinkSites WHERE enabled = 1")
			for link in self.q.fetchall():
				sites.append(Link(*link))
		if disabled:
			self.q.execute("SELECT id, key, name, enabled FROM LinkSites WHERE enabled = 0")
			for link in self.q.fetchall():
				sites.append(LinkSite(*link))
		return sites
	
	@db_error_default(None)
	def get_links(self, show=None):
		if show is not None:
			debug("Getting all links for show {}".format(show.id))
			
			# Get all streams with show ID
			self.q.execute("SELECT link_site, show, site_key FROM Links WHERE show = ?", (show.id,))
			links = self.q.fetchall()
			links = [Link(*link) for link in links]
			return links
		else:
			error("A show must be provided to get links")
			return list()
	
	# Shows
	
	@db_error_default(None)
	def get_show(self, stream=None):
		debug("Getting show from database")
		
		# Get show ID
		show_id = None
		if stream:
			show_id = stream.show
		
		# Get show
		if show_id is None:
			error("Show ID not provided to get_show")
			return None
		self.q.execute("SELECT id, name, length, type, has_source FROM Shows WHERE id = ?", (show_id,))
		show = self.q.fetchone()
		show = Show(*show)
		return show
	
	# Episodes
	
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
		return None
	return DatabaseDatabase(db)
