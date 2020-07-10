# Show search: https://www.nyaa.eu/?page=search&cats=1_37&filter=2&term=
# Show search (RSS): https://www.nyaa.eu/?page=rss&cats=1_37&filter=2&term=

from logging import debug, info, warning, error, exception
from datetime import datetime, timedelta
import re
from urllib.parse import quote_plus as url_quote

from .. import AbstractServiceHandler
from data.models import Episode

class ServiceHandler(AbstractServiceHandler):
	_search_base = "https://{domain}/?page=rss&c=1_2&f={filter}&q={q}&exclude={excludes}"
	_recent_list = "https://{domain}/?page=rss&c=1_2&f={filter}&exclude={excludes}"
	
	def __init__(self):
		super().__init__("nyaa", "Nyaa", True)
	
	# Episode finding
	
	def get_all_episodes(self, stream, **kwargs):
		info("Getting live episodes for Nyaa/{}".format(stream.show_key))
		episode_datas = self._get_feed_episodes(stream.show_key, **kwargs)
		
		# Check data validity and digest
		episodes = []
		for episode_data in episode_datas:
			if _is_valid_episode(episode_data):
				try:
					episode = _digest_episode(episode_data)
					if episode is not None:
						episodes.append(episode)
				except:
					exception("Problem digesting episode for Crunchyroll/{}".format(stream.show_key))
		
		if len(episode_datas) > 0:
			debug("  {} episodes found, {} valid".format(len(episode_datas), len(episodes)))
		else:
			debug("  No episodes found")
		return episodes

	def get_recent_episodes(self, streams, **kwargs):
		"""
		Returns all recent episode on the top of https://nyaa.si/?c=1_2.
		Return a list of episodes for each stream.
		"""
		torrents = self._get_recent_torrents(**kwargs)
		episodes = dict()

		for torrent in torrents:
			if not _is_valid_episode(torrent):
				continue

			stream = self._find_matching_stream(torrent, streams)
			if not stream:
				continue

			# A stream has been found, generate the episode
			try:
				episode = _digest_episode(torrent)
				if episode is not None:
					show_episodes = episodes.get(stream, list())
					show_episodes.append(episode)
					debug(f"Adding episode {episode.number} for show {stream.show.id}")
					episodes[stream] = show_episodes
			except:
				exception(f"Problem digesting torrent {torrent.id}")
		return episodes

	def _find_matching_stream(self, torrent, streams):
		debug(f"Searching matching stream for torrent {torrent.title}")
		for stream in streams:
			show = stream.show
			names = [show.name] + show.aliases

			for name in names:
				debug(f"  Trying: {name}")
				# Match if each word in the show name is in the torrent name
				# Intent is to allow inclusion of fansub group names
				words_show = set(_normalize_show_name(name).split())
				words_torrent = set(_normalize_show_name(torrent.title).split())
				if words_show.issubset(words_torrent):
					debug(f"  -> MATCH")
					info(f"Matching found for torrent {torrent.title}")
					info(f"  -> {show.name}")
					return stream
		info(f"No matching show found for torrent {torrent.title}")
		return None

	def _get_recent_torrents(self, **kwargs):
		"""
		Returns all torrents on the top of https://nyaa.si/?c=1_2.
		"""
		info("Getting all recent episodes on Nyaa")
		domain = self.config.get("domain", "nyaa.si")
		filter_ = self.config.get("filter", "2")
		excludes = self.config.get("excluded_users", "").replace(" ", "")
		url = self._recent_list.format(domain=domain, filter=filter_, excludes=excludes)

		response = self.request(url, rss=True, **kwargs)
		if response is None:
			error("Cannot get latest show for Nyaa")
			return list()

		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		return response.get("entries", list())

	def _get_feed_episodes(self, show_key, **kwargs):
		"""
		Always returns a list.
		"""
		info("Getting episodes for Nyaa/{}".format(show_key))
		if "domain" not in self.config or not self.config["domain"]:
			error("  Domain not specified in config")
			return list()
		
		# Send request
		query = re.sub("[`~!@#$%^&*()+=:;,.<>?/|\"]+", " ", show_key)
		query = re.sub("season", " ", query, flags=re.I)
		query = re.sub(" +", " ", query)
		query = re.sub("(?:[^ ])-", " ", query) # do not ignore the NOT operator
		debug("  query={}".format(query))
		query = url_quote(query, safe="", errors="ignore")
		
		domain = self.config.get("domain", "nyaa.si")
		filter_ = self.config.get("filter", "2")
		excludes = self.config.get("excluded_users", "").replace(" ", "")
		url = self._search_base.format(domain=domain, filter=filter_, excludes=excludes, q=query)
		response = self.request(url, rss=True, **kwargs)
		if response is None:
			error("Cannot get latest show for Nyaa/{}".format(show_key))
			return list()
		
		# Parse RSS feed
		if not _verify_feed(response):
			warning("Parsed feed could not be verified, may have unexpected results")
		return response.get("entries", list())
	
	# Don't need these!
	
	def get_stream_link(self, stream):
		return None
	
	def get_stream_info(self, stream, **kwargs):
		return None
	
	def extract_show_key(self, url):
		# The show key for Nyaa is just the search string
		return url
	
	def get_seasonal_streams(self, **kwargs):
		return list()

