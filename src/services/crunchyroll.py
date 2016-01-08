from logging import debug, info, warning, error
import feedparser, re
from . import AbstractService, Episode

class Service(AbstractService):
	_episode_rss = "http://crunchyroll.com/{id}.rss"
	_backup_rss = "http://crunchyroll.com/rss/anime"
	
	def __init__(self):
		super().__init__("crunchyroll")
	
	def get_latest_episode(self, show_id, **kwargs):
		episodes = self._get_feed_episodes(show_id, **kwargs)
		if not episodes or len(episodes) == 0:
			debug("No episodes found")
			return None
		
		# Hope the episodes were parsed in order and iterate down looking for the latest episode
		# The show-specific feed was likely used, but not guaranteed
		for episode in episodes:
			if _is_valid_episode(episode, show_id):
				return _digest_episode(episode)
		
		debug("Episode not found")
		return None
	
	def _get_feed_episodes(self, show_id, **kwargs):
		"""
		Always returns a list.
		"""
		info("Getting episodes for Crunchyroll/{}".format(show_id))
		
		# Sometimes shows don't have an RSS feed
		# Use the backup global feed when it doesn't
		if show_id is not None:
			url = self._episode_rss.format(id=show_id)
		else:
			debug("  Using backup feed")
			url = self._backup_rss
		
		# Send request
		response = self.request(url, **kwargs)
		if response is None:
			error("Cannot get latest show for Crunchyroll/{}".format(show_id))
			return list()
		
		# Parse RSS feed
		rss = feedparser.parse(response)
		if not _verify_feed(rss):
			warning("Parsed feed could not be verified, may have unexpected results")
		print(rss)
		
		return rss.get("entries", list())

# Helpers

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
	debug("  Feed verified \U0001F44D")
	return True

def _is_valid_episode(feed_episode, show_id):
	# We don't want non-episodes (PVs, VA interviews, etc.)
	if feed_episode.get("crunchyroll_isclip", False):
		debug("Is PV, ignoring")
		return False
	if _get_slug(feed_episode.link) != show_id:
		debug("Wrong ID")
		return False
	return True

def _digest_episode(feed_episode):
	debug("Digesting episode")
	
	# Get data
	num = feed_episode.crunchyroll_episodenumber
	debug("  num={}".format(num))
	name = feed_episode.title
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
