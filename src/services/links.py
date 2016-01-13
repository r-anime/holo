from logging import debug, info, warning, error

from . import AbstractLinkHandler

class MyAnimeList(AbstractLinkHandler):
	_link_base = "http://myanimelist.net/anime/{id}/"
	
	def __init__(self):
		super().__init__("mal", "MyAnimeList")
	
	def get_link(self, link):
		if link is None:
			return None
		return self._link_base.format(id=link.site_key)
