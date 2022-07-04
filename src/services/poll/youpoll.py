from logging import debug, info, warning, error
from datetime import datetime, timezone
import requests
import re

from .. import AbstractPollHandler
from data.models import Poll

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

	_poll_id_re = re.compile('youpoll.me/(\d+)', re.I)
	_poll_link = 'https://youpoll.me/{id}/'
	_poll_results_link = 'https://youpoll.me/{id}/r'

	def __init__(self):
		super().__init__("youpoll")

	def create_poll(self, title, submit, **kwargs):
		if not submit:
			return None
		#headers = _poll_post_headers
		#headers['User-Agent'] = config.useragent
		data = self._poll_post_data
		data['poll-1[question]'] = title
		#resp = requests.post(_poll_post_url, data = data, headers = headers, **kwargs)
		try:
			resp = requests.post(self._poll_post_url, data = data, **kwargs)
		except:
			error("Could not create poll (exception in POST)")
			return None

		if resp.ok:
			match = self._poll_id_re.search(resp.url)
			return match.group(1)
		else:
			error("Could not create poll (resp !OK)")
			return None

	def get_link(self, poll):
		return self._poll_link.format(id = poll.id)

	def get_results_link(self, poll):
		return self._poll_results_link.format(id = poll.id)

	def get_score(self, poll):
		debug(f"Getting score for show {poll.show_id} / episode {poll.episode}")
		try:
			response = self.request(self.get_results_link(poll), html = True)
		except:
			error(f"Couldn't get scores for poll {self.get_results_link(poll)} (query error)")
			return None

		try:
			# 5 points scale
			divs = response.find_all('div', class_='basic-option-wrapper')
			num_votes_str = response.find("span", class_="admin-total-votes").text
			num_votes = int(num_votes_str.replace(',', ''))
			if num_votes == 0:
				warning('No vote recorded, no score returned')
				return None
			values = dict()
			for div in divs:
				label = div.find('span', class_='basic-option-title').text
				if label not in self.OPTIONS:
					error(f'Found unexpected label {label}, aborted')
					return None
				value_text = div.find('span', class_='basic-option-percent').text
				score = float(value_text.strip('%')) / 100
				values[label] = score
			results = [values[k] for k in self.OPTIONS]
			info(f'Results: {str(results)}')
			total = sum([r * s for r, s in zip(results, range(5, 0, -1))])
			total = round(total, 2)
			return total
		except:
			error(f"Couldn't get scores for poll {self.get_results_link(poll)} (parsing error)")
			return None


	@staticmethod
	def convert_score_str(score):
		if score is None:
			return '----'
		else:
			return str(score)
