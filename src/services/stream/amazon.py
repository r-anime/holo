# https://www.amazon.com/dp/B01NCUV2FV
# https://www.amazon.com/-/dp/B01NCUV2FV
# https://www.amazon.com/Scums-Wish/dp/B01NCUV2FV
# https://www.amazon.com/gp/product/B01NCUV2FV

from logging import debug, info, warning, error
import re

from .. import AbstractServiceHandler

class ServiceHandler(AbstractServiceHandler):
	_show_url = "https://www.amazon.com/dp/{key}"
	
	_show_key_re = re.compile(r"amazon\.com/(?:(?:[\w-]+/)?dp|gp/product)/([a-z0-9]+)/?", re.I)
	
	def __init__(self):
		super().__init__("amazon", "Amazon", False)
	
	# Episode finding
	
	def get_all_episodes(self, stream, **kwargs):
		return []
	
	# Remote info getting
	
	def get_stream_info(self, stream, **kwargs):
		return None
	
	def get_seasonal_streams(self, **kwargs):
		return list()
	
	# Local info formatting
	
	def get_stream_link(self, stream):
		return self._show_url.format(key=stream.show_key)
	
	def extract_show_key(self, url):
		match = self._show_key_re.search(url)
		if match:
			return match.group(1)
		return None
