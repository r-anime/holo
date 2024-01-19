from logging import debug, info, warning, error, exception
import re
from datetime import UTC, datetime, timedelta
import dateutil.parser

from .. import AbstractServiceHandler
from data.models import Episode, UnprocessedStream

class ServiceHandler(AbstractServiceHandler):
    _show_url = "https://www.adultswim.com/videos/{id}/"
    _show_re = re.compile("adultswim.com/videos/([\w-]+)", re.I)

    def __init__(self):
        super().__init__("adultswim", "Adult Swim", False)

    # Episode finding

    def get_all_episodes(self, stream, **kwargs):
        info(f"Getting live episodes for {self.name}/{stream.show_key}")
        episode_datas = self._get_feed_episodes(stream.show_key, **kwargs)

        # Check episode validity and digest
        episodes = []
        for episode_data in episode_datas:
            if _is_valid_episode(episode_data, stream.show_key):
                try:
                    episodes.append(_digest_episode(episode_data))
                except:
                    exception(f"Problem digesting episode for {self.name}/{stream.show_key}")

        if len(episode_datas) > 0:
            debug(f"  {len(episode_datas)} episodes found, {len(episodes)} valid")
        else:
            debug("  No episode found")
        return episodes

    def _get_feed_episodes(self, show_key, **kwargs):
        info(f"Getting episodes for {self.name}/{show_key}")

        url = self._get_feed_url(show_key)

        # Send request
        response = self.request(url, html=True, **kwargs)
        if response is None:
            error(f"Cannot get show page for {self.name}/{show_key}")
            return list()

        # Parse html page
        sections = response.find_all("div", itemprop="episode")
        return sections


    @classmethod
    def _get_feed_url(cls, show_key):
        if show_key is not None:
            return cls._show_url.format(id=show_key)
        else:
            return None

    # Remove info getting

    def get_stream_info(self, stream, **kwargs):
        info(f"Getting stream info for {self.name}/{stream.show_key}")

        url = self._get_feed_url(stream.show_key)
        response = self.request(url, html=True, **kwargs)
        if response is None:
            error("Cannot get feed")
            return None

        stream.name = response.find("h1", itemprop="name").text
        return stream

    def get_seasonal_streams(self, **kwargs):
        # What is this for again ?
        return list()

    def get_stream_link(self, stream):
        return self._show_url.format(id=stream.show_key)

    def extract_show_key(self, url):
        match = self._show_re.search(url)
        if match:
            return match.group(1)
        return None

def _is_valid_episode(episode_data, show_key):
    # Don't check old episodes (possible wrong season !)
    date_string = episode_data.find("meta", itemprop="datePublished")["content"]
    date = datetime.fromordinal(dateutil.parser.parse(date_string).toordinal())

    date_diff = datetime.now(UTC).replace(tzinfo=None) - date

    if date_diff < timedelta(0):
        return False

    if date_diff >= timedelta(days=2):
        debug("  Episode too old")
        return False

    return True

def _digest_episode(feed_episode):
    debug("Digesting episode")

    name = feed_episode.find("h4", itemprop="name", class_="episode__title").text
    link = feed_episode.find("a", itemprop="url", class_="episode__link").href
    num = int(feed_episode.find("meta", itemprop="episodeNumber")["content"])

    date_string = feed_episode.find("meta", itemprop="dateCreated")["content"]
    date = datetime.fromordinal(dateutil.parser.parse(date_string).toordinal())

    return Episode(num, name, link, date)
