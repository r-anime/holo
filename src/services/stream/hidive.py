import re
from datetime import datetime, timedelta
from logging import debug, error, exception, info, warning
from typing import Any

from bs4 import BeautifulSoup, Tag

from data.models import Episode, Stream, UnprocessedStream

from .. import AbstractServiceHandler


class ServiceHandler(AbstractServiceHandler):
    _show_url = "https://www.hidive.com/tv/{id}"
    _show_re = re.compile("hidive.com/tv/([\w-]+)", re.I)
    _date_re = re.compile(r"Premiere: (\d+)/(\d+)/(\d+)")

    def __init__(self):
        super().__init__("hidive", "HIDIVE", False)

    # Episode finding

    def get_all_episodes(self, stream: Stream, **kwargs: Any) -> list[Episode]:
        info(f"Getting live episodes for HiDive/{stream.show_key}")
        episodes: list[Episode] = []
        episode_datas = self._get_feed_episodes(stream.show_key, **kwargs)

        # HIDIVE does not include episode date in the show's page
        # Pre-process the data to obtain all the other information
        # Sort the episodes by descending number
        # Check individual episode dates, stop at the first invalid episode
        # (Assumption: all new episodes have increasing numbers,
        # to reduce the number of requests to make)
        try:
            episode_candidates = sorted(
                list(filter(None, map(_digest_episode, episode_datas))),
                key=lambda e: e.number,
                reverse=True,
            )
        except Exception:
            exception("Problem digesting episode for HiDive/%s", stream.show_key)
            return episodes

        for episode in episode_candidates:
            try:
                episode = self._to_valid_episode(episode, stream.show_key, **kwargs)
                if not episode:
                    break
                episodes.append(episode)
            except Exception:
                exception("Problem validating episode for HiDive/%s", stream.show_key)

        if len(episode_datas) > 0:
            debug(f"  {len(episode_datas)} episodes found, {len(episodes)} valid")
        else:
            debug("  No episode found")
        return episodes

    def _get_feed_episodes(self, show_key: str, **kwargs: Any) -> list[Tag]:
        info(f"Getting episodes for HiDive/{show_key}")

        url = self._get_feed_url(show_key)

        # Send request
        response = self.request(url, html=True, **kwargs)
        if response is None:
            error(f"Cannot get show page for HiDive/{show_key}")
            return list()

        # Parse html page
        sections = response.find_all("div", {"data-section": "episodes"})
        #return [section.a['data-playurl'] for section in sections if section.a]
        return sections


    def _to_valid_episode(self, episode: Episode, show_key: str, **kwargs: Any) -> Episode | None:
        response: BeautifulSoup = self.request(episode.link, html=True, **kwargs)
        if not (response and response.h2):
            warning("Invalid episode link for show %s/%s", self.key, show_key)
            return episode
        match = self._date_re.search(response.h2.text or "")
        if not match:
            warning("Date not found")
            return episode
        month, day, year = map(int, match.groups()) # MM/DD/YY date format
        episode_day = datetime(day=day,month=month,year=year)
        date_diff = datetime.utcnow() - episode_day
        if date_diff >= timedelta(days=2):
            debug("  Episode too old")
            return None
        episode.date = episode_day
        return episode


    @classmethod
    def _get_feed_url(cls, show_key):
        if show_key is not None:
            return cls._show_url.format(id=show_key)
        else:
            return None

    # Remove info getting

    def get_stream_info(self, stream, **kwargs):
        info(f"Getting stream info for HiDive/{stream.show_key}")

        url = self._get_feed_url(stream.show_key)
        response = self.request(url, html=True, **kwargs)
        if response is None:
            error("Cannot get feed")
            return None

        title_section = response.find("div", {"class": "episodes"})
        if title_section is None:
           error("Could not extract title")
           return None

        stream.name = title_section.h1.text
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

_episode_re = re.compile("(?:https://www.hidive.com)?/stream/[\w-]+/s\d{2}e(\d{3})", re.I)
_episode_re_alter = re.compile("(?:https://www.hidive.com)?/stream/[\w-]+/\d{4}\d{2}\d{2}(\d{2})", re.I)
_episode_name_correct = re.compile("(?:E\d+|Shorts) ?\| ?(.*)")
_episode_name_invalid = re.compile(".*coming soon.*", re.I)

def _digest_episode(feed_episode: Tag) -> Episode | None:
    debug("Digesting episode")
    if not feed_episode.a:
        return None
    link = f"https://www.hidive.com{feed_episode.a['href']}"

    # Get data
    num_match = _episode_re.match(link)
    num_match_alter = _episode_re_alter.match(link)
    if num_match:
        num = int(num_match.group(1))
    elif num_match_alter:
        warning("Using alternate episode key format")
        num = int(num_match_alter.group(1))
    else:
        warning("Unknown episode number format in %s", link)
        return None
    if num <= 0:
        return None

    name = feed_episode.h2.text if feed_episode.h2 else ""
    name_match = _episode_name_correct.match(name)
    if name_match:
        debug("  Corrected title from %s", name)
        name = name_match.group(1)
    if _episode_name_invalid.match(name):
        warning("  Episode title not found")
        name = ""

    date = datetime.utcnow() # Not included in stream page!

    return Episode(num, name, link, date)
