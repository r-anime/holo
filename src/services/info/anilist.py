# API docs: http://anilist-api.readthedocs.org/en/latest/

from logging import debug, info, warning, error
import re

from .. import AbstractInfoHandler
from data.models import UnprocessedShow, ShowType

class InfoHandler(AbstractInfoHandler):
	_show_link_base = "http://anilist.co/anime/{id}"
	_show_link_matcher = "https?://anilist\\.co/anime/([0-9]+)"
	_season_url = "http://anilist.co/api/browse/anime?year={year}&season={season}&type=Tv"
	
	def __init__(self):
		super().__init__("anilist", "AniList")
		self.rate_limit_wait = 2
		
	def get_link(self, link):
		if link is None:
			return None
		return self._show_link_base.format(id=link.site_key)
	
	def extract_show_id(self, url):
		if url is not None:
			match = re.match(self._show_link_matcher, url, re.I)
			if match:
				return match.group(1)
		return None
	
	def get_episode_count(self, show, link, **kwargs):
		return None
	
	def get_show_score(self, show, link, **kwargs):
		return None
	
	def get_seasonal_shows(self, year=None, season=None, **kwargs):
		debug("Getting season shows: year={}, season={}".format(year, season))
		
		# Request season page from AniDB
		#url = self._season_url.format(year=year, season=season)
		#response = self._site_request(url, **kwargs)
		#if response is None:
		#	error("Cannot get show list")
		#	return list()
		
		# Parse page
		#TODO
		return list()
	
	def find_show(self, show_name, **kwargs):
		return list()
	
	def _site_request(self, url, **kwargs):
		return self.request(url, html=True, **kwargs)
