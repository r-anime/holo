from logging import debug, info, warning, error, exception
import re
from datetime import datetime, timedelta

from .. import AbstractServiceHandler
from data.models import Episode, UnprocessedStream

class ServiceHandler(AbstractServiceHandler):
    # There are two ways to refer to a show on hidive: by show name with /tv/
    # and by a numeric id with /season/. Since our sources have used both over time,
    # we must support both versions.
    _show_url = "https://www.hidive.com/{id}"
    _show_res = [re.compile("hidive.com/(tv/[\w-]+)", re.I),
                 re.compile("hidive.com/(season/\d+)", re.I)]

    # An undocumented HiDive API that appears to be used by its mobile app.
    # Inspiration taken from https://github.com/anidl/multi-downloader-nx/blob/master/hidive.ts
    # rpp is the number of episodes fetched. It only goes to 20.
    _api_query = "https://dce-frontoffice.imggaming.com/api/v4/{key}?rpp=20"
    _api_headers = {'X-Api-Key': '857a1e5d-e35e-4fdf-805b-a87b6f8364bf',
                    'X-App-Var': '6.0.1.bbf09a2',
                    'realm': 'dce.hidive',
                    'Referer': 'https://www.hidive.com/',
                    'Origin': 'https://www.hidive.com'
                   }
    _api_auth_token = None

    def __init__(self):
        super().__init__("hidive", "HIDIVE", False)

    # Episode finding

    def get_all_episodes(self, stream, **kwargs):
        info(f"Getting live episodes for HiDive/{stream.show_key}")
        episode_datas = self._get_feed_episodes(stream.show_key, **kwargs)

        # Check episode validity and digest
        episodes = []
        for episode_data in episode_datas:
            if _is_valid_episode(episode_data, stream.show_key):
                try:
                    episode = _digest_episode(episode_data)
                    if episode is not None:
                        episodes.append(episode)
                except:
                    exception(f"Problem digesting episode for HiDive/{stream.show_key}")

        if len(episode_datas) > 0:
            debug(f"  {len(episode_datas)} episodes found, {len(episodes)} valid")
        else:
            debug("  No episode found")
        return episodes

    def _get_feed_episodes(self, show_key, **kwargs):
        info(f"Getting episodes for HiDive/{show_key}")

        headers = self._api_headers
        headers['Authorization'] = "Bearer " + self._get_api_auth_token()
        last_seen = None
        episodes = []

        # This will cover the first 400 episodes. Currently, the odds of a Hidive
        # show having more than 400 episodes seems lower than the odds of Hidive's
        # api bugging and always saying there are more episodes, which would otherwise
        # stall holo forever.
        for _ in range(20):
            url = self._get_feed_url(show_key, last_seen)
            response = self.request(url, json=True, headers=headers, **kwargs)
            if response is None:
                error(f"Cannot get show page for HiDive/{show_key}")
                return list()

            for ep in response['episodes']:
                if "onlinePlayback" in ep:
                    if ep["onlinePlayback"] == "AVAILABLE":
                        episodes.append(ep)
                else:
                    warning("  HiDive API returned JSON not matching expectations: onlinePlayback")

            if ( "paging" in response and "moreDataAvailable" in response["paging"]
                  and "lastSeen" in response["paging"]):
                if response["paging"]["moreDataAvailable"]:
                    last_seen = response["paging"]["lastSeen"]
                    debug("Fetching additional page from HiDive's API")
                else:
                    break
            else:
                warning("  HiDive API returned JSON not matching expectations: paging")
                break

        return episodes


    @classmethod
    def _get_feed_url(cls, show_key, last_seen=None):
        # This api only works with /season/ style hidive identifiers.
        if show_key is not None and show_key.startswith("season/"):
            url =  cls._api_query.format(key=show_key)
            if last_seen is not None:
                url += "&lastSeen=" + str(last_seen)
            return url
        else:
            return None

    @classmethod
    def _get_api_auth_token(cls):
        # The auth token easily lasts a full holo run, so we assume any one we have is valid.
        # If just getting through all HiDive shows takes longer than the token lasts,
        # we have far greater issues.
        if cls._api_auth_token:
            debug("  HiDive API key from cache")
            return cls._api_auth_token

        init = cls.request(cls, "https://dce-frontoffice.imggaming.com/api/v1/init",
                            headers=cls._api_headers, json=True)
        tok = init['authentication']['authorisationToken']
        cls._api_auth_token = tok
        debug("  HiDive API key from endpoint")
        return tok



    # Remove info getting

    def get_stream_info(self, stream, **kwargs):
        info(f"Getting stream info for HiDive/{stream.show_key}")

        url = self._get_feed_url(stream.show_key)
        headers = self._api_headers
        headers['Authorization'] = "Bearer " + self._get_api_auth_token()
        response = self.request(url, json=true, headers=headers, **kwargs)
        if response is None:
            error("Cannot get feed")
            return None

        if "series" in response and "title" in response["series"]:
            return response["series"]["title"]

        error("Could not extract title")
        return None

    def get_seasonal_streams(self, **kwargs):
        # What is this for again ?
        return list()

    def get_stream_link(self, stream):
        return self._show_url.format(id=stream.show_key)

    def extract_show_key(self, url):
        for re in self._show_res:
            match = re.search(url)
            if match:
                return match.group(1)
        return None

def _is_valid_episode(episode_data, show_key):
    if ( "episodeInformation" in episode_data
         and "episodeNumber" in episode_data["episodeInformation"]
         and "title" in episode_data and "id" in episode_data ):
           return True
    warning("  HiDive API returned JSON not matching expectations: episode data")
    return False

def _digest_episode(feed_episode):
    debug("Digesting episode")

    num = feed_episode["episodeInformation"]["episodeNumber"]
    if num <= 0:
        debug("Rejected episode for invalid number: {}", num)
        return None

    # Remove the leading 'E\d+ - ' from the title.
    name = feed_episode["title"].split(" - ", maxsplit=1)[1]

    link = "https://www.hidive.com/video/" + str(feed_episode["id"])

    # The API does not return a timestamp.
    date = datetime.utcnow()

    return Episode(number=num, name=name, link=link, date=date)
