from logging import debug, warning, error
from abc import abstractmethod, ABC
from types import ModuleType
from typing import List, Dict, Optional, Iterable

# Common

_service_configs = None

def setup_services(config):
	global _service_configs
	_service_configs = config.services

def _get_service_config(key):
	if key in _service_configs:
		return _service_configs[key]
	return dict()

def _make_service(service):
	service.set_config(_get_service_config(service.key))
	return service

# Utilities

def import_all_services(pkg: ModuleType, class_name: str):
	import importlib
	services = dict()
	for name in pkg.__all__:
		module = importlib.import_module("."+name, package=pkg.__name__)
		if hasattr(module, class_name):
			handler = getattr(module, class_name)()
			services[handler.key] = _make_service(handler)
		else:
			warning("Service module {}.{} has no handler {}".format(pkg.__name__, name, class_name))
		del module
	del importlib
	return services

##############
# Requesting #
##############

from functools import wraps, lru_cache
from time import perf_counter, sleep
import requests
from json import JSONDecodeError
from xml.etree import ElementTree as xml_parser
from bs4 import BeautifulSoup
import feedparser

def rate_limit(wait_length):
	last_time = 0
	
	def decorate(f):
		@wraps(f)
		def rate_limited(*args, **kwargs):
			nonlocal last_time
			diff = perf_counter() - last_time
			if diff < wait_length:
				sleep(wait_length - diff)
			
			r = f(*args, **kwargs)
			last_time = perf_counter()
			return r
		return rate_limited
	return decorate

class Requestable:
	rate_limit_wait = 1
	
	@lru_cache(maxsize=100)
	@rate_limit(rate_limit_wait)
	def request(self, url, json=False, xml=False, html=False, rss=False, proxy=None, useragent=None, auth=None, timeout=10):
		"""
		Sends a request to the service.
		:param url: The request URL
		:param json: If True, return the response as parsed JSON
		:param xml: If True, return the response as parsed XML
		:param html: If True, return the response as parsed HTML
		:param proxy: Optional proxy, a tuple of address and port
		:param useragent: Ideally should always be set
		:param auth: Tuple of username and password to use for HTTP basic auth
		:param timeout: Amount of time to wait for a response in seconds
		:return: The response if successful, otherwise None
		"""
		if proxy is not None:
			if len(proxy) != 2:
				warning("Invalid number of proxy values, need address and port")
				proxy = None
			else:
				proxy = {"http": "http://{}:{}".format(*proxy)}
				debug("Using proxy: {}", proxy)
		
		headers = {"User-Agent": useragent}
		debug("Sending request")
		debug("  URL={}".format(url))
		debug("  Headers={}".format(headers))
		try:
			response = requests.get(url, headers=headers, proxies=proxy, auth=auth, timeout=timeout)
		except requests.exceptions.Timeout:
			error("  Response timed out")
			return None
		debug("  Status code: {}".format(response.status_code))
		if not response.ok or response.status_code == 204:		# 204 is a special case for MAL errors
			error("Response {}: {}".format(response.status_code, response.reason))
			return None
		if len(response.text) == 0:		# Some sites *coughfunimationcough* may return successful empty responses for new shows
			error("Empty response (probably funimation)")
			return None
		
		if json:
			debug("Response returning as JSON")
			try:
				return response.json()
			except JSONDecodeError as e:
				error("Response is not JSON", exc_info=e)
				return None
		if xml:
			debug("Response returning as XML")
			#TODO: error checking
			raw_entry = xml_parser.fromstring(response.text)
			#entry = dict((attr.tag, attr.text) for attr in raw_entry)
			return raw_entry
		if html:
			debug("Returning response as HTML")
			soup = BeautifulSoup(response.text, 'html.parser')
			return soup
		if rss:
			debug("Returning response as RSS feed")
			rss = feedparser.parse(response.text)
			return rss
		debug("Response returning as text")
		return response.text

###################
# Service handler #
###################

from datetime import datetime
from data.models import Episode, PollSite, Stream, UnprocessedStream

