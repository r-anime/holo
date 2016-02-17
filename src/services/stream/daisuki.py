# Shows in a region: https://motto.daisuki.net/api2/search/mode:1
# Specific show: https://motto.daisuki.net/api2/seriesdetail/SHOW_ID

from logging import debug, info, warning, error
from datetime import datetime

from .. import AbstractServiceHandler
from data.models import Episode

class ServiceHandler(AbstractServiceHandler):
	def __init__(self):
		super().__init__("daisuki", "Daisuki")
	
	def get_latest_episode(self, stream, **kwargs):
		return None
	
	def get_stream_link(self, stream):
		return None
	
	def get_seasonal_streams(self, year=None, season=None, **kwargs):
		return list()
