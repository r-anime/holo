from logging import debug, info, warning, error
import re

from .. import AbstractInfoHandler
from data.models import UnprocessedShow, ShowType

class InfoHandler(AbstractInfoHandler):
	_show_link_base = "https://www.anime-planet.com/anime/{name}"
	_show_link_matcher = "(?:https?://)?(?:www\.)?anime-planet\.com/anime/([a-zA-Z0-9-]+)"

	def __init__(self):
		super().__init__("animeplanet", "Anime-Planet")

	def get_link(self, link):
		if link is None:
			return None
		return self._show_link_base.format(name=link.site_key)

	def extract_show_id(self, url):
		if url is not None:
			match = re.match(self._show_link_matcher, url, re.I)
			if match:
				return match.group(1)
		return None

	def get_episode_count(self, link, **kwargs):
		return None

	def get_show_score(self, show, link, **kwargs):
		return None

	def get_seasonal_shows(self, year=None, season=None, **kwargs):
		return list()

	def find_show(self, show_name, **kwargs):
		return list()

	def find_show_info(self, show_id, **kwargs):
		return None
