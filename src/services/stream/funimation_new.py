# All shows: http://www.funimation.com/feeds/ps/shows?limit=100000
# 			 http://www.funimation.com/feeds/ps/shows?sort=SortOptionLatestSubscription (limit no workie)
# Single show: http://www.funimation.com/feeds/ps/videos?ut=FunimationSubscriptionUser&show_id=7556914&limit=100000

from logging import debug, info, warning, error, exception
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
	
	def get_all_episodes(self, stream, **kwargs):
		info("Getting live episodes for Funimation_new/{} ({})".format(stream.show_key, stream.show_id))
		if not stream.show_id:
			debug("  ID required and not given")
			return []
		
		episode_datas = self._get_feed_shows(stream.show_id, **kwargs)
		
		episodes = []
		for episode_data in episode_datas:
			if _is_valid_episode(episode_data, stream.show_id):
				try:
					episodes.append(self._digest_episode(episode_data, stream))
				except:
					exception("Problem digesting episode for Funimation_new/{} ({})".format(stream.show_key, stream.show_id))
		
		if len(episode_datas) > 0:
			debug("  {} episodes found, {} valid".format(len(episode_datas), len(episodes)))
			if len(episode_datas) != len(episodes):
				warning("  Not all episodes processed")
		else:
			debug("  No episodes found")
		return episodes
	
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
	
	def get_stream_info(self, stream, **kwargs):
		# TODO important
		return None
	
	def get_seasonal_streams(self, **kwargs):
		return list()
	
	def extract_show_key(self, url):
		return None

# Helpers

def _verify_feed(feed):
	return True

def _is_valid_episode(feed_episode, show_id):
	block = feed_episode.find("id")
	if block is None or block.text != show_id:
		return False
	block = feed_episode.find("content")
	if not block or not block.find("metadata"):
		print("Content block not found")
		return False
	return True
