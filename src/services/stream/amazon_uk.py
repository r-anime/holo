from logging import debug, info, warning, error, exception
import re
from datetime import datetime, timedelta
import dateutil.parser

from .. import AbstractServiceHandler
from data.models import Episode, UnprocessedStream

class ServiceHandler(AbstractServiceHandler):
    _show_url = "https://www.amazon.co.uk/dp/{id}"
    _show_re = re.compile("amazon.co.uk/(?:[\w-]+/)?dp/([\w-]+)", re.I)

    def __init__(self):
        super().__init__("amazon_uk", "Amazon UK", False)

    # Episode finding

    def get_all_episodes(self, stream, **kwargs):
        info(f"Getting live episodes for Amazon UK/{stream.show_key}")
        episode_datas = self._get_feed_episodes(stream.show_key, **kwargs)

        # Check episode validity and digest
        episodes = []
        for episode_data in episode_datas:
            if _is_valid_episode(episode_data, stream.show_key):
                try:
                    episodes.append(_digest_episode(episode_data))
                except:
                    exception(f"Problem digesting episode for Amazon UK/{stream.show_key}")

        if len(episode_datas) > 0:
            debug(f"  {len(episode_datas)} episodes found, {len(episodes)} valid")
        else:
            debug("  No episode found")
        return episodes

    def _get_feed_episodes(self, show_key, **kwargs):
        info(f"Getting episodes for Amazon UK/{show_key}")

        url = self._get_feed_url(show_key)

        # Send request
        response = self.request(url, html=True, **kwargs)
        if response is None:
            error(f"Cannot get show page for Amazon UK/{show_key}")
            return list()

        # Parse html page
        sections = response.find_all("div", class_ = "dv-episode-container")
        return sections


    @classmethod
    def _get_feed_url(cls, show_key):
        if show_key is not None:
            return cls._show_url.format(id=show_key)
        else:
            return None

    # Remove info getting

    def get_stream_info(self, stream, **kwargs):
        info(f"Getting stream info for Amazon UK/{stream.show_key}")

        url = self._get_feed_url(stream.show_key)
        response = self.request(url, html=True, **kwargs)
        if response is None:
            error("Cannot get feed")
            return None

        stream.name = response.find("h1", {'data-automation-id': "title"}).text
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

_episode_id = re.compile("dv-el-id-\d+")
_episode_date_key = re.compile("\s*Release date:\s*")

_episode_re = re.compile("https://www.hidive.com/stream/[\w-]+/s\d{2}e(\d{3})", re.I)
_episode_re_alter = re.compile("https://www.hidive.com/stream/[\w-]+/\d{4}\d{2}\d{2}(\d{2})", re.I)
_episode_name_correct = re.compile("(?:E\d+|Shorts) \| (.*)")
_episode_name_invalid = re.compile(".*coming soon.*", re.I)

def _is_valid_episode(episode_data, show_key):
    # Possibly other cases to watch ?
    return _episode_id.match(episode_data.attrs["id"])

def _digest_episode(feed_episode):
    debug("Digesting episode")

    title = feed_episode.find("div", class_ = "dv-el-title").text.strip()

    num, name = title.split(".")
    num = int(num)
    name = name.strip()
    link = None

    date_string = feed_episode.find(string = _episode_date_key).parent.next_sibling.next_sibling.string.strip()
    date = dateutil.parser.parse(date_string)

    return Episode(num, name, link, date)
