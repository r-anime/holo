# All shows: http://www.funimation.com/feeds/ps/shows?limit=100000
# 			 http://www.funimation.com/feeds/ps/shows?sort=SortOptionLatestSubscription (limit no workie)
# Single show: http://www.funimation.com/feeds/ps/videos?ut=FunimationSubscriptionUser&show_id=7556914&limit=100000

from logging import debug, info, warning, error
from datetime import datetime
import re

from .. import AbstractServiceHandler
from data.models import Episode

class ServiceHandler(AbstractServiceHandler):
	_show_url = "http://funimation.com/shows/{id}"
	_episode_feed = "https://api-funimation.dadcdigital.com/xml/longlist/content/page/?id=shows&sort=&sort_direction=DESC&itemThemes=dateAddedShow&territory=US&offset=0&limit=30"
	_episode_url = "http://www.funimation.com/shows/{show_slug}/videos/official/{ep_slug}?watch=sub"
	
	_re_episode_num = re.compile("Episode ([0-9]+)", re.I)
	
	def __init__(self):
		super().__init__("funimation_new", "FUNimation", False)
	
	def get_latest_episode(self, stream, **kwargs):
		shows = self._get_feed_shows(stream.show_id, **kwargs)
		if not shows or len(shows) == 0:
			debug("No shows found")
			return None
		
		# Hope the episodes were parsed in order and iterate down looking for the latest episode
		# The show-specific feed was likely used, but not guaranteed
		for episode in shows:
			if _is_valid_show(episode, stream.show_id):
				return self._digest_episode(episode, stream)
		
		debug("Show not found")
		return None
	
	def get_stream_link(self, stream):
		# Just going to assume it's the correct service
		return self._show_url.format(id=stream.show_key)
	
	def _get_feed_shows(self, show_id, **kwargs):
		"""
		Always returns a list.
		"""
		info("Getting episodes for Funimation/{}".format(show_id))
		
		# Send request
		response = self.request(self._episode_feed, xml=True, **kwargs)
		if response is None:
			error("Cannot get latest shows feed".format(show_id))
			return list()
		
		# Parse response
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		#print(rss)
		
		return response
	
	def _digest_episode(self, feed_episode, stream):
		debug("Digesting episode")
		
		# Get data
		content = feed_episode.find("content").find("metadata")
		num_text = content.find("recentContentItem").text
		num_match = self._re_episode_num.match(num_text)
		if not num_match:
			error("recentContentItem episode has unknown format: \"{}\"".format(num_text))
		num = int(num_match.group(1))
		debug("  num={}".format(num))
		name = None #feed_episode["show_name"]		#FIXME
		debug("  name={}".format(name))
		link = None #self._episode_url.format(show_slug=stream.show_key, ep_slug=feed_episode["url"])		#FIXME
		debug("  link={}".format(link))
		#FIXME: content-metadata contains "<recentlyAdded>added {1458071999} ago"; could use timestamp
		date = datetime.now() #datetime.strptime(feed_episode["releaseDate"], "%Y/%m/%d")
		debug("  date={}".format(date))
		
		return Episode(num, name, link, date)
	
	def get_seasonal_streams(self, year=None, season=None, **kwargs):
		return list()

# Helpers

def _verify_feed(feed):
	return True

def _is_valid_show(feed_episode, show_id):
	block = feed_episode.find("id")
	if block is None or block.text != show_id:
		return False
	block = feed_episode.find("content")
	if not block or not block.find("metadata"):
		print("Content block not found")
		return False
	return True
