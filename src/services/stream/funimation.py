# All shows: http://www.funimation.com/feeds/ps/shows?limit=100000
# 			 http://www.funimation.com/feeds/ps/shows?sort=SortOptionLatestSubscription (limit no workie)
# Single show: http://www.funimation.com/feeds/ps/videos?ut=FunimationSubscriptionUser&show_id=7556914&limit=100000

from logging import debug, info, warning, error
from datetime import datetime, date, timedelta
import re

from .. import AbstractServiceHandler
from data.models import Episode

class ServiceHandler(AbstractServiceHandler):
	_show_url = "http://funimation.com/shows/{id}"
	_show_list = "http://www.funimation.com/feeds/ps/shows?limit=100000"
	_episode_feed = "http://funimation.com/feeds/ps/videos?ut=FunimationSubscriptionUser&show_id={id}&limit=100000"
	_episode_url = "http://www.funimation.com/shows/{show_slug}/videos/official/{ep_slug}?watch=sub"
	
	_show_key_re = re.compile("funimation\.com/(?:shows/)?([^/]+)", re.I)
	
	def __init__(self):
		super().__init__("funimation", "FUNimation", False)
	
	# Episode finding
	
	def get_latest_episode(self, stream, **kwargs):
		if not stream.show_id:
			debug("ID required and not given")
			return None
		
		episodes = self._get_feed_episodes(stream.show_id, **kwargs)
		if not episodes or len(episodes) == 0:
			debug("No episodes found")
			return None
		
		# Find all valid episodes
		valid_episodes = list()
		for episode in episodes:
			if _is_valid_episode(episode, stream.show_id):
				valid_episodes.append(self._digest_episode(episode, stream))
		if len(valid_episodes) == 0:
			debug("No episodes found")
			return None
		
		valid_episodes = sorted(valid_episodes, key=lambda e: e.date, reverse=True)
		today = date.today()			# Uses local time instead of UTC, but probably doesn't matter too much on a day scale
		for episode in valid_episodes:
			if today <= episode.date.date():
				debug("{}: {}".format(episode.number, episode.date))
				return episode
		
		debug("Episode not found")
		return None
	
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
	
	# Remote info getting
	
	def get_stream_info(self, stream, **kwargs):
		info("Getting stream info for Funimation/{}".format(stream.show_key))
		
		response = self.request(self._show_list, json=True, **kwargs)
		if response is None:
			error("Cannot get stream info")
			return None
		
		for show_data in response:
			show_key = self.extract_show_key(show_data["link"])
			if show_key and show_key == stream.show_key:
				name = show_data["series_name"]
				id = show_data["asset_id"]
				stream.name = name
				stream.show_id = id
				return stream
		
		return None
	
	def get_seasonal_streams(self, year=None, season=None, **kwargs):
		#TODO
		return list()
	
	# Local info formatting
	
	def get_stream_link(self, stream):
		# Just going to assume it's the correct service
		return self._show_url.format(id=stream.show_key)
	
	def extract_show_key(self, url):
		match = self._show_key_re.search(url)
		if match:
			return match.group(1)
		return None

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