# Feed parsing

def _verify_feed(feed):
	debug("Verifying feed")
	if feed.bozo:
		debug("  Feed was malformed")
		return False
	debug("  Feed verified")
	return True

def _is_valid_episode(feed_episode):
	if any(ex.search(feed_episode["title"]) is not None for ex in _exludors):
		debug("  Excluded")
		return False
	episode_date = datetime(*feed_episode.published_parsed[:6])
	date_diff = datetime.utcnow() - episode_date
	if date_diff >= timedelta(days=2):
		debug("  Episode too old")
		return False
	number = _extract_episode_num(feed_episode["title"])
	if number is None or number <= 0:
		debug(f"  Probably not the right episode number ({number})")
		return False
	return True

def _digest_episode(feed_episode):
	title = feed_episode["title"]
	debug("Extracting episode number from \"{}\"".format(title))
	episode_num = _extract_episode_num(title)
	if episode_num is not None:
		debug("  Match found, num={}".format(episode_num))
		date = feed_episode["published_parsed"] or datetime.utcnow()
		link = feed_episode["id"]
		return Episode(episode_num, None, link, date)
	debug("  No match found")
	return None

_exludors = [re.compile(x, re.I) for x in [
	"\.srt$",
	r"\b(batch|vol(ume|\.)? ?\d+|dub|dubbed)\b",
	r"\b(bd|bluray|bdrip)\b",
	r"PV.?\d+",
	r"pre-?air",
	r"blackjaxx", # blacklisted uploaders
]]
_num_extractors = [re.compile(x, re.I) for x in [
	# " - " separator between show and episode
	r"\[(?:horriblesubs|commie|hiryuu|kuusou|fff|merchant|lolisubs|hitoku|erai-raws|davinci|asenshi|mezashite|anonyneko|pas|ryuujitk)\] .+ - (\d+) ",
	r"\[DameDesuYo\] .+ - (\d+)[ v]",
	r"\[Some-Stuffs\]_.+_(\d{3})_",
	r"\[(?:orz|hayaku|sxrp)\] .+ (\d+)", # No separator
	r"\[(?:kaitou|gg)\]_.+_-_(\d+)_", # "_-_" separator
	r"\[flysubs].+ - (\d+)\[.+\]", # "_-_" separator
	r".+_(\d+)\[(?:please_sub_this_viz)\]", # "_-_" separator
	r"\[doremi\]\..+\.(\d+)", # "." separator
	r"\[anon\] .+? (\d{2,})",
	r"\[seiya\] .+ - (\d+) \[.+\]",
	r"\[U3-Web\] .+ \[EP(\d+)\]",
	r"(?:.+).S(?:\d+)E(\d+).Laelaps.Calling.(?:\d+)p.(?:.+)",
	r"\[(?:SenritsuSubs|AtlasSubbed|Rakushun)\] .+ - (\d+)",
	r"\[.*?\][ _][^\(\[]+[ _](?:-[ _])?(\d+)[ _]", # Generic to make a best guess. Does not include . separation due to the common "XXX vol.01" format
	r".*?[ _](\d+)[ _]\[\d+p\]", # No tag followed by quality
	r".*?episode[ _](\d+)", # Completely unformatted, but with the "Episode XX" text
	r".*[ _]-[ _](\d+)(?:[ _].*)?$", # - separator
	r".*(\d+)\.mkv$", # num right before extension
]]

def _extract_episode_num(name):
	if any(ex.search(name) is not None for ex in _exludors):
		return None
	for regex in _num_extractors:
		match = regex.match(name)
		if match is not None:
			num = int(match.group(1))
			return num
	return None

def _normalize_show_name(name):
	"""
	Normalize a title for string comparison. Ignores all non-ASCII letter or digit symbols.
	Also removes "Season X" substrings and converts to lowercase.
	"""
	name = name.casefold()
	name = re.sub("[^a-z0-9]", " ", name)
	name = re.sub("season \d( part \d)?", " ", name)
	name = re.sub("\s+", " ", name)
	return name
