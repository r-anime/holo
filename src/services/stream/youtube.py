from logging import debug, info, warning, error, exception
import re
from datetime import datetime, timedelta

from .. import AbstractServiceHandler
from data.models import Episode, UnprocessedStream

class ServiceHandler(AbstractServiceHandler):
	_playlist_api_query = "https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&playlistId={id}&key={key}"
	_videos_api_query = "https://youtube.googleapis.com/youtube/v3/videos?part=status&part=snippet&hl=en&id={id}&key={key}"
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
		if url is None:
			error(f"Cannot get feed url for {self.name}/{show_key}")

		# Request channel information
		response = self.request(url, json=True, **kwargs)
		if response is None:
			error(f"Cannot get episode feed for {self.name}/{show_key}")
			return list()

		# Extract videos ids and build new query for all videos
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		feed = response.get("items", list())

		video_ids = [item["contentDetails"]["videoId"] for item in feed]
		url = self._get_videos_url(video_ids)

		# Request videos information
		response = self.request(url, json=True, **kwargs)
		if response is None:
			error(f"Cannot get video information for {self.name}/{show_key}")
			return list()

		# Return feed
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		return response.get("items", list())

	def _get_feed_url(self, show_key):
		# Show key is the channel ID
		if "api_key" not in self.config or not self.config["api_key"]:
			error("  Missing API key for access to Youtube channel")
			return None
		api_key = self.config["api_key"]
		if show_key is not None:
			return self._playlist_api_query.format(id=show_key, key=api_key)
		else:
			return None

	def _get_videos_url(self, video_ids):
		# Videos ids is a list of all videos in feed
		if "api_key" not in self.config or not self.config["api_key"]:
			error("  Missing API key for access to Youtube channel")
			return None
		api_key = self.config["api_key"]
		if video_ids:
			return self._videos_api_query.format(id=','.join(video_ids), key=api_key)
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
	if not (feed["kind"] == "youtube#playlistItemListResponse" or feed["kind"] == "youtube#videoListResponse"):
		debug("  Feed does not match request")
		return False
	if feed["pageInfo"]["totalResults"] > feed["pageInfo"]["resultsPerPage"]:
		debug(f"  Too many results ({feed['pageInfo']['totalResults']}), will not get all episodes")
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
	if feed_episode["status"]["privacyStatus"] == "private":
		info("  Video was excluded (is private)")
		return False
	if feed_episode["snippet"]["liveBroadcastContent"] == "upcoming":
		info("  Video was excluded (not yet online)")
		return False
	title = feed_episode["snippet"]["localized"]["title"]
	if len(title) == 0:
		info("  Video was exluded (no title found)")
		return False
	if any(ex.search(title) is not None for ex in _excludors):
		info("  Video was exluded (excludors)")
		return False
	if all(num.match(title) is None for num in _num_extractors):
		info("  Video was excluded (no episode number found)")
		return False
	return True

def _digest_episode(feed_episode):
	_video_url = "https://www.youtube.com/watch?v={video_id}"
	snippet = feed_episode["snippet"]

	title = snippet["localized"]["title"]
	episode_num = _extract_episode_num(title)
	if episode_num is None or not 0 < episode_num <720:
		return None

	date_string = snippet["publishedAt"].replace('Z', '')
	#date_string = snippet["publishedAt"].replace('Z', '+00:00') # Use this for offset-aware dates
	date = datetime.fromisoformat(date_string) or datetime.utcnow()

	link = _video_url.format(video_id=feed_episode["id"])
	return Episode(episode_num, None, link, date)

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
