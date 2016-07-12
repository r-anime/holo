# API information
# 	http://myanimelist.net/modules.php?go=api

from logging import debug, info, warning, error
import re

from .. import AbstractInfoHandler
from data.models import UnprocessedShow, ShowType

class InfoHandler(AbstractInfoHandler):
	_show_link_base = "http://myanimelist.net/anime/{id}/"
	_show_link_matcher = "https?://(?:.+?\.)?myanimelist\.net/anime/([0-9]{5,})/"
	_season_show_url = "http://myanimelist.net/anime/season"
	
	_api_search_base = "http://myanimelist.net/api/anime/search.xml?q={q}"
	
	def __init__(self):
		super().__init__("mal", "MyAnimeList")
	
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
	
	def find_show(self, show_name, **kwargs):
		url = self._api_search_base.format(q=show_name)
		result = self._mal_api_request(url, **kwargs)
		if result is None:
			error("Failed to find show")
			return list()
		
		assert result.tag == "anime"
		shows = list()
		for child in result:
			print(child)
			assert child.tag == "entry"
			
			id = child.find("id").text
			name = child.find("title").text
			more_names = [child.find("english").text]
			show = UnprocessedShow(self.key, id, name, more_names, ShowType.UNKNOWN, 0, False)
			shows.append(show)
		
		return shows
	
	def get_episode_count(self, show, link, **kwargs):
		debug("Getting episode count")
		
		# Request show page from MAL
		url = self._show_link_base.format(id=link.site_key)
		response = self._mal_request(url, **kwargs)
		if response is None:
			error("Cannot get show page")
			return None
		
		# Parse show page (ugh, HTML parsing)
		count_sib = response.find("span", string="Episodes:")
		if count_sib is None:
			error("Failed to find episode count sibling")
			return None
		count_elem = count_sib.find_next_sibling(string=re.compile("\d+"))
		if count_elem is None:
			warning("  Count not found")
			return None
		count = int(count_elem.strip())
		debug("  Count: {}".format(count))
		
		return count
	
	def get_show_score(self, show, link, **kwargs):
		debug("Getting show score")
		
		# Request show page
		url = self._show_link_base.format(id=link.site_key)
		response = self._mal_request(url, **kwargs)
		if response is None:
			error("Cannot get show page")
			return None
		
		# Find score
		score_elem = response.find("span", attrs={"itemprop": "ratingValue"})
		if score_elem is None:
			warning("  Count not found")
			return None
		score = float(score_elem.string)
		debug("  Score: {}".format(score))
		
		return score
	
	def get_seasonal_shows(self, year=None, season=None, **kwargs):
		#TODO: use year and season if provided
		debug("Getting season shows: year={}, season={}".format(year, season))
		
		# Request season page from MAL
		response = self._mal_request(self._season_show_url, **kwargs)
		if response is None:
			error("Cannot get show list")
			return list()
		
		# Parse page (ugh, HTML parsing. Where's the useful API, MAL?)
		lists = response.find_all(class_="seasonal-anime-list")
		if len(lists) == 0:
			error("Invalid page? Lists not found")
			return list()
		new_list = lists[0].find_all(class_="seasonal-anime")
		if len(new_list) == 0:
			error("Invalid page? Shows not found in list")
			return list()
		
		new_shows = list()
		episode_count_regex = re.compile("(\d+|\?) eps?")
		for show in new_list:
			show_key = show.find(class_="genres")["id"]
			title = str(show.find("a", class_="link-title").string)
			title = _normalize_title(title)
			more_names = [title[:-11]] if title.lower().endswith("2nd season") else list()
			show_type = ShowType.TV #TODO, changes based on section/list
			episode_count = episode_count_regex.search(show.find(class_="eps").find(string=episode_count_regex)).group(1)
			episode_count = None if episode_count == "?" else int(episode_count)
			has_source = show.find(class_="source").string != "Original"
			
			new_shows.append(UnprocessedShow(self.key, show_key, title, more_names, show_type, episode_count, has_source))
		
		return new_shows
	
	# Private
	
	def _mal_request(self, url, **kwargs):
		return self.request(url, html=True, **kwargs)
	
	def _mal_api_request(self, url, **kwargs):
		if "username" not in self.config or "password" not in self.config:
			error("Username and password required for MAL requests")
			return None
		
		auth = (self.config["username"], self.config["password"])
		return self.request(url, auth=auth, xml=True, **kwargs)
	
def _convert_type(mal_type):
	return None
	
def _normalize_title(title):
	title = re.sub(" \(TV\)", "", title)
	return title