class AbstractServiceHandler(ABC, Requestable):
	def __init__(self, key, name, is_generic):
		self.key = key
		self.name = name
		self.config = None
		self.is_generic = is_generic
	
	def set_config(self, config):
		self.config = config
	
	def get_latest_episode(self, stream: Stream, **kwargs) -> Optional[Episode]:
		"""
		Gets information on the latest episode for this service.
		:param stream: The stream being checked
		:param kwargs: Arguments passed to the request, such as proxy and authentication
		:return: The latest episode, or None if no episodes are found and valid
		"""
		episodes = self.get_published_episodes(stream, **kwargs)
		return max(episodes, key=lambda e: e.number, default=None)
	
	def get_published_episodes(self, stream: Stream, **kwargs) -> Iterable[Episode]:
		"""
		Gets all possible live episodes for a given stream. Not all older episodes are
		guaranteed to be returned due to potential API limitations.
		:param stream: The stream being checked
		:param kwargs: Arguments passed to the request, such as proxy and authentication
		:return: An iterable of live episodes
		"""
		episodes = self.get_all_episodes(stream, **kwargs)
		today = datetime.utcnow().date()							#NOTE: Uses local time instead of UTC, but probably doesn't matter too much on a day scale
		return filter(lambda e: e.date.date() <= today, episodes)	# Update 9/14/16: It actually matters.
	
	@abstractmethod
	def get_all_episodes(self, stream: Stream, **kwargs) -> Iterable[Episode]:
		"""
		Gets all possible episodes for a given stream. Not all older episodes are
		guaranteed to be returned due to potential API limitations.
		:param stream: The stream being checked
		:param kwargs: Arguments passed to the request, such as proxy and authentication
		:return: A list of live episodes
		"""
		return list()

	def get_recent_episodes(self, streams: Iterable[Stream], **kwargs) -> Dict[Stream, Iterable[Episode]]:
		"""
		Gets all recently released episode on the service, for the given streams.
		What counts as recent is decided by the service handler, but all newly released episodes
		should be returned by this function.
		By default, calls get_all_episodes for each stream.
		:param streams: The streams for which new episodes must be returned.
		:param kwargs: Arguments passed to the request, such as proxy and authentication
		:return: A dict in which each key is one of the requested streams
			 and the value is a list of newly released episodes for the stream
		"""
		return {stream: self.get_all_episodes(stream, **kwargs) for stream in streams}
	
	@abstractmethod
	def get_stream_link(self, stream: Stream) -> Optional[str]:
		"""
		Creates a URL to a show's main stream page hosted by this service.
		:param stream: The show's stream
		:return: A URL to the stream's page
		"""
		return None
	
	@abstractmethod
	def extract_show_key(self, url: str) -> Optional[str]:
		"""
		Extracts a show's key from its URL.
		For example, "myriad-colors-phantom-world" is extracted from the Crunchyroll URL
			http://www.crunchyroll.com/myriad-colors-phantom-world.rss
		:param url: 
		:return: The show's service key
		"""
		return None
	
	@abstractmethod
	def get_stream_info(self, stream: Stream, **kwargs) -> Optional[Stream]:
		"""
		Get information about the stream, including name and ID.
		:param stream: The stream being checked
		:return: An updated stream object if successful, otherwise None"""
		return None
	
	@abstractmethod
	def get_seasonal_streams(self, **kwargs) -> List[UnprocessedStream]:
		"""
		Gets a list of streams for the current or nearly upcoming season.
		:param kwargs: Extra arguments, particularly useragent
		:return: A list of UnprocessedStreams (empty list if no shows or error)
		"""
		return list()

# Services

_services = dict()

def _ensure_service_handlers():
	global _services
	if _services is None or len(_services) == 0:
		from . import stream
		_services = import_all_services(stream, "ServiceHandler")

def get_service_handlers() -> Dict[str, AbstractServiceHandler]:
	"""
	Creates an instance of every service in the services module and returns a mapping to their keys.
	:return: A dict of service keys to an instance of the service
	"""
	_ensure_service_handlers()
	return _services

def get_service_handler(service=None, key:str=None) -> Optional[AbstractServiceHandler]:
	"""
	Returns an instance of a service handler representing the given service or service key.
	:param service: A service
	:param key: A service key
	:return: A service handler instance
	"""
	_ensure_service_handlers()
	if service is not None and service.key in _services:
		return _services[service.key]
	if key is not None and key in _services:
		return _services[key]
	return None

@lru_cache(maxsize=1)
def get_genereic_service_handlers(services=None, keys=None) -> List[AbstractServiceHandler]:
	_ensure_service_handlers()
	if keys is None:
		if services is not None:
			keys = {s.key for s in services}
	return [_services[key] for key in _services if (len(keys) == 0 or key in keys) and _services[key].is_generic]

################
# Link handler #
################

from data.models import Show, EpisodeScore, UnprocessedShow, Link

