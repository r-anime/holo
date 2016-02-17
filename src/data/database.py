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
			enabled		INTEGER NOT NULL DEFAULT 0,
			use_in_post	INTEGER NOT NULL DEFAULT 1
		)""")
		
		self.q.execute("""CREATE TABLE IF NOT EXISTS Streams (
			id			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
			service		TEXT NOT NULL,
			show		INTEGER,
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
	def get_services(self, enabled=True, disabled=False) -> [Service]:
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
			
			self.q.execute("SELECT id, service, show, show_id, show_key, name, remote_offset, display_offset, active FROM Streams WHERE id = ?", (id,))
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
	def get_streams(self, service=None, show=None, active=True, use_in_post=True, unmatched=False):
		# Not the best combination of options, but it's only the usage needed
		if service is not None:
			debug("Getting all streams for service {}".format(service.key))
			service = self.get_service(key=service.key)
			self.q.execute("SELECT id, service, show, show_id, show_key, name, remote_offset, display_offset, active FROM Streams \
							WHERE service = ? AND active = ?", (service.id, 1 if active else 0))
		elif show is not None:
			debug("Getting all streams for show {}".format(show.id))
			self.q.execute("SELECT id, service, show, show_id, show_key, name, remote_offset, display_offset, active FROM Streams \
							WHERE show = ? AND active = ? AND use_in_post = ?", (show.id, active, use_in_post))
		elif unmatched:
			debug("Getting unmatched streams")
			self.q.execute("SELECT id, service, show, show_id, show_key, name, remote_offset, display_offset, active FROM Streams \
							WHERE show IS NULL")
		else:
			error("A service or show must be provided to get streams")
			return list()
		
		streams = self.q.fetchall()
		streams = [Stream(*stream) for stream in streams]
		return streams
	
	@db_error_default(False)
	def has_stream(self, service_key, key):
		service = self.get_service(key=service_key)
		self.q.execute("SELECT count(*) FROM Streams WHERE service = ? AND show_key = ?", (service.id, key))
		return self.get_count() > 0
	
	@db_error
	def add_stream(self, raw_stream, show_id, commit=True):
		debug("Inserting stream: {}".format(raw_stream))
		
		service = self.get_service(key=raw_stream.service_key)
		self.q.execute("INSERT INTO Streams (service, show, show_id, show_key, name, remote_offset, display_offset, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
					   (service.id, show_id, raw_stream.show_id, raw_stream.show_key, raw_stream.name, raw_stream.remote_offset, raw_stream.display_offset, show_id is not None))
		if commit:
			self.commit()
	
	@db_error
	def update_stream(self, stream, show=None, active=None, commit=True):
		debug("Updating stream: show={}".format(show))
		if show is not None:
			self.q.execute("UPDATE Streams SET show = ? WHERE id = ?", (show, stream.id))
		if active is not None:
			self.q.execute("UPDATE Streams SET active = ? WHERE id = ?", (active, stream.id))
		
		if commit:
			self.commit()
	
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
	def get_show(self, id=None, stream=None):
		debug("Getting show from database")
		
		# Get show ID
		if stream and not id:
			id = stream.show
		
		# Get show
		if id is None:
			error("Show ID not provided to get_show")
			return None
		self.q.execute("SELECT id, name, length, type, has_source, enabled FROM Shows WHERE id = ?", (id,))
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
		self.add_show_names(raw_show.name, *raw_show.more_names, id=show_id, commit=commit)
		
		if commit:
			self.commit()
		return show_id
	
	@db_error
	def add_show_names(self, *names, id=None, commit=True):
		self.q.executemany("INSERT INTO ShowNames (show, name) VALUES (?, ?)", [(id, name) for name in names])
		if commit:
			self.commit()
	
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
_romanization_o = re.compile("\bwo\b")

def _alphanum_convert(s):
	#TODO: punctuation is important for some shows to distinguish between seasons (ex. K-On! and K-On!!)
	
	# Characters to words
	s = s.replace("&", "and")
	# Japanese romanization differences
	s = _romanization_o.sub("o", s)
	s = s.replace("uu", "u")
	s = s.replace("wo", "o")
	
	s = _alphanum_regex.sub("", s)
	s = s.lower()
	return unidecode(s)
