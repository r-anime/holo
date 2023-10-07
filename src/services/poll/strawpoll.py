import logging
import re
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from data.models import Poll

from .. import AbstractPollHandler


class PollHandler(AbstractPollHandler):
	OPTIONS = ["Excellent", "Great", "Good", "Mediocre", "Bad"]

	_poll_post_url = "https://strawpoll.ai/poll-maker/"
	_poll_post_data = (
		'{{"address":"","token":"{token}","type":"0",'
		'"questions":[{{"plurality":{{"isVoterOpts":false,"maxOpts":"10"}},'
		'"approval":{{"type":"0","value":"1","lower":"1","upper":"1"}},'
		'"range":{{"min":"1","max":"10"}},"integer":{{"min":"1","max":"10"}},'
		'"rational":{{"min":"1.0","max":"10.0"}},"type":"0",'
		'"title":"{question}","opts":['
		+ ",".join(f'"{option}"' for option in OPTIONS)
		+ "]}}],"
		'"settings":{{"reddit":{{"link":"0","comment":"200","days":"0"}},'
		'"limits":"3","isCaptcha":false,"isDeadline":false,'
		'"isHideResults":false,"deadline":null}}}}'
	)

	_form_token_re = re.compile(
		r"<input type=\"hidden\" id=\"pm-token\" value=\"(\w+)\">"
	)

	_poll_id_re = re.compile(r"strawpoll.ai/poll/vote/(\w+)", re.I)
	_poll_link = "https://strawpoll.ai/poll/vote/{id}"
	_poll_results_link = "https://strawpoll.ai/poll/results/{id}"

	def __init__(self) -> None:
		super().__init__(key="strawpoll")

	def create_poll(self, title: str, submit: bool, **kwargs: Any) -> Optional[str]:
		if not submit:
			return None

		# Obtain a poll creation form to fill
		try:
			form = requests.get(self._poll_post_url, timeout=10)
		except Exception as e:
			logging.error("Could not obtain a form to fill: %s", e)
			return None

		# Get the token associated to the form
		try:
			match = self._form_token_re.search(form.text)
			assert match
			token: str = match.group(1)
		except Exception as e:
			logging.error("Could not retrieve the form token: %s", e)
			return None

		# Get the session cookie associated to the form
		try:
			cookies = {
				"PHPSESSID": form.headers["set-cookie"].split(";")[0].split("=")[1]
			}
		except Exception as e:
			logging.error("Could not retrieve the session cookie: %s", e)
			return None

		# Submit poll creation form
		data = self._poll_post_data.format(token=token, question=title)
		try:
			resp = requests.post(
				self._poll_post_url,
				data={"data": data},
				cookies=cookies,
				timeout=10,
			)
		except Exception as e:
			logging.error("Could not create poll (exception in POST): %s", e)
			return None

		if not resp.ok:
			logging.error("Could not create poll (resp !OK)")
			return None

		if match := self._poll_id_re.search(resp.url):
			return match.group(1)

		logging.error("Could not create poll (ID not found)")
		# A failed submission normally returns the poll creation page
		# This happens for example when the payload doesn't have a specific format
		return None

	def get_link(self, poll: Poll) -> str:
		return self._poll_link.format(id=poll.id)

	def get_results_link(self, poll: Poll) -> str:
		return self._poll_results_link.format(id=poll.id)

	def get_score(self, poll: Poll) -> Optional[float]:
		logging.debug(
			"Getting score for show %s / episode %d", poll.show_id, poll.episode
		)
		try:
			response = self.request(url=self.get_results_link(poll), html=True)
			assert isinstance(response, BeautifulSoup)
		except Exception:
			logging.error(
				"Couldn't get scores for poll %s (GET request failed)",
				self.get_results_link(poll),
			)
			return None

		try:
			labels: list[str] = [
				x.text.strip() for x in response.find_all("div", "rslt-plurality-txt")
			]
			if diff := (set(labels) - set(self.OPTIONS)):
				logging.error("Aborted - found unexpected labels: %s", ",".join(diff))
				return None
			votes = [
				int(x.text.strip().replace(",", "").replace(".", ""))
				for x in response.find_all("div", "rslt-plurality-votes")
			]
			num_votes = int(response.find("span", "rslt-total-votes").text.strip())
			if num_votes == 0:
				logging.warning("No vote recorded, no score returned")
				return None
			votes_dict = dict(zip(labels, votes))
			score = round(
				sum(votes_dict[a] * i for i, a in enumerate(self.OPTIONS[::-1], 1))
				/ num_votes,
				2,
			)
			return score
		except Exception as e:
			logging.error(
				"Couldn't get scores for poll %s - parsing error: %s",
				self.get_results_link(poll),
				e,
			)
			return None
