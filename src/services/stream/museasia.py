from logging import debug, info, warning, error, exception
import re
from datetime import datetime, timedelta

from .. import AbstractServiceHandler
from data.models import Episode, UnprocessedStream

from services.stream import youtube

class ServiceHandler(youtube.ServiceHandler):
	def __init__(self):
		super(youtube.ServiceHandler, self).__init__("museasia", "Muse Asia", False)
