# https://www.youtube.com/playlist?list=PLJV1h9xQ7Hx-zsp8lYI4dubgEeNia46mr

from logging import debug, info, warning, error
import re

from .. import AbstractServiceHandler

class ServiceHandler(AbstractServiceHandler):
	_show_url = "https://www.youtube.com/playlist?list={key}"
	
	_show_key_re = re.compile("youtube.com/playlist\?list=([\w-]+)", re.I)
	
	def __init__(self):
		super().__init__("youtube", "YouTube", False)
	
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
