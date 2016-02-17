# All shows: http://www.funimation.com/feeds/ps/shows?limit=100000
# Single show: http://www.funimation.com/feeds/ps/videos?ut=FunimationSubscriptionUser&show_id=7556914

from logging import debug, info, warning, error
from datetime import datetime

from .. import AbstractServiceHandler
from data.models import Episode

class ServiceHandler(AbstractServiceHandler):
	_show_url = "http://funimation.com/shows/{id}"
	_episode_feed = "http://funimation.com/feeds/ps/videos?ut=FunimationSubscriptionUser&show_id={id}"
	_episode_url = "http://www.funimation.com/shows/{show_slug}/videos/official/{ep_slug}?watch=sub"
	
	def __init__(self):
		super().__init__("funimation", "FUNimation")
	
	def get_latest_episode(self, stream, **kwargs):
		episodes = self._get_feed_episodes(stream.show_id, **kwargs)
		if not episodes or len(episodes) == 0:
			debug("No episodes found")
			return None
		
		# Hope the episodes were parsed in order and iterate down looking for the latest episode
		# The show-specific feed was likely used, but not guaranteed
		for episode in episodes:
			if _is_valid_episode(episode, stream.show_id):
				return self._digest_episode(episode, stream)
		
		debug("Episode not found")
		return None
	
	def get_stream_link(self, stream):
		# Just going to assume it's the correct service
		return self._show_url.format(id=stream.show_key)
	
	def _get_feed_episodes(self, show_id, **kwargs):
		"""
		Always returns a list.
		"""
		info("Getting episodes for Funimation/{}".format(show_id))
		
		# Send request
		url = self._episode_feed.format(id=show_id)
		response = self.request(url, json=True, **kwargs)
		if response is None:
			error("Cannot get latest show for Funimation/{}".format(show_id))
			return list()
		
		# Parse RSS feed
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		#print(rss)
		
		return response["videos"]
	
	def _digest_episode(self, feed_episode, stream):
		debug("Digesting episode")
		
		# Get data
		num = feed_episode["number"]
		debug("  num={}".format(num))
		name = feed_episode["show_name"]
		debug("  name={}".format(name))
		link = self._episode_url.format(show_slug=stream.show_key, ep_slug=feed_episode["url"])
		debug("  link={}".format(link))
		date = datetime.strptime(feed_episode["releaseDate"], "%Y/%m/%d")
		debug("  date={}".format(date))
		
		return Episode(num, name, link, date)
	
	def get_seasonal_streams(self, year=None, season=None, **kwargs):
		return list()

# Helpers

def _verify_feed(feed):
	debug("Verifying feed")
	if "videos" not in feed:
		debug("  Feed doesn't contain videos")
		return False
	return True

def _is_valid_episode(feed_episode, show_id):
	def get(key, default):
		if key in feed_episode:
			return feed_episode[key]
		return default
	
	# Ignore dubs (HA!)
	if get("has_subtitles", "false") != "true" or get("dub_sub", "dub") != "sub":
		debug("Is dub, ignoring")
		return False
	# Sanity check
	if get("show_id", "-1") != show_id:
		debug("Wrong ID")
		return False
	return True
