# Dummy info handler, used for official website of shows

from logging import debug, info, warning, error
import re

from .. import AbstractInfoHandler

class InfoHandler(AbstractInfoHandler):

	def __init__(self):
		super().__init__("official", "Official Website")

	def get_link(self, link):
		if link is None:
			return None
		return link.site_key

	def extract_show_id(self, url):
		return url

	def find_show(self, show_name, **kwargs):
		return list()

	def find_show_info(self, show_id, **kwargs):
		return None

	def get_episode_count(self, link, **kwargs):
		return None

	def get_show_score(self, show, link, **kwargs):
		return None

	def get_seasonal_shows(self, year=None, season=None, **kwargs):
		return list()
