# Show search: https://www.nyaa.eu/?page=search&cats=1_37&filter=2&term=
# Show search (RSS): https://www.nyaa.eu/?page=rss&cats=1_37&filter=2&term=

from logging import debug, info, warning, error
from datetime import datetime, timedelta
import re
from urllib.parse import quote_plus as url_quote

from .. import AbstractServiceHandler
from data.models import Episode

class ServiceHandler(AbstractServiceHandler):
	_search_base = "https://{domain}/?page=rss&cats=1_37&filter=2&term={q}"
	
	def __init__(self):
		super().__init__("nyaa", "Nyaa", True)
	
	# Episode finding
	
	def get_latest_episode(self, stream, **kwargs):
		episodes = self._get_feed_episodes(stream.show_key, **kwargs)
		max_episode = None
		for episode in episodes:
			debug("Checking episode")
			if _is_valid_episode(episode):
				episode = _digest_episode(episode)
				if episode:
					if max_episode is None:
						max_episode = episode
					else:
						max_episode = max(max_episode, episode, key=lambda x: x.number)
		return max_episode
	
	def _get_feed_episodes(self, show_key, **kwargs):
		"""
		Always returns a list.
		"""
		info("Getting episodes for Nyaa/{}".format(show_key))
		if "domain" not in self.config or not self.config["domain"]:
			error("  Domain not specified in config")
			return list()
		
		# Send request
		query = url_quote(show_key, safe="", errors="ignore")
		url = self._search_base.format(domain=self.config["domain"], q=query)
		response = self.request(url, rss=True, **kwargs)
		if response is None:
			error("Cannot get latest show for Nyaa/{}".format(show_key))
			return list()
		
		# Parse RSS feed
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		return response.get("entries", list())
	
	# Don't need these!
	
	def get_stream_link(self, stream):
		return None
	
	def get_stream_info(self, stream, **kwargs):
		return None
	
	def extract_show_key(self, url):
		return None
	
	def get_seasonal_streams(self, year=None, season=None, **kwargs):
		return list()

# Feed parsing

def _verify_feed(feed):
	debug("Verifying feed")
	if feed.bozo:
		debug("  Feed was malformed")
		return False
	debug("  Feed verified")
	return True

def _is_valid_episode(feed_episode):
	episode_date = datetime(*feed_episode.published_parsed[:6])
	date_diff = datetime.utcnow() - episode_date
	if date_diff >= timedelta(days=3):
		debug("  Episode too old")
		return False
	return True

def _digest_episode(feed_episode):
	title = feed_episode["title"]
	episode_num = _extract_episode_num(title)
	if episode_num:								# Intended, checks if not None and > 0
		date = feed_episode["published_parsed"]
		link = feed_episode["id"]
		return Episode(episode_num, None, link, date)
	return None

_num_extractors = [re.compile(x, re.I) for x in [
	"\[(?:horriblesubs|commie|hiryuu|kuusou|fff)\] .+ - (\d+)",	# " - " separator between show and episode
	"\[orz\] .* (\d+)",											# No separator
	"\[kaitou\]_.*_-_(\d+)",									# "_-_" separator
	"\[doremi\]\..*\.(\d+)",									# "." separator
	"\[.*?\][ _].*[ _](?:-[ _])?(\d+)"							# Generic to make a best guess. Does not include . separation due to the common "XXX vol.01" format
]]

def _extract_episode_num(name):
	debug("Extracting episode number from \"{}\"".format(name))
	for regex in _num_extractors:
		match = regex.match(name)
		if match:
			num = int(match.group(1))
			debug("  Match found, num={}".format(num))
			return num
	debug("  No match found")
	return None
