from logging import debug, info, warning
from datetime import datetime

from .. import AbstractPollHandler
from data.models import Poll

class PollHandler(AbstractPollHandler):
	def __init__(self):
		super().__init__("youpoll")

	def create_poll(self, show, episode, **kwargs):
		return None

	def get_link(self, poll):
		return None

	def get_poll_score(self, poll):
		return None
