from logging import debug, info, warning, error, exception
import re

from .. import AbstractServiceHandler
from data.models import Episode, UnprocessedStream

class ServiceHandler(AbstractServiceHandler):
	_show_url = "http://crunchyroll.com/{id}"
	_show_re = re.compile("crunchyroll.com/([\w-]+)", re.I)
	_episode_rss = "http://crunchyroll.com/{id}.rss"
	_backup_rss = "http://crunchyroll.com/rss/anime"
	_season_url = "http://crunchyroll.com/lineup"
	
	def __init__(self):
		super().__init__("crunchyroll", "Crunchyroll", False)
	
	# Episode finding
	
	def get_all_episodes(self, stream, **kwargs):
		info("Getting live episodes for Crunchyroll/{}".format(stream.show_key))
		episode_datas = self._get_feed_episodes(stream.show_key, **kwargs)
		
		# Check data validity and digest
		episodes = []
		for episode_data in episode_datas:
			if _is_valid_episode(episode_data, stream.show_key):
				try:
					episodes.append(_digest_episode(episode_data))
				except:
					exception("Problem digesting episode for Crunchyroll/{}".format(stream.show_key))
		
		if len(episode_datas) > 0:
			debug("  {} episodes found, {} valid", len(episode_datas), len(episodes))
		else:
			debug("  No episodes found")
		return episodes
	
	def _get_feed_episodes(self, show_key, **kwargs):
		"""
		Always returns a list.
		"""
		info("Getting episodes for Crunchyroll/{}".format(show_key))
		
		url = self._get_feed_url(show_key)
		
		# Send request
		response = self.request(url, rss=True, **kwargs)
		if response is None:
			error("Cannot get latest show for Crunchyroll/{}".format(show_key))
			return list()
		
		# Parse RSS feed
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		return response.get("entries", list())
	
	@classmethod
	def _get_feed_url(cls, show_key):
		# Sometimes shows don't have an RSS feed
		# Use the backup global feed when it doesn't
		if show_key is not None:
			return cls._episode_rss.format(id=show_key)
		else:
			debug("  Using backup feed")
			return cls._backup_rss
	
	# Remote info getting
	
	_title_fix = re.compile("(.*) Episodes", re.I)
	
	def get_stream_info(self, stream, **kwargs):
		info("Getting stream info for Crunchyroll/{}".format(stream.show_key))
		
		url = self._get_feed_url(stream.show_key)
		response = self.request(url, rss=True, **kwargs)
		if response is None:
			error("Cannot get feed")
			return None
		
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		
		stream.name = response.feed.title
		match = self._title_fix.match(stream.name)
		if match:
			stream.name = match.group(1)
		return stream
	
	def get_seasonal_streams(self, year=None, season=None, **kwargs):
		#TODO finish
		debug("Getting season shows: year={}, season={}".format(year, season))
		if year or season:
			error("Year and season are not supported by {}".format(self.name))
			return list()
		
		# Request page
		response = self.request(self._season_url, html=True, **kwargs)
		if response is None:
			error("Failed to get seasonal streams page")
			return list()
		
		# Find sections (continuing simulcast, new simulcast, new catalog)
		lists = response.find_all(class_="lineup-grid")
		if len(lists) < 2:
			error("Unsupported structure of lineup page")
			return list()
		elif len(lists) < 2 or len(lists) > 3:
			warning("Unexpected number of lineup grids")
		
		# Parse individual shows
		# WARNING: Some may be dramas and there's nothing distinguishing them from anime
		show_elements = lists[1].find_all(class_="element-lineup-anime")
		raw_streams = list()
		for show in show_elements:
			title = show["title"]
			if "to be announced" not in title.lower():
				debug("  Show: {}".format(title))
				url = show["href"]
				debug("  URL: {}".format(url))
				url_match = self._show_re.search(url)
				if not url_match:
					error("Failed to parse show URL: {}".format(url))
					continue
				key = url_match.group(1)
				debug("  Key: {}".format(key))
				remote_offset, display_offset = self._get_stream_info(key)
				
				raw_stream = UnprocessedStream(self.key, key, None, title, remote_offset, display_offset)
				raw_streams.append(raw_stream)
		
		return raw_streams
	
	def _get_stream_info(self, show_key):
		#TODO: load show page and figure out offsets based on contents
		return 0, 0
	
	# Local info formatting
	
	def get_stream_link(self, stream):
		# Just going to assume it's the correct service
		return self._show_url.format(id=stream.show_key)
	
	def extract_show_key(self, url):
		match = self._show_re.search(url)
		if match:
			return match.group(1)
		return None
	
# Episode feeds

def _verify_feed(feed):
	debug("Verifying feed")
	if feed.bozo:
		debug("  Feed was malformed")
		return False
	if "crunchyroll" not in feed.namespaces or feed.namespaces["crunchyroll"] != "http://www.crunchyroll.com/rss":
		debug("  Crunchyroll namespace not found or invalid")
		return False
	if feed.feed.language != "en-us":
		debug("  Language not en-us")
		return False
	debug("  Feed verified")
	return True


def _is_valid_episode(feed_episode, show_id):
	# We don't want non-episodes (PVs, VA interviews, etc.)
	if feed_episode.get("crunchyroll_isclip", False) or not hasattr(feed_episode, "crunchyroll_episodenumber"):
		debug("Is PV, ignoring")
		return False
	# Sanity check
	if _get_slug(feed_episode.link) != show_id:
		debug("Wrong ID")
		return False
	return True

_episode_name_correct = re.compile("Episode \d+ - (.*)")
_episode_count_fix = re.compile("([0-9]+)[abc]?", re.I)

def _digest_episode(feed_episode):
	debug("Digesting episode")
	
	# Get data
	num_match = _episode_count_fix.match(feed_episode.crunchyroll_episodenumber)
	if num_match:
		num = int(num_match.group(1))
	else:
		warning("Unknown episode number format \"{}\"".format(feed_episode.crunchyroll_episodenumber))
		num = 0
	debug("  num={}".format(num))
	name = feed_episode.title
	match = _episode_name_correct.match(name)
	if match:
		info("  Corrected title from \"{}\"".format(name))
		name = match.group(1)
	debug("  name={}".format(name))
	link = feed_episode.link
	debug("  link={}".format(link))
	date = feed_episode.published_parsed
	debug("  date={}".format(date))
	
	return Episode(num, name, link, date)

_slug_regex = re.compile("crunchyroll.com/([a-z0-9-]+)/", re.I)

def _get_slug(episode_link):
	match = _slug_regex.search(episode_link)
	if match:
		return match.group(1)
	return None

# Season page
