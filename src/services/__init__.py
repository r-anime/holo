from logging import debug, warning, error

##############
# Requesting #
##############

from functools import wraps, lru_cache
from time import perf_counter, sleep

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
	@lru_cache(maxsize=20)
	@rate_limit(1)
	def request(self, url, json=False, proxy=None, useragent=None):
		"""
		Sends a request to the service.
		:param url: The request URL
		:param json: If True, return the response as JSON
		:param proxy: Optional proxy, a tuple of address and port
		:param useragent: Ideally should always be set
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
		response = requests.get(url, headers=headers, proxies=proxy)
		debug("  Status code: {}".format(response.status_code))
		if not response.ok:
			error("Response {}: {}".format(response.status_code, response.reason))
			return None
		
		if json:
			debug("Response returning as JSON")
			return response.json()
		debug("Response returning as text")
		return response.text

###################
# Service handler #
###################

from abc import abstractmethod, ABC
import requests

class AbstractServiceHandler(ABC, Requestable):
	def __init__(self, key, name):
		self.key = key
		self.name = name
	
	@abstractmethod
	def get_latest_episode(self, show_id, **kwargs):
		"""
		Gets information on the latest episode for this service.
		:param show_id: The ID of the show being checked
		:param kwargs: Arguments passed to the request, such as proxy and authentication
		:return: The latest episode
		"""
		return None
	
	@abstractmethod
	def get_stream_link(self, stream):
		"""
		Creates a URL to a show's main stream page hosted by this service.
		:param stream: The show's stream
		:return: A URL to the stream's page
		"""
		return None

# Services

_services = None

def _ensure_service_handlers():
	global _services
	if _services is None:
		_services = dict()
		#TODO: find services in module (every file not __init__)
		from . import crunchyroll
		_services["crunchyroll"] = crunchyroll.ServiceHandler()

def get_service_handlers():
	"""
	Creates an instance of every service in the services module and returns a mapping to their keys.
	:return: A dict of service keys to an instance of the service
	"""
	_ensure_service_handlers()
	return _services

def get_service_handler(service):
	"""
	Returns an instance of a service handler representing the given service.
	:param service: A service
	:return: A service handler instance
	"""
	_ensure_service_handlers()
	if service is not None and service.key in _services:
		return _services[service.key]
	return None

################
# Link handler #
################

class AbstractLinkHandler(ABC, Requestable):
	def __init__(self, key, name):
		self.key = key
		self.name = name
	
	@abstractmethod
	def get_link(self, link):
		"""
		Creates a URL using the information provided by a link object.
		:param link: The link object
		:return: A URL
		"""
		return None

# Link sites

_link_sites = None

def _ensure_link_handlers():
	global _link_sites
	if _link_sites is None:
		_link_sites = dict()
		#TODO: find services in module (every file not __init__)
		from . import links
		_link_sites["mal"] = links.MyAnimeList()

def get_link_handlers():
	"""
	Creates an instance of every link handler in the links module and returns a mapping to their keys.
	:return: A dict of link handler keys to an instance of the link handler
	"""
	_ensure_link_handlers()
	return _link_sites

def get_link_handler(link_site):
	"""
	Returns an instance of a link handler representing the given link site.
	:param link_site: A link site
	:return: A link handler instance
	"""
	_ensure_link_handlers()
	if link_site is not None and link_site.key in _link_sites:
		return _link_sites[link_site.key]
	return None
