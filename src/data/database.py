from logging import debug, error, exception
import sqlite3, re
from functools import wraps, lru_cache
from unidecode import unidecode

from .models import Show, ShowType, Stream, Service, LinkSite, Link

def living_in(the_database):
	# wow wow
	try:
		db = sqlite3.connect(the_database)
		db.execute("PRAGMA foreign_keys=ON")
	except sqlite3.OperationalError:
		error("Failed to open database, {}".format(the_database))
		return None
	return DatabaseDatabase(db)

# Database

def db_error(f):
	@wraps(f)
	def protected(*args, **kwargs):
		try:
			f(*args, **kwargs)
			return True
		except:
			exception("Database exception thrown")
			return False
	return protected

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
		
		# Set up collations
		self._db.create_collation("alphanum", _collate_alphanum)
	
	def __getattr__(self, attr):
		if attr in self.__dict__:
			return getattr(self, attr)
		return getattr(self._db, attr)
	
	def get_count(self):
		return self.q.fetchone()[0]
	
	# Setup
	
	def setup_tables(self):
		self.q.execute("""CREATE TABLE IF NOT EXISTS ShowTypes (
			id		INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			key		TEXT NOT NULL
		)""")
		self.q.executemany("INSERT OR IGNORE INTO ShowTypes (id, key) VALUES (?, ?)", [(t.value, t.name.lower()) for t in ShowType])
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Shows (
			id			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			name		TEXT NOT NULL,
			length		INTEGER,
			type		INTEGER NOT NULL,
			has_source	INTEGER NOT NULL DEFAULT 0,
			enabled		INTEGER NOT NULL DEFAULT 1,
			FOREIGN KEY(type) REFERENCES ShowTypes(id)
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS ShowNames (
			show		INTEGER NOT NULL,
			name		TEXT NOT NULL
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
			show_id		TEXT,
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
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS LinkSites (
			id			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			key			TEXT NOT NULL UNIQUE,
			name		TEXT NOT NULL,
			enabled		INTEGER NOT NULL DEFAULT 1
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Links (
			show		INTEGER NOT NULL,
			site		INTEGER NOT NULL,
			site_key	TEXT NOT NULL,
			FOREIGN KEY(site) REFERENCES LinkSites(id)
			FOREIGN KEY(show) REFERENCES Shows(id)
		)""")
		
		self.commit()
	
	def register_services(self, services):
		self.q.execute("UPDATE Services SET enabled = 0")
		for service_key in services:
			service = services[service_key]
			self.q.execute("INSERT OR IGNORE INTO Services (key, name) VALUES (?, '')", (service.key,))
			self.q.execute("UPDATE Services SET name = ?, enabled = 1 WHERE key = ?", (service.name, service.key))
		self.commit()
		
	def register_link_sites(self, sites):
		self.q.execute("UPDATE LinkSites SET enabled = 0")
		for site_key in sites:
			site = sites[site_key]
			self.q.execute("INSERT OR IGNORE INTO LinkSites (key, name) VALUES (?, '')", (site.key,))
			self.q.execute("UPDATE LinkSites SET name = ?, enabled = 1 WHERE key = ?", (site.name, site.key))
		self.commit()
	
	# Services
	
	@db_error_default(None)
	@lru_cache(10)
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
	
	@db_error_default(list())
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
	def get_stream(self, id=None):
		if id is not None:
			debug("Getting stream for id {}".format(id))
			
			self.q.execute("SELECT service, show, show_id, show_key, name, remote_offset, display_offset, active FROM Streams WHERE id = ?", (id,))
			stream = self.q.fetchone()
			if stream is None:
				error("Stream {} not found".format(id))
				return None
			stream = Stream(*stream)
			return stream
		else:
			error("Nothing provided to get stream")
			return None
	
	@db_error_default(list())
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
			self.q.execute("SELECT service, show, show_id, show_key, name, remote_offset, display_offset, active FROM Streams WHERE service = ? AND active = ?", (service_id, 1 if active else 0))
			streams = self.q.fetchall()
			streams = [Stream(*stream) for stream in streams]
			return streams
		elif show is not None:
			debug("Getting all streams for show {}".format(show.id))
			
			# Get all streams with show ID
			self.q.execute("SELECT service, show, show_id, show_key, name, remote_offset, display_offset, active FROM Streams WHERE show = ? AND active = ?", (show.id, 1 if active else 0))
			streams = self.q.fetchall()
			streams = [Stream(*stream) for stream in streams]
			return streams
		else:
			error("A service or show must be provided to get streams")
			return list()
	
	@db_error_default(False)
	def has_stream(self, service_key, key):
		service = self.get_service(key=service_key)
		self.q.execute("SELECT count(*) FROM Streams WHERE service = ? AND show_key = ?", (service.id, key))
		return self.get_count() > 0
	
	# Links
	
	@db_error_default(None)
	def get_link_site(self, id=None, key=None):
		if id is not None:
			self.q.execute("SELECT id, key, name, enabled FROM LinkSites WHERE id = ?", (id,))
		elif key is not None:
			self.q.execute("SELECT id, key, name, enabled FROM LinkSites WHERE key = ?", (key,))
		else:
			error("ID or key required to get link site")
			return None
		site = self.q.fetchone()
		if site is None:
			return None
		return LinkSite(*site)
	
	@db_error_default(list())
	def get_link_sites(self, enabled=True, disabled=False):
		sites = list()
		if enabled:
			self.q.execute("SELECT id, key, name, enabled FROM LinkSites WHERE enabled = 1")
			for link in self.q.fetchall():
				sites.append(LinkSite(*link))
		if disabled:
			self.q.execute("SELECT id, key, name, enabled FROM LinkSites WHERE enabled = 0")
			for link in self.q.fetchall():
				sites.append(LinkSite(*link))
		return sites
	
	@db_error_default(list())
	def get_links(self, show=None):
		if show is not None:
			debug("Getting all links for show {}".format(show.id))
			
			# Get all streams with show ID
			self.q.execute("SELECT site, show, site_key FROM Links WHERE show = ?", (show.id,))
			links = self.q.fetchall()
			links = [Link(*link) for link in links]
			return links
		else:
			error("A show must be provided to get links")
			return list()
	
	@db_error_default(None)
	def get_link(self, show, link_site):
		debug("Getting link for show {} and site {}".format(show.id, link_site.key))
		
		self.q.execute("SELECT site, show, site_key FROM Links WHERE show = ? AND site = ?", (show.id, link_site.id))
		link = self.q.fetchone()
		if link is None:
			return None
		link = Link(*link)
		return link
	
	@db_error_default(False)
	def has_link(self, site_key, key):
		site = self.get_link_site(key=site_key)
		self.q.execute("SELECT count(*) FROM Links WHERE site = ? AND site_key = ?", (site.id, key))
		return self.get_count() > 0
	
	@db_error
	def add_link(self, raw_show, show_id, commit=True):
		debug("Inserting link: {}/{}".format(show_id, raw_show))
		
		site = self.get_link_site(key=raw_show.site_key)
		if site is None:
			error("  Invalid site \"{}\"".format(raw_show.site_key))
			return
		site_key = raw_show.show_key
		
		self.q.execute("INSERT INTO Links (show, site, site_key) VALUES (?, ?, ?)", (show_id, site.id, site_key))
		if commit:
			self.commit()
	
	# Shows
	
	@db_error_default(list())
	def get_shows(self, missing_length=False, enabled=True):
		shows = list()
		if missing_length:
			self.q.execute("SELECT id, name, length, type, has_source, enabled FROM Shows WHERE (length IS NULL OR length = '') AND enabled = ?", (enabled,))
			for show in self.q.fetchall():
				shows.append(Show(*show))
		else:
			self.q.execute("SELECT id, name, length, type, has_source, enabled FROM Shows WHERE enabled = ?", (enabled,))
			for show in self.q.fetchall():
				shows.append(Show(*show))
		return shows
	
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
		self.q.execute("SELECT id, name, length, type, has_source, enabled FROM Shows WHERE id = ?", (show_id,))
		show = self.q.fetchone()
		if show is None:
			return None
		show_type = to_show_type(show[4])
		show = Show(*show[:4], show_type, *show[5:])
		return show
	
	@db_error_default(None)
	def add_show(self, raw_show, commit=True):
		debug("Inserting show: {}".format(raw_show))
		
		name = raw_show.name
		length = raw_show.episode_count
		show_type = from_show_type(raw_show.show_type)
		has_source = raw_show.has_source
		self.q.execute("INSERT INTO Shows (name, length, type, has_source) VALUES (?, ?, ?, ?)", (name, length, show_type, has_source))
		show_id = self.q.lastrowid
		
		for name in [raw_show.name]+raw_show.more_names:
			self.q.execute("INSERT INTO ShowNames (show, name) VALUES (?, ?)", (show_id, name))
		
		if commit:
			self.commit()
		return show_id
	
	@db_error
	def set_show_episode_count(self, show, length):
		debug("Updating show episode count in database: {}, {}".format(show.name, length))
		self.q.execute("UPDATE Shows SET length = ? WHERE id = ?", (length, show.id))
		self.commit()
	
	# Episodes
	
	@db_error_default(True)
	def stream_has_episode(self, stream, episode_num):
		self.q.execute("SELECT count(*) FROM Episodes WHERE show = ? AND episode = ?", (stream.show, episode_num))
		num_found = self.q.fetchone()[0]
		debug("Found {} entries matching show {}, episode {}".format(num_found, stream.show, episode_num))
		return num_found > 0
	
	@db_error
	def add_episode(self, show_id, episode_num, post_url):
		debug("Inserting episode {} for show {} ({})".format(episode_num, show_id, post_url))
		self.q.execute("INSERT INTO Episodes (show, episode, post_url) VALUES (?, ?, ?)", (show_id, episode_num, post_url))
		self.commit()
	
	# Searching
	
	@db_error_default(set())
	def search_show_ids_by_names(self, *names):
		shows = set()
		for name in names:
			debug("Searching shows by name: {}".format(name))
			self.q.execute("SELECT show, name FROM ShowNames WHERE name = ? COLLATE alphanum", (name,))
			matched = self.q.fetchall()
			for match in matched:
				debug("  Found match: {} | {}".format(match[0], match[1]))
				shows.add(match[0])
		return shows

# Helper methods

## Conversions



def to_show_type(db_val):
	for st in ShowType:
		if st.value == db_val:
			return st
	return ShowType.UNKNOWN

def from_show_type(st):
	if st is None:
		return None
	return st.value

## Collations

def _collate_alphanum(str1, str2):
	str1 = _alphanum_convert(str1)
	str2 = _alphanum_convert(str2)
	
	if str1 == str2:
		return 0
	elif str1 < str2:
		return -1
	else:
		return 1

_alphanum_regex = re.compile("[^a-zA-Z0-9]+")

def _alphanum_convert(s):
	s = _alphanum_regex.sub("", s)
	s = s.lower()
	return unidecode(s)
