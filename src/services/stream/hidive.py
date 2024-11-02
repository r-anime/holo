import functools
import json
from logging import debug, info, warning, error, exception
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from data.models import Episode, Stream, UnprocessedStream
from .. import AbstractServiceHandler


class HiDiveError(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(*args)
        self.message = message

class ServiceHandler(AbstractServiceHandler):
    _show_url = "https://www.hidive.com/season/{id}"
    _show_re = re.compile(r"hidive.com/season/(\d+)", re.I)

    def __init__(self) -> None:
        super().__init__("hidive", "HIDIVE", False)

    def get_all_episodes(self, stream: Stream, **kwargs: Any) -> list[Episode]:
        info(f"Getting live episodes for HiDive/{stream.show_key}")

        episode_datas = self._get_feed_episodes(stream.show_key, **kwargs)

        # HIDIVE does not include episode date in the show's page
        # Pre-process the data to obtain all the other information
        # Sort the episodes by descending number
        # Stop at the first invalid episode
        # (Assumption: all new episodes have increasing numbers)
        # This is to reduce the number of requests to make
        episodes_candidates = sorted(
            list(filter(None, map(_digest_episode, episode_datas))),
            key=lambda e: e.number,
            reverse=True,
        )

        episodes: list[Episode] = []
        for episode in episodes_candidates:
            try:
                if validated_episode := _validate_episode(
                    episode=episode, show_key=stream.show_key, **kwargs
                ):
                    episodes.append(validated_episode)
                else:
                    break
            except Exception:
                exception(
                    "Problem digesting episode for HiDive/%s: %s",
                    stream.show_key,
                    episode.link,
                )
        debug("  %d episodes found, %d valid", len(episode_datas), len(episodes))
        return episodes

    def _get_feed_episodes(self, show_key: str, **kwargs: Any) -> list[dict[str, Any]]:
        info(f"Getting episodes for HiDive/{show_key}")

        data = _load_anime_data(show_key)
        if not data:
            error("Cannot get show page for HiDive/%s", show_key)
            return []

        episodes = data["elements"][2]["attributes"]["items"]
        return episodes


    @classmethod
    def _get_feed_url(cls, show_key: str) -> str | None:
        if show_key:
            return cls._show_url.format(id=show_key)
        return None

    # Remove info getting

    def get_stream_info(self, stream: Stream, **kwargs: Any) -> Stream | None:
        info(f"Getting stream info for HiDive/{stream.show_key}")

        anime_data = _load_anime_data(stream.show_key)
        if not anime_data:
            error("Cannot get feed")
            return None

        try:
            title = anime_data["elements"][0]["attributes"]["header"]["attributes"][
                "text"
            ]
        except (KeyError, IndexError):
            error("Could not extract title")
            return None

        stream.name = title
        return stream


    def get_seasonal_streams(self, **kwargs: Any) -> list[UnprocessedStream]:
        # What is this for again ?
        return []

    def get_stream_link(self, stream: Stream) -> str:
        return self._show_url.format(id=stream.show_key)

    def extract_show_key(self, url: str) -> str | None:
        match = self._show_re.search(url)
        if match:
            return match.group(1)
        return None


_episode_url = "https://www.hidive.com/interstitial/{id}"
_episode_re = re.compile(r"https://www.hidive.com/interstitial/(\d+)")
_date_re = re.compile(r"Premiere: (\d+)/(\d+)/(\d+)")
# Only process episodes with episode number
# formatted like E1 or E1.00 (sic)
_episode_name_correct = re.compile(r"E(\d+)(?:\.00)? - (.*)")
# The title of unreleased episodes is "Coming m/d/y hh:mm UTC", we leave some leeway
_episode_name_invalid = re.compile(r"Coming \d+/\d+/\d+.*")


def _validate_episode(
    episode: Episode, show_key: str, **kwargs: Any
) -> Episode | None:
    episode_id = _episode_re.match(episode.link)
    if not episode_id:
        error("Invalid episode id parsing")
        return None

    episode_data = _load_episode_data(episode_id.group(1))
    if not episode_data:
        error("Invalid episode link for show HiDive/%s", show_key)
        return None

    try:
        content = episode_data["elements"][0]["attributes"]["content"]
        content_elt = next((c for c in content if c["$type"] == "tagList"))
        tags = content_elt["attributes"]["tags"]
        date_tag = next(
            (
                t
                for t in tags
                if t["attributes"]["text"].startswith("Original Premiere")
            )
        )
        date_data = date_tag["attributes"]["text"]
    except (IndexError, KeyError, StopIteration):
        error("Could not retrieve episode date: malformed episode data")
        return episode

    date_text = re.match(r"Original Premiere: (.*)", date_data)
    if not date_text:
        error("Invalid date text: %s", date_data)
        return episode
    date = datetime.strptime(date_text.group(1), "%B %d, %Y")

    # HiDive only has m/d/y, not hh:mm
    episode_day = datetime(day=date.day, month=date.month, year=date.year)
    date_diff = datetime.now(UTC).replace(tzinfo=None) - episode_day
    if date_diff >= timedelta(days=2):
        debug("  Episode too old")
        return None
    episode.date = episode_day
    return episode


def _digest_episode(feed_episode: dict[str, Any]) -> Episode | None:
    debug("Digesting episode")

    episode_link = _episode_url.format(id=feed_episode["id"])

    title_match = _episode_name_correct.match(feed_episode["title"])
    if not title_match:
        warning("Unknown episode number format in %s", episode_link)
        return None

    num, name = title_match.groups()
    num = int(num)
    if num == 0:
        warning("Excluding episode numbered 0: %s", episode_link)
        return None

    unreleased = _episode_name_invalid.match(name)
    if unreleased:
        debug("Excluding unreleased episode: %s", episode_link)
        return None

    date = datetime.now(UTC).replace(tzinfo=None)  # Not included in stream!

    return Episode(number=num, name=name, link=episode_link, date=date)


# With the update in March 2024,
# HiDive doesn't serve pages directly, but returns a bunch of javascript
# that executes further requests to get the page contents

# The following functions execute the relevant requests
# without having to emulating a web browser
# the resulting content is returned in a JSON format


def _load_page_data(
    element_id: int | str, base_url: str, content_url: str
) -> Any | None:
    try:
        js_path = _get_js_path(element_id, base_url)
        api_key = _get_api_key(js_path)
        auth_token = _get_auth_token(api_key)
        contents = _get_content_json(element_id, auth_token, api_key, content_url)
    except HiDiveError as e:
        error(e.message)
        return None
    return contents


_load_anime_data = functools.partial(
    _load_page_data,
    base_url="https://www.hidive.com/season/{}",
    content_url="https://dce-frontoffice.imggaming.com/api/v1/view?type=season&id={}",
)

_load_episode_data = functools.partial(
    _load_page_data,
    base_url="https://www.hidive.com/interstitial/{}",
    content_url="https://dce-frontoffice.imggaming.com/api/v1/view?type=VOD&id={}",
)


_re_js = re.compile(r"<script defer=\"defer\" src=\"(.*?/\d+\.js)\"></script>")
_re_api_key = re.compile(r"API_KEY:\"(.*?)\"")
_re_auth_token = re.compile(r"authorisationToken\":\"(.*?)\"")


def _get_js_path(element_id: int | str, base_url: str) -> str:
    url = base_url.format(element_id)
    debug("Fetching landing page: %s", url)
    r = requests.get(url, timeout=60)
    if not r.ok:
        raise HiDiveError(f"Couldn't fetch landing page. Status code: {r.status_code}")
    json_path = _re_js.findall(r.text)[-1]
    if not json_path:
        raise HiDiveError(f"Couldn't find the JS path on the page: {url}")
    return json_path


def _get_api_key(js_path: str) -> str:
    url = f"https://www.hidive.com{js_path}"
    debug("Retrieving API key: %s", url)
    r = requests.get(url, timeout=60)
    if not r.ok:
        raise HiDiveError(
            f"Failed to request the page containing the API key: {url} - "
            f"Status code: {r.status_code}"
        )
    match = _re_api_key.search(r.text)
    if not match:
        raise HiDiveError(f"Failed to find the API key in the page: {url}")
    return match.group(1)


def _get_auth_token(api_key: str) -> str:
    url = "https://dce-frontoffice.imggaming.com/api/v1/init/"
    debug("Obtaining auth token using the provided API key: %s", url)
    r = requests.get(
        url,
        headers={"Origin": "https://www.hidive.com", "X-Api-Key": api_key},
        timeout=60,
    )
    if not r.ok:
        raise HiDiveError(
            f"Failed to request the page containing the auth token: {url} - "
            f"Status code: {r.status_code}"
        )
    match = _re_auth_token.search(r.text)
    if not match:
        raise HiDiveError(f"Failed to find the auth token in the page: {url}")
    return match.group(1)


def _get_content_json(
    element_id: int | str, auth_token: str, api_key: str, content_url: str
) -> Any:
    url = content_url.format(element_id)
    debug("Retrieving page JSON data")
    r = requests.get(
        url,
        headers={
            "Realm": "dce.hidive",
            "Authorization": f"Bearer {auth_token}",
            "X-Api-Key": api_key,
        },
        timeout=60,
    )
    if not r.ok:
        raise HiDiveError(
            f"Failed to request the content page: {url} - Status code: {r.status_code}"
        )
    try:
        j = json.loads(r.text)
    except json.JSONDecodeError as e:
        raise HiDiveError(
            f"Failed to decode the content page as valid JSON: {url}"
        ) from e
    return j
