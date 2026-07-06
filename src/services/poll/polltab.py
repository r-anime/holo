import re
from logging import debug, warning, error
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from data.models import Poll
from .. import AbstractPollHandler


class PollHandler(AbstractPollHandler):
	OPTIONS = ["Excellent", "Great", "Good", "Mediocre", "Bad"]

	_poll_post_url = "https://www.polltab.com/api/poll/create"
	_poll_post_headers = {"Content-Type": "application/json"}
	_poll_post_data = '{{"question":"{}","questionMedia":"","choices":[{{"text":"{}"}},{{"text":"{}"}},{{"text":"{}"}},{{"text":"{}"}},{{"text":"{}"}}],"allowMultiChoice":false,"startDate":null,"endDate":null,"enableCaptcha":false,"enableComments":false,"hideResults":false,"restriction":"re"}}'

	_poll_id_re = re.compile(r"polltab.com/(\d+)", re.I)
	_poll_link = "https://polltab.com/{id}/"
	_poll_results_link = "https://polltab.com/{id}/results/"

	def __init__(self) -> None:
		super().__init__("polltab")

	def create_poll(self, title: str, submit: bool, **kwargs: Any) -> Optional[str]:
		if not submit:
			return None
		headers = self._poll_post_headers
		data = self._poll_post_data.format(title, *self.OPTIONS)
		try:
			resp = requests.post(self._poll_post_url, data=data, headers=headers)
		except Exception as e:
			error("Could not create poll (exception in POST): %s", e)
			return None

		if not resp.ok:
			error("Could not create poll (resp !OK)")
			return None

		try:
			poll_id = resp.json()["data"]["pollId"]
		except (KeyError, AttributeError):
			error("Could not retrieve poll (malformed response)")
			return None
		return poll_id

	def get_link(self, poll: Poll) -> str:
		return self._poll_link.format(id=poll.id)

	def get_results_link(self, poll: Poll) -> str:
		return self._poll_results_link.format(id=poll.id)

	def get_score(self, poll: Poll) -> Optional[float]:
		debug(f"Getting score for show {poll.show_id} / episode {poll.episode}")
		try:
			response = self.request(self.get_results_link(poll), html=True)
			assert isinstance(response, BeautifulSoup)
		except Exception as e:
			error(
				"Couldn't get scores for poll %s (query error: %s)",
				self.get_results_link(poll),
				e,
			)
			return None

		try:
			answers = [
				a.text for a in response.find_all("div", "pollresult-chart-item-result")
			]
			# vote% is not returned with the request, probably calculated on the fly with a script
			# pre-remove potential separators (,.) just in case
			if diff := (set(answers) - set(self.OPTIONS)):
				error("Aborted - found unexpected labels: %s", ",".join(diff))
				return None
			votes = [
				int(v.text.split()[0].replace(",", "").replace(".", ""))
				for v in response.find_all("span", "pollresult-chart-item-result-vote")
			]
			num_votes = sum(votes)
			if num_votes == 0:
				warning("No vote recorded, no score returned")
				return None
			votes_dict = dict(zip(answers, votes))
			score = round(
				sum(votes_dict[a] * i for i, a in enumerate(self.OPTIONS[::-1], 1))
				/ num_votes,
				2,
			)
			return score
		except Exception as e:
			error(
				"Couldn't get scores for poll %s (parsing error: %s)",
				self.get_results_link(poll),
				e,
			)
			return None
