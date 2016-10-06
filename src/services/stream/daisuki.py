# Shows in a region: https://motto.daisuki.net/api2/search/mode:1
# Specific show: https://motto.daisuki.net/api2/seriesdetail/SHOW_ID
# Public show page: http://www.daisuki.net/us/en/anime/detail.SHOW_KEY.html

from logging import debug, info, warning, error
from datetime import datetime
import re

from .. import AbstractServiceHandler
from data.models import Episode

class ServiceHandler(AbstractServiceHandler):
	_show_url = "http://funimation.com/shows/{key}"
	
	_show_key_re = re.compile("daisuki\.net/[a-z]{2}/[a-z]{2}/anime/detail\.([^/.]+)(?:\.html)?", re.I)
	
	def __init__(self):
		super().__init__("daisuki", "Daisuki", False)
	
	# Episode finding
	
	def get_all_episodes(self, stream, **kwargs):
		return []
	
	# Remote info getting
	
	def get_stream_info(self, stream, **kwargs):
		return None
	
	def get_seasonal_streams(self, year=None, season=None, **kwargs):
		return list()
	
	# Local info formatting
	
	def get_stream_link(self, stream):
		return self._show_url.format(key=stream.show_key)
	
	def extract_show_key(self, url):
		match = self._show_key_re.search(url)
		if match:
			return match.group(1)
		return None
