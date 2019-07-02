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
	
	def _get_feed_episodes(self, show_key, **kwargs):
		"""
		Always returns a list.
		"""
		info("Getting episodes for Nyaa/{}".format(show_key))
		if "domain" not in self.config or not self.config["domain"]:
			error("  Domain not specified in config")
			return list()
		
		# Send request
		query = re.sub("[-`~!@#$%^&*()+=:;,.<>?/|\\'\"]+", " ", show_key)
		query = re.sub("season", " ", query, flags=re.I)
		query = re.sub(" +", " ", query)
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
	episode_date = datetime(*feed_episode.published_parsed[:6])
	date_diff = datetime.utcnow() - episode_date
	if date_diff >= timedelta(days=2):
		debug("  Episode too old")
		return False
	number = _extract_episode_num(feed_episode["title"])
	if number is None or not (0 < number < 720) or number == 501:
		debug(f"  Probably not the right episode number ({number})")
		return False
	return True

def _digest_episode(feed_episode):
	title = feed_episode["title"]
	episode_num = _extract_episode_num(title)
	if episode_num is not None and 0 <= episode_num < 720:
		date = feed_episode["published_parsed"] or datetime.utcnow()
		link = feed_episode["id"]
		return Episode(episode_num, None, link, date)
	return None

_exludors = [re.compile(x, re.I) for x in [
	"\.srt$",
	r"\b(batch|vol(ume|\.)? ?\d+|dub|dubbed)\b",
	r"\b(bd|bluray)\b",
	r"PV.?\d+",
	r"pre-?air",
]]
_num_extractors = [re.compile(x, re.I) for x in [
	# " - " separator between show and episode
	r"\[(?:horriblesubs|commie|hiryuu|kuusou|fff|merchant|lolisubs|hitoku|erai-raws|davinci|asenshi|mezashite|anonyneko|pas|ryuujitk)\] .+ - (\d+) ",
	r"\[DameDesuYo\] .+ - (\d+)[ v]",
	r"\[(?:orz|hayaku|sxrp)\] .+ (\d+)", # No separator
	r"\[(?:kaitou|gg)\]_.+_-_(\d+)_", # "_-_" separator
	r"\[flysubs].+ - (\d+)\[.+\]", # "_-_" separator
	r".+_(\d+)\[(?:please_sub_this_viz)\]", # "_-_" separator
	r"\[doremi\]\..+\.(\d+)", # "." separator
	r"\[anon\] .+? (\d{2,})",
	r"\[seiya\] .+ - (\d+) \[.+\]",
	r"\[U3-Web\] .+ \[EP(\d+)\]",
	r"\[.*?\][ _][^\(\[]+[ _](?:-[ _])?(\d+)[ _]", # Generic to make a best guess. Does not include . separation due to the common "XXX vol.01" format
	r".*?[ _](\d+)[ _]\[\d+p\]", # No tag followed by quality
	r".*?episode[ _](\d+)", # Completely unformatted, but with the "Episode XX" text
	r".*[ _]-[ _](\d+)(?:[ _].*)?$", # - separator
]]

def _extract_episode_num(name):
	debug("Extracting episode number from \"{}\"".format(name))
	if any(ex.search(name) is not None for ex in _exludors):
		debug("  Excluded")
		return None
	for regex in _num_extractors:
		match = regex.match(name)
		if match is not None:
			num = int(match.group(1))
			debug("  Match found, num={}".format(num))
			return num
	debug("  No match found")
	return None
