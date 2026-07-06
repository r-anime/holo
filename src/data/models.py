from datetime import datetime
import enum
import copy

class ShowType(enum.Enum):
	UNKNOWN = 0
	TV = 1
	MOVIE = 2
	OVA = 3

def str_to_showtype(string):
	if string is not None:
		string = string.lower()
		if string == "tv":
			return ShowType.TV
		if string == "movie":
			return ShowType.MOVIE
		if string == "ova":
			return ShowType.OVA
	return ShowType.UNKNOWN

class DbEqMixin:
	def __eq__(self, other):
		return self.id == other.id
	
	def __ne__(self, other):
		return self.id != other.id
	
	def __hash__(self):
		return hash(self.id)

class Show(DbEqMixin):
	def __init__(self, id, name, name_en, length, show_type, has_source, is_nsfw, enabled, delayed):
		self.id = id
		self.name = name
		self.name_en = name_en
		self.length = length
		self.type = show_type
		self.has_source = has_source == 1
		self.is_nsfw = is_nsfw == 1
		self.enabled = enabled
		self.delayed = delayed

	@property
	def aliases(self):
		return self._aliases if hasattr(self, '_aliases') else []

	@aliases.setter
	def aliases(self, names):
		self._aliases = names
	
	def __str__(self):
		return "Show: {} (id={}, type={}, len={})".format(self.name, self.id, self.type, self.length)

class Episode:
	def __init__(self, number, name=None, link=None, date=None):
		self.number = number
		self.name = name		# Not stored in database
		self.link = link
		if isinstance(date, datetime):
			self.date = date
		elif date:
			self.date = datetime(*date[:6])
	
	def __str__(self):
		return "Episode: {} | Episode {}, {} ({})".format(self.date, self.number, self.name, self.link)
	
	@property
	def is_live(self, local=False):
		now = datetime.now() if local else datetime.utcnow()
		return now >= self.date

class EpisodeScore:
	def __init__(self, show_id, episode, score, site_id=None):
		self.show_id = show_id
		self.episode = episode
		self.site_id = site_id
		self.score = score

class Service(DbEqMixin):
	def __init__(self, id, key, name, enabled, use_in_post):
		self.id = id
		self.key = key
		self.name = name
		self.enabled = enabled == 1
		self.use_in_post = use_in_post == 1
		
	def __str__(self):
		return "Service: {} ({})".format(self.key, self.id)

class Stream(DbEqMixin):
	"""
		remote_offset: relative to a start episode of 1
			If a stream numbers new seasons after ones before, remote_offset should be positive.
			If a stream numbers starting before 1 (ex. 0), remote_offset should be negative.
		display_offset: relative to the internal numbering starting at 1
			If a show should be displayed with higher numbering (ex. continuing after a split cour), display_offset should be positive.
			If a show should be numbered lower than 1 (ex. 0), display_offset should be negative.
	"""
	def __init__(self, id, service, show, show_id, show_key, name, remote_offset, display_offset, active):
		self.id = id
		self.service = service
		self.show = show
		self.show_id = show_id
		self.show_key = show_key
		self.name = name
		self.remote_offset = remote_offset
		self.display_offset = display_offset
		self.active = active
	
	def __str__(self):
		return "Stream: {} ({}@{}), {} {}".format(self.show, self.show_key, self.service, self.remote_offset, self.display_offset)
	
	@classmethod
	def from_show(cls, show):
		return Stream(id=-show.id, service=-1, show=show, show_id=show.id, show_key=show.name, name=show.name, remote_offset=0, display_offset=0, active=1)
	
	def to_internal_episode(self, episode):
		e = copy.copy(episode)
		e.number -= self.remote_offset
		return e
	
	def to_display_episode(self, episode):
		e = copy.copy(episode)
		e.number += self.display_offset
		return e

class LinkSite(DbEqMixin):
	def __init__(self, id, key, name, enabled):
		self.id = id
		self.key = key
		self.name = name
		self.enabled = enabled == 1
	
	def __str__(self):
		return "Link site: {} {} ({})".format(self.key, self.id, self.enabled)

class Link:
	def __init__(self, site, show, site_key):
		self.site = site
		self.show = show
		self.site_key = site_key
	
	def __str__(self):
		return "Link: {}@{}, show={}".format(self.site_key, self.site, self.show)

class PollSite(DbEqMixin):
	def __init__(self, id, key):
		self.id = id
		self.key = key

	def __str__(self):
		return f"Poll site: {self.key}"

class Poll:
	def __init__(self, show_id, episode, service, id, date, score):
		self.show_id = show_id
		self.episode = episode
		self.service_id = service
		self.id = id
		if isinstance(date, datetime):
			self.date = date
		else:
			self.date = datetime.fromtimestamp(int(date))
		self.score = score

	@property
	def has_score(self):
		return self.score is not None

	def __str__(self):
		return f"Poll {self.show_id}/{self.episode} (Score {self.score})"

class LiteStream:
	def __init__(self, show, service, service_name, url):
		self.show = show
		self.service = service
		self.service_name = service_name
		self.url = url

	def __str__(self):
		return f"LiteStream: {self.service}|{self.service_name}, show={self.show}, url={self.url}"

class UnprocessedShow:
	def __init__(self, name, show_type, episode_count, has_source, is_nsfw=False, site_key=None, show_key=None, name_en=None, more_names=None):
		self.site_key = site_key
		self.show_key = show_key
		self.name = name
		self.name_en = name_en
		self.more_names = more_names or []
		self.show_type = show_type
		self.episode_count = episode_count
		self.has_source = has_source
		self.is_nsfw = is_nsfw

class UnprocessedStream:
	def __init__(self, service_key, show_key, remote_offset, display_offset, show_id=None, name=""):
		self.service_key = service_key
		self.show_key = show_key
		self.show_id = show_id
		self.name = name
		self.remote_offset = remote_offset
		self.display_offset = display_offset
