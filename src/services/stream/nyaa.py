# Show search: https://www.nyaa.eu/?page=search&cats=1_37&filter=2&term=

from logging import debug, info, warning, error
from datetime import datetime

from .. import AbstractServiceHandler
from data.models import Episode

class ServiceHandler(AbstractServiceHandler):
	def __init__(self):
		super().__init__("nyaa", "Nyaa")
	
	def get_latest_episode(self, stream, **kwargs):
		return None
	
	def get_stream_link(self, stream):
		return None
	
	def get_seasonal_streams(self, year=None, season=None, **kwargs):
		return list()
