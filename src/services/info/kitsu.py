# API docs: https://kitsu.docs.apiary.io

from logging import debug, info, warning, error
import re

from .. import AbstractInfoHandler
from data.models import UnprocessedShow, ShowType

class InfoHandler(AbstractInfoHandler):
	_show_link_base = "https://kitsu.io/anime/{slug}"
	_show_link_matcher = "https?://kitsu\.io/anime/([a-zA-Z0-9-]+)"
	_season_url = "https://kitsu.io/api/edge/anime?filter[year]={year}&filter[season]={season}&filter[subtype]=tv&page[limit]=20"

	_api_base = "https:///kitsu.io/api/edge/anime"
	
	def __init__(self):
		super().__init__("kitsu", "Kitsu")
		
	def get_link(self, link):
		if link is None:
			return None
		return self._show_link_base.format(slug=link.site_key)
	
	def extract_show_id(self, url):
		if url is not None:
			match = re.match(self._show_link_matcher, url, re.I)
			if match:
				return match.group(1)
		return None
	
	def get_episode_count(self, link, **kwargs):
		#debug("Getting episode count")
		
		# Request show data from Kitsu
		#url = self._api_base + "?filter[slug]=" + link.site_key + "&fields[anime]=episodeCount"
		#response = self._site_request(url, **kwargs)
		#if response is None:
		#	error("Cannot get show data")
		#	return None
		
		# Parse show data
		#count = response["data"][0]["attributes"]["episodeCount"]
		#if count is None:
		#	warning("  Count not found")
		#	return None

		#return count
		return None
	
	def get_show_score(self, show, link, **kwargs):
		#debug("Getting show score")
		
		# Request show data
		#url = self._api_base + "?filter[slug]=" + link.site_key + "&fields[anime]=averageRating"
		#response = self._site_request(url, **kwargs)
		#if response is None:
		#	error("Cannot get show data")
		#	return None
		
		# Find score
		#score = response["data"][0]["attributes"]["averageRating"]
		#if score is None:
		#	warning("  Score not found")
		#	return None

		#return score
		return None
	
	def get_seasonal_shows(self, year=None, season=None, **kwargs):
		#debug("Getting season shows: year={}, season={}".format(year, season))
		
		# Request season data from Kitsu
		#url = self._season_url.format(year=year, season=season)
		#response = self._site_request(url, **kwargs)
		#if response is None:
		#	error("Cannot get show list")
		#	return list()
		
		# Parse data
		#TODO
		return list()
	
	def find_show(self, show_name, **kwargs):
		#url = self._api_base + "?filter[text]=" + show_name
		#result = self._site_request(url, **kwargs)
		#if result is None:
		#	error("Failed to find show")
		#	return list()
		
		#shows = list()
		#TODO
		
		#return shows
		return list()
	
	def find_show_info(self, show_id, **kwargs):
		#debug("Getting show info for {}".format(show_id))
		
		# Request show data from Kitsu
		#url = self._api_base + "?filter[slug]=" + show_id + "&fields[anime]=titles,abbreviatedTitles"
		#response = self._site_request(url, **kwargs)
		#if response is None:
		#	error("Cannot get show data")
		#	return None
			
		# Parse show data
		#name_english = response["data"][0]["attributes"]["titles"]["en"]
		#if name_english is None:
		#	warning("  English name was not found")
		#	return None

		#names = [name_english]
		#return UnprocessedShow(self.key, id, None, names, ShowType.UNKNOWN, 0, False)
		return None
	
	def _site_request(self, url, **kwargs):
		return self.request(url, json=True, **kwargs)
