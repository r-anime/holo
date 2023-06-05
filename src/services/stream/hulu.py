"""
Service Handler for Hulu.

Information as of 2023/06/05:

The URL is of the form ``https://www.hulu.com/series/show_key``
where ``show_key`` is like ``title-with-dashes-followed-by-entity-id``
where ``entity-id`` is 5 'hashes' joined by dashes
Example:
show name: Tengoku Daimakyou
show key: tengoku-daimakyo-c0bba144-1fa6-4ee5-affc-1029c77cfb71

Series information can be obtained from the raw html of the series page.
They are part of a JSON contained in the element:

<script id="__NEXT_DATA__" type="application/json"></script>

Examples of the JSON are included in the example directory.
The relevant information is structured as follows:

JSON object -> "props" -> "pageProps"

which is a dictionary structured as follows:

"query": {"id": (string: show_key), ...},
"latestSeason": {"season": (string: latest season number), ...},
"layout": {
	"locale": (string: language code)
	"components": [
		{"type": "navigation", ...},
		{
			"type": "detailentity_masthead",
			"title": (string: show title),
			"entityId": (string: the internal ID of the show)
			"description": (string: synopsis)
			"premiereDate": (string: date in ISO format)
			...
		},
		{
			"type": "collection_tabs",
			"tabs": [
				{
					"title": "Episodes",
					"collection": {
						"items": [
							{
								"id": (string: episode ID),
								"type": "episode",
								"name": (str: episode title),
								"premiereDate": (str: date in ISO format),
								"seriesName": (str: show title),
							}, ...
						],
						...
					},
				},
				{
					"title": "Extras"
					(here go things like PVs)
				},
				{
					"title": "Details"
				}
			],
			...
		},
	],
	...
},
...
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

from data.models import Episode, Stream, UnprocessedStream

from .. import AbstractServiceHandler

logger = logging.getLogger(__name__)


@dataclass
class HuluEpisode:
	name: str = ""
	date: datetime = datetime.utcnow()
	season: int = 0
	number: int = 0
	series_name: str = ""


class InvalidHulu(Exception):
	"""Generic exception raised when parsing the contents of a Hulu webpage."""


class ServiceHandler(AbstractServiceHandler):
	_show_url = "http://hulu.com/series/{id}"
	_show_re = re.compile(r"hulu\.com\/series\/((?:\w+-?)+)", re.I)

	def __init__(self) -> None:
		super().__init__(key="hulu", name="Hulu", is_generic=False)

	def get_all_episodes(self, stream: Stream, **kwargs: Any) -> Iterable[Episode]:
		logger.info("Getting live episodes for Hulu/%s", stream.show_key)
		url = self.get_stream_link(stream=stream)
		if not url:
			return []
		response: str | None = self.request(url=url, **kwargs)
		if not response:
			logger.error("Cannot reach URL")
			return []
		try:
			json_contents = _get_json_data(raw_html=response)
			episodes_data = _get_episodes_data(json_contents)
		except (
			InvalidHulu,
			json.JSONDecodeError,
			KeyError,
			TypeError,
			AttributeError,
			StopIteration,
		):
			logger.error("Cannot extract malformed content")
			return []
		if not episodes_data:
			logger.debug("  No episodes found")
			return []
		episodes = list(map(_process_episode, filter(_is_valid_episode, episodes_data)))
		logger.debug("  %d episodes found, %d valid", len(episodes_data), len(episodes))
		return episodes

	def get_stream_link(self, stream: Stream) -> str | None:
		if not stream.show_key:
			logger.warning("Missing show key from stream %s", stream)
			return None
		return self._show_url.format(id=stream.show_key)

	def extract_show_key(self, url: str) -> str | None:
		match = self._show_re.search(url)
		if match:
			return match.group(1)
		return None

	def get_stream_info(self, stream: Stream, **kwargs: Any) -> Stream | None:
		logger.info("Getting stream info for Hulu/%s", stream.show_key)
		url = self.get_stream_link(stream)
		if not url:
			logger.error("Cannot get URL")
			return None
		response: str | None = self.request(url=url, **kwargs)
		if not response:
			logger.error("Cannot reach URL")
			return None
		try:
			json_contents = _get_json_data(raw_html=response)
			stream_name = _extract_series_name_from_json(json_contents)
		except (
			InvalidHulu,
			json.JSONDecodeError,
			KeyError,
			TypeError,
			AttributeError,
		):
			logger.error("Cannot extract malformed content")
			return None
		stream.name = stream_name
		return stream

	def get_seasonal_streams(self, **kwargs: Any) -> list[UnprocessedStream]:
		# Not implemented
		return []


def _get_json_data(raw_html: str) -> Any:
	pattern = r"<script id=\"__NEXT_DATA__\" type=\"application\/json\">(.+?)<\/script>"
	contents = re.findall(pattern, raw_html)
	if not contents:
		raise InvalidHulu
	if len(contents) > 1:
		logger.warning(
			"Multiple matches found, may have unexpected results. The first match will be used."
		)
	contents_json = json.loads(contents[0])
	return contents_json


def _extract_series_name_from_json(json_contents: Any) -> str:
	if json_contents["props"]["pageProps"]["layout"]["locale"].lower() != "en-us":
		logger.warning("  Language not en-us")
	components = json_contents["props"]["pageProps"]["layout"]["components"]
	head = next((c for c in components if c["type"] == "detailentity_masthead"), None)
	if not head:
		raise InvalidHulu
	return head["title"]


def _get_episodes_data(contents_json: Any) -> list[HuluEpisode]:
	page = contents_json["props"]["pageProps"]
	if page["layout"]["locale"].lower() != "en-us":
		logger.warning("Unexpected language detected, may have unexpected results")
	components = page["layout"]["components"]
	collection = next((c for c in components if c["type"] == "collection_tabs"))
	episode_container: list[dict[str, str]] = []
	episode_container = next(
		(
			tab["model"]["collection"]["items"]
			for tab in collection["tabs"]
			if tab["title"] == "Episodes"
		),
		episode_container,
	)
	if not episode_container:
		raise InvalidHulu
	episodes = list(
		filter(
			None,
			[_format_episode_from_json(episode) for episode in episode_container],
		)
	)
	return episodes


def _format_episode_from_json(episode_json: dict[str, str]) -> HuluEpisode | None:
	name = episode_json["name"]
	date = episode_json["premiereDate"]
	season = int(episode_json["season"])
	number = int(episode_json["number"])
	series_name = episode_json["seriesName"]
	if name.lower().startswith("(dub)"):
		return None
	if name.lower().startswith("(sub)"):
		name = name[6:]
	formatted_episode = HuluEpisode(
		name=name,
		date=datetime.fromisoformat(date).replace(tzinfo=None),
		# remove tzinfo as datetime.utcnow() is used elsewhere
		season=season,
		number=number,
		series_name=series_name,
	)
	return formatted_episode


_time_adjustments = {
	"Tengoku Daimakyo": timedelta(hours=1),  # 12pm UTC -> 1pm UTC
}

# ? Tengoku Daimakyou has a mismatch between listed time and actual release time
# ? Need to see what happens with new series

def _is_valid_episode(episode: HuluEpisode) -> bool:
	# Adjust time if needed, so the episode is not released too early
	episode.date += _time_adjustments.get(episode.series_name, timedelta(0))
	date_diff = datetime.utcnow() - episode.date
	if date_diff >= timedelta(days=2):
		logger.debug("  Episode S%dE%d too old", episode.season, episode.number)
		return False
	return True


def _process_episode(episode: HuluEpisode) -> Episode:
	return Episode(number=episode.number, name=episode.name, link="", date=episode.date)
