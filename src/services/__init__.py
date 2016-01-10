from logging import debug, warning, error

# Request helpers

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

# Service definition

from abc import abstractmethod
import requests

class AbstractService:
	def __init__(self, key):
		self.key = key
	
	@abstractmethod
	def get_latest_episode(self, show_id, **kwargs):
		"""
		Gets information on the latest episode for this service.
		:param show_id: The ID of the show being checked
		:param kwargs: Arguments passed to the request, such as proxy and authentication
		:return: The latest episode
		"""
		return None
	
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

# Services

_services = None

def get_services():
	global _services
	if _services is None:
		_services = dict()
		#TODO: find services in module (every file not __init__)
		from . import crunchyroll
		_services["crunchyroll"] = crunchyroll.Service()
	
	return _services

def get_service(key):
	if key in _services:
		return _services[key]
	return None
