import re
from logging import debug, warning, error
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from data.models import Poll
from .. import AbstractPollHandler

class PollHandler(AbstractPollHandler):
	OPTIONS = ['Excellent', 'Great', 'Good', 'Mediocre', 'Bad']

	_poll_post_url = 'https://youpoll.me'
	_poll_post_headers = {'User-Agent': None}
	_poll_post_data = {'address': '',
	                   'poll-1[question]': None,
	                   'poll-1[option1]': OPTIONS[0],
	                   'poll-1[option2]': OPTIONS[1],
	                   'poll-1[option3]': OPTIONS[2],
	                   'poll-1[option4]': OPTIONS[3],
	                   'poll-1[option5]': OPTIONS[4],
	                   'poll-1[min]': '1',
	                   'poll-1[max]': 10,
	                   'poll-1[voting-system]': '0',
	                   'poll-1[approval-validation-type]': '0',
	                   'poll-1[approval-validation-value]': '1',
	                   'poll-1[basic]': '',
	                   'voting-limits-dropdown': '3',
	                   'captcha-test-checkbox': 'on',
	                   'reddit-link-karma': '0',
	                   'reddit-comment-karma': '200',
	                   'reddit-days-old': '0',
	                   'responses-input': '',
	                   }

	_poll_id_re = re.compile(r'youpoll.me/(\d+)', re.I)
	_poll_link = 'https://youpoll.me/{id}/'
	_poll_results_link = 'https://youpoll.me/{id}/r'

	def __init__(self) -> None:
		super().__init__("youpoll")

	def create_poll(self, title: str, submit: bool, **kwargs: Any)-> Optional[str]:
		if not submit:
			return None
		#headers = _poll_post_headers
		#headers['User-Agent'] = config.useragent
		data = self._poll_post_data
		data['poll-1[question]'] = title
		#resp = requests.post(_poll_post_url, data = data, headers = headers, **kwargs)
		try:
			resp = requests.post(self._poll_post_url, data = data, **kwargs)
		except Exception as e:
			error("Could not create poll (exception in POST): %s", e)
			return None

		if not resp.ok:
			error("Could not create poll (resp !OK)")
			return None

		match = self._poll_id_re.search(resp.url)
		if not match:
			error("Could not create poll (URL not found)")
			return None
		return match.group(1)

	def get_link(self, poll: Poll) -> str:
		return self._poll_link.format(id = poll.id)

	def get_results_link(self, poll: Poll) -> str:
		return self._poll_results_link.format(id = poll.id)

	def get_score(self, poll: Poll) -> Optional[float]:
		debug(f"Getting score for show {poll.show_id} / episode {poll.episode}")
		try:
			response = self.request(self.get_results_link(poll), html = True)
			assert isinstance(response, BeautifulSoup)
		except Exception as e:
			error("Couldn't get scores for poll %s - query error: %s", self.get_results_link(poll), e)
			return None

		try:
			labels = [x.text.strip() for x in response.find_all('div', 'rslt-plurality-txt')]
			if diff := (set(labels) - set(self.OPTIONS)):
				error("Aborted - found unexpected labels: %s", ",".join(diff))
				return None
			votes = [
				int(x.text.strip().replace(',','').replace('.',''))
				for x in response.find_all('div', 'rslt-plurality-votes')
			]
			num_votes = int(response.find('span', 'rslt-total-votes').text.strip())
			if num_votes == 0:
				warning('No vote recorded, no score returned')
				return None
			votes_dict = dict(zip(labels, votes))
			score = round(
				sum(votes_dict[a] * i for i, a in enumerate(self.OPTIONS[::-1], 1))
				/ num_votes,
				2,
			)
			return score
		except Exception as e:
			error("Couldn't get scores for poll %s - parsing error: %s", self.get_results_link(poll), e)
			return None


	@staticmethod
	def convert_score_str(score: Optional[float]) -> str:
		if score is None:
			return '----'
		return str(score)
