# API information
# 	https://wiki.anidb.net/w/HTTP_API_Definition
# Limits
# 	- 1 page every 2 seconds
#	- Avoid calling same function multiple times per day
#
# Season page
# 	https://anidb.net/perl-bin/animedb.pl?tvseries=1&show=calendar
# 	- Based on year and month, defaults to current month

from logging import debug, info, warning, error
import re

from .. import AbstractInfoHandler
from data.models import UnprocessedShow, ShowType

class InfoHandler(AbstractInfoHandler):
	_show_link_base = "https://anidb.net/perl-bin/animedb.pl?show=anime&aid={id}"
	_show_link_matcher = "https?://anidb\\.net/a([0-9]+)|https?://anidb\\.net/perl-bin/animedb\\.pl\\?(?:[^/]+&)aid=([0-9]+)|https?://anidb\\.net/anime/([0-9]+)"
	_season_url = "https://anidb.net/perl-bin/animedb.pl?show=calendar&tvseries=1&ova=1&last.anime.month=1&last.anime.year=2016"
	
	_api_base = "http://api.anidb.net:9001/httpapi?client={client}&clientver={ver}&protover=1&request={request}"
	
	def __init__(self):
		super().__init__("anidb", "AniDB")
		self.rate_limit_wait = 2
		
	def get_link(self, link):
		if link is None:
			return None
		return self._show_link_base.format(id=link.site_key)
	
	def extract_show_id(self, url):
		if url is not None:
			match = re.match(self._show_link_matcher, url, re.I)
			if match:
				return match.group(1) or match.group(2) or match.group(3)
		return None
	
	def get_episode_count(self, link, **kwargs):
		return None
	
	def get_show_score(self, show, link, **kwargs):
		return None
	
	def get_seasonal_shows(self, year=None, season=None, **kwargs):
		return []
		
		#TODO: use year and season if provided
		debug("Getting season shows: year={}, season={}".format(year, season))
		
		# Request season page from AniDB
		response = self._site_request(self._season_url, **kwargs)
		if response is None:
			error("Cannot get show list")
			return list()
		
		# Parse page
		shows_list = response.select(".calendar_all .g_section.middle .content .box")
		new_shows = list()
		for show in shows_list:
			top = show.find(class_="top")
			title_e = top.find("a")
			title = str(title_e.string)
			title = _normalize_title(title)
			show_link = title_e["href"]
			key = re.search("aid=([0-9]+)", show_link).group(1)
			
			data = show.find(class_="data")
			more_names = list()
			show_info_str = data.find(class_="series").string.strip()
			debug("Show info: {}".format(show_info_str))
			show_info = show_info_str.split(", ")
			show_type = _convert_show_type(show_info[0])
			if len(show_info) == 1:
				episode_count = 1
			else:
				ec_match = re.match("([0-9]+) eps", show_info[1])
				episode_count = int(ec_match.group(1)) if ec_match else None
			tags = data.find(class_="tags")
			has_source = tags.find("a", string=re.compile("manga|novel|visual novel")) is not None
			
			new_shows.append(UnprocessedShow(self.key, key, title, more_names, show_type, episode_count, has_source))
		
		return new_shows
	
	def find_show(self, show_name, **kwargs):
		return list()
	
	def find_show_info(self, show_id, **kwargs):
		return None
	
	def _site_request(self, url, **kwargs):
		return self.request(url, html=True, **kwargs)

def _convert_show_type(type_str):
	type_str = type_str.lower()
	if type_str == "tv series":
		return ShowType.TV
	if type_str == "movie":
		return ShowType.MOVIE
	if type_str == "ova":
		return ShowType.OVA
	return ShowType.UNKNOWN

def _normalize_title(title):
	year_match = re.match("(.*) \([0-9]+\)", title)
	if year_match:
		title = year_match.group(1)
	title = re.sub(": second season", " 2nd Season", title, flags=re.I)
	title = re.sub(": third season", " 3rd Season", title, flags=re.I)
	title = re.sub(": fourth season", " 4th Season", title, flags=re.I)
	title = re.sub(": fifth season", " 5th Season", title, flags=re.I)
	title = re.sub(": sixth season", " 6th Season", title, flags=re.I)
	return title
