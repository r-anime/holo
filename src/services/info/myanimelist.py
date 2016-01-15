from logging import debug, info, warning, error
import re

from .. import AbstractInfoHandler

class InfoHandler(AbstractInfoHandler):
	_show_link_base = "http://myanimelist.net/anime/{id}/"
	
	def __init__(self):
		super().__init__("mal", "MyAnimeList")
	
	def get_link(self, link):
		if link is None:
			return None
		return self._show_link_base.format(id=link.site_key)
	
	def find_show(self, show):
		return None
	
	def get_episode_count(self, show, link, **kwargs):
		debug("Getting episode count")
		
		# Request show page from MAL
		url = self._show_link_base.format(id=link.site_key)
		response = self._mal_request(url, **kwargs)
		if response is None:
			error("Cannot get episode count")
			return None
		
		# Parse show page (ugh)
		count_sib = response.find("span", string="Episodes:")
		if count_sib is None:
			error("Failed to find episode count sibling")
			return None
		count = count_sib.find_next_sibling(string=re.compile("\d+"))
		if count is None:
			debug("  Count not found")
			return None
		count = int(count.strip())
		
		return count
	
	# Private
	
	def _mal_request(self, url, **kwargs):
		#if "username" not in self.config or "password" not in self.config:
		#	error("Username and password required for MAL requests")
		#	return None
		
		#auth = (self.config["username"], self.config["password"])
		return self.request(url, auth=None, html=True, **kwargs)