class AbstractInfoHandler(ABC, Requestable):
	def __init__(self, key, name):
		self.key = key
		self.name = name
		self.config = None
	
	def set_config(self, config):
		#debug("Setting config of {} to {}".format(self.key, config))
		self.config = config
	
	@abstractmethod
	def get_link(self, link: Link) -> Optional[str]:
		"""
		Creates a URL using the information provided by a link object.
		:param link: The link object
		:return: A URL
		"""
		return None
	
	@abstractmethod
	def extract_show_id(self, url: str) -> Optional[str]:
		"""
		Extracts a show's ID from its URL.
		For example, 31737 is extracted from the MAL URL
			http://myanimelist.net/anime/31737/Gakusen_Toshi_Asterisk_2nd_Season
		:param url: 
		:return: The show's service ID
		"""
		return None
	
	@abstractmethod
	def find_show(self, show_name: str, **kwargs) -> List[Show]:
		"""
		Searches the link site for a show with the specified name.
		:param show_name: The desired show's name
		:param kwargs: Extra arguments, particularly useragent
		:return: A list of shows (empty list if no shows or error)
		"""
		return list()
	
	@abstractmethod
	def find_show_info(self, show_id: str, **kwargs) -> Optional[UnprocessedShow]:
		return None
	
	@abstractmethod
	def get_episode_count(self, link: Link, **kwargs) -> Optional[int]:
		"""
		Gets the episode count of the specified show on the site given by the link.
		:param link: The link pointing to the site being checked
		:param kwargs: Extra arguments, particularly useragent
		:return: The episode count, otherwise None
		"""
		return None
	
	@abstractmethod
	def get_show_score(self, show, link, **kwargs) -> Optional[EpisodeScore]:
		"""
		Gets the score of the specified show on the site given by the link.
		:param show: The show being checked
		:param link: The link pointing to the site being checked
		:param kwargs: Extra arguments, particularly useragent
		:return: The show's score, otherwise None
		"""
		return None
	
	@abstractmethod
	def get_seasonal_shows(self, year=None, season=None, **kwargs) -> List[UnprocessedShow]:
		"""
		Gets a list of shows airing in a particular season.
		If year and season are None, uses the current season.
		Note: Not all sites may allow specific years and seasons.
		:param year: 
		:param season: 
		:param kwargs: Extra arguments, particularly useragent
		:return: A list of UnprocessedShows (empty list if no shows or error)
		"""
		return list()
	
# Link sites

_link_sites = dict()

def _ensure_link_handlers():
	global _link_sites
	if _link_sites is None or len(_link_sites) == 0:
		from . import info
		_link_sites = import_all_services(info, "InfoHandler")

def get_link_handlers() -> Dict[str, AbstractInfoHandler]:
	"""
	Creates an instance of every link handler in the links module and returns a mapping to their keys.
	:return: A dict of link handler keys to an instance of the link handler
	"""
	_ensure_link_handlers()
	return _link_sites

def get_link_handler(link_site=None, key:str=None) -> Optional[AbstractInfoHandler]:
	"""
	Returns an instance of a link handler representing the given link site.
	:param link_site: A link site
	:param key: A link site key
	:return: A link handler instance
	"""
	_ensure_link_handlers()
	if link_site is not None and link_site.key in _link_sites:
		return _link_sites[link_site.key]
	if key is not None and key in _link_sites:
		return _link_sites[key]
	return None

################
# Poll handler #
################

from data.models import Poll

class AbstractPollHandler(ABC, Requestable):
	def __init__(self, key):
		self.key = key
		self.config = None

	def set_config(self, config):
		self.config = config

	@abstractmethod
	def create_poll(self, title, submit: bool) -> Optional[str]:
		"""
		Create a new Poll.
		:param title: title of this poll
		:return: the id of the poll
		"""
		return None

	@abstractmethod
	def get_link(self, poll: Poll) -> Optional[str]:
		"""
		Creates a URL using the information provided by the poll object.
		:param poll: the Poll object
		:return: a URL
		"""
		return None

	@abstractmethod
	def get_results_link(self, poll: Poll) -> Optional[str]:
		"""
		Creates a URL for the poll results using the information provided by the poll object.
		:param poll: the Poll object
		:return: a URL
		"""
		return None

	@abstractmethod
	def get_score(self, poll: Poll) -> Optional[float]:
		"""
		Return the score of this poll.
		:param poll: the Poll object
		:return: the score on a 1-10 scale
		"""
		return None

	@staticmethod
	def convert_score_str(score: Optional[float]) -> str:
		if score is None:
			return '----'
		return str(score)


_poll_sites = dict()

def _ensure_poll_handlers():
	global _poll_sites
	if _poll_sites is None or len(_poll_sites) == 0:
		from . import poll
		_poll_sites = import_all_services(poll, "PollHandler")

def get_poll_handlers() -> Dict[str, AbstractPollHandler]:
	"""
	Creates an instance of every poll handler in the polls module and returns a mapping to their keys.
	:return: a dict of poll handler keys to the instance of th poll handler
	"""
	_ensure_poll_handlers()
	return _poll_sites

def get_default_poll_handler() -> AbstractPollHandler:
	"""
	Returns an instance of the default poll handler.
	:return: the handler
	"""
	_ensure_poll_handlers()
	return _poll_sites["polltab"]


def get_poll_handler(
		poll_site: Optional[PollSite] = None,
		key: Optional[str] = None,
	) -> Optional[AbstractPollHandler]:
	"""
	Returns an instance of a poll handler representing the given poll site.
	:param poll_site: A poll site
	:param key: A poll site key
	:return: A poll handler instance
	"""
	_ensure_poll_handlers()
	if poll_site is not None and poll_site.key in _poll_sites:
		return _poll_sites[poll_site.key]
	if key is not None and key in _poll_sites:
		return _poll_sites[key]
	return None
