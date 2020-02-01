from logging import debug, info, warning, error
from datetime import datetime, timezone
import requests
import re

from .. import AbstractPollHandler
from data.models import Poll

class PollHandler(AbstractPollHandler):
	OPTION_V2_PLUS = 'Like'
	OPTION_V2_MINUS = 'Dislike'
	OPTIONS_V3 = ['Excellent', 'Great', 'Good', 'Mediocre', 'Bad']

	_poll_post_url = 'https://youpoll.me'
	_poll_post_headers = {'User-Agent': None}
	_poll_post_data = {'address': '',
	                   'poll-1[question]': None,
	                   'poll-1[option1]': OPTIONS_V3[0],
	                   'poll-1[option2]': OPTIONS_V3[1],
	                   'poll-1[option3]': OPTIONS_V3[2],
	                   'poll-1[option4]': OPTIONS_V3[3],
	                   'poll-1[option5]': OPTIONS_V3[4],
	                   'poll-1[min]': '1',
	                   'poll-1[max]': 10,
	                   'poll-1[voting-system]': '0',
	                   'poll-1[approval-validation-type]': '0',
	                   'poll-1[approval-validation-value]': '1',
	                   'poll-1[basic]': '',
	                   'voting-limits-dropdown': '3',
			   'captcha-test-checkbox': 'on',
	                   'reddit-link-karma': '0',
	                   'reddit-comment-karma': '0',
	                   'reddit-days-old': '8',
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
		resp = requests.post(self._poll_post_url, data = data, **kwargs)

		if resp.ok:
			match = self._poll_id_re.search(resp.url)
			return match.group(1)
		else:
			return None

	def get_link(self, poll):
		return self._poll_link.format(id = poll.id)

	def get_results_link(self, poll):
		return self._poll_results_link.format(id = poll.id)

	def get_score(self, poll):
		debug(f"Getting score for show {poll.show_id} / episode {poll.episode}")
		response = self.request(self.get_results_link(poll), html = True)
		if response.find('div', class_='basic-type-results') is None: # numeric score
			# v1 votes, 1-10 range
			value_text = response.find("span", class_="rating-mean-value").text
			num_votes = response.find("span", class_="admin-total-votes").text
			try:
				return float(value_text)
			except ValueError:
				warning(f"Invalid value '{value_text}' (v1), no score returned")
				return None
		else: # options-based score
			divs = response.find_all('div', class_='basic-option-wrapper')
			if len(divs) == 2:
				# v2 votes, like dislike
				# returned as fraction of likes
				divs = response.find_all('div', class_='basic-option-wrapper')
				num_votes = int(response.find("span", class_="admin-total-votes").text)
				if num_votes == 0:
					warning('No vote recorded, no score returned')
					return None
				for div in divs:
					if div.find('span', class_='basic-option-title').text == self.OPTION_V2_PLUS:
						value_text = div.find('span', class_='basic-option-percent').text
						score = float(value_text.strip('%')) / 100
						print(f'Score: {score}')
						return score
				error(f'Could not find the score (v2), no score returned')
				return None
			elif len(divs) == 5:
				# v3 votes, 5 points scale
				divs = response.find_all('div', class_='basic-option-wrapper')
				num_votes = int(response.find("span", class_="admin-total-votes").text)
				if num_votes == 0:
					warning('No vote recorded, no score returned')
					return None
				values = dict()
				for div in divs:
					label = div.find('span', class_='basic-option-title').text
					if label not in self.OPTIONS_V3:
						error(f'Found unexpected label {label}, aborted')
						return None
					value_text = div.find('span', class_='basic-option-percent').text
					score = float(value_text.strip('%')) / 100
					values[label] = score
				results = [values[k] for k in self.OPTIONS_V3]
				info(f'Results: {str(results)}')
				total = sum([r * s for r, s in zip(results, range(5, 0, -1))])
				total = round(total, 2)
				return total


	@staticmethod
	def convert_score_str(score):
		if score is None:
			return ''
		elif score <= 1.0: # New style votes
			return f'{round(100 * score)}%'
		else:
			return str(score)
