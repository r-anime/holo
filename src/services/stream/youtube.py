from logging import debug, info, warning, error, exception
import re
from datetime import datetime, timedelta

from .. import AbstractServiceHandler
from data.models import Episode, UnprocessedStream

class ServiceHandler(AbstractServiceHandler):
	_channel_feed = "https://www.youtube.com/feeds/videos.xml?playlist_id={id}"
	_channel_url = "https://www.youtube.com/playlist?list={id}"
	_channel_re = re.compile("youtube.com/playlist\\?list=([\w-]+)", re.I)

	def __init__(self):
		super().__init__("youtube", "Youtube", False)

	# Episode finding

	def get_all_episodes(self, stream, **kwargs):
		info(f"Getting live episodes for Youtube/{stream.show_key}")
		episode_datas = self._get_feed_episodes(stream.show_key, **kwargs)

		# Extract valid episodes from feed and digest
		episodes = []
		for episode_data in episode_datas:
			if _is_valid_episode(episode_data, stream.show_key):
				try:
					episodes.append(_digest_episode(episode_data))
				except:
					exception(f"Problem digesting episode for Youtube/{stream.show_key}")

		if len(episode_datas) > 0:
			debug("  {} episodes found, {} valid".format(len(episode_datas), len(episodes)))
		else:
			debug("  No episodes found")
		return episodes

	def _get_feed_episodes(self, show_key, **kwargs):
		url = self._get_feed_url(show_key)

		# Request channel information
		response = self.request(url, rss=True, **kwargs)
		if response is None:
			error(f"Cannot get episode feed for Youtube/{show_key}")
			return list()

		# Return feed
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		return response.get("entries", list())

	@classmethod
	def _get_feed_url(cls, show_key):
		# Show key is the channel ID
		if show_key is not None:
			return cls._channel_feed.format(id=show_key)
		else:
			return None

	def get_stream_info(self, stream, **kwargs):
		# Can't trust consistent stream naming, ignored
		return None

	def get_seasonal_streams(self, **kwargs):
		# What is this for again ?
		return list()

	def get_stream_link(self, stream):
		return self._channel_url.format(id=stream.show_key)

	def extract_show_key(self, url):
		match = self._channel_re.search(url)
		if match:
			return match.group(1)
		return None

# Episode feeds format

def _verify_feed(feed):
	debug("Verifying feed")
	if feed.bozo:
		debug("  Feed was malformed")
		return False
	if "yt" not in feed.namespaces or feed.namespaces["yt"] != "http://www.youtube.com/xml/schemas/2015":
		debug("  Youtube name space not found or unexpected version")
		return False
	debug("  Feed verified")
	return True

_excludors = [re.compile(x, re.I) for x in [
	"(?:[^a-zA-Z]|^)(?:PV|OP|ED)(?:[^a-zA-Z]|$)",
	"blu.?ray",
]]

_num_extractors = [re.compile(x, re.I) for x in [
	r".*\D(\d{2,3})(?:\D|$)",
	r".*episode (\d+)(?:\D|$)",
]]

def _is_valid_episode(feed_episode, show_id):
	title = feed_episode.get("title", "")
	if len(title) == 0:
		return False
	if any(ex.search(title) is not None for ex in _excludors):
		return False
	if all(num.match(title) is None for num in _num_extractors):
		return False
	stats = feed_episode.get("media_statistics", dict())
	views = int(stats.get("views", 0))
	if views <= 99:
		return False
	return True

def _digest_episode(feed_episode):
	title = feed_episode["title"]
	episode_num = _extract_episode_num(title)
	if episode_num is not None and 0 <= episode_num < 720:
		date = feed_episode["published_parsed"] or datetime.utcnow()
		link = feed_episode["link"]
		return Episode(episode_num, None, link, date)
	return None

def _extract_episode_num(name):
	debug(f"Extracting episode number from \"{name}\"")
	if any(ex.search(name) is not None for ex in _excludors):
		return None
	for regex in _num_extractors:
		match = regex.match(name)
		if match is not None:
			num = int(match.group(1))
			debug(f"  Match found, num={num}")
			return num
	debug("  No match found")
	return none
