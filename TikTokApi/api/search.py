from __future__ import annotations

from urllib.parse import urlencode

from typing import TYPE_CHECKING, Iterator, Type

from .user import User
from .sound import Sound
from .hashtag import Hashtag
from .video import Video

if TYPE_CHECKING:
    from ..tiktok import TikTokApi

import requests


class Search:
    """Contains static methods about searching."""

    parent: TikTokApi

    @staticmethod
    def users_old(search_term, count=28, **kwargs) -> Iterator[User]:
        """
        Searches for users.

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.

        Example Usage
        ```py
        for user in api.search.users('therock'):
            # do something
        ```
        """
        return Search.discover_type(search_term, prefix="user", count=count, **kwargs)

    @staticmethod
    def sounds_old(search_term, count=28, **kwargs) -> Iterator[Sound]:
        """
        Searches for sounds.

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.

        Example Usage
        ```py
        for user in api.search.sounds('funny'):
            # do something
        ```
        """
        return Search.discover_type(search_term, prefix="music", count=count, **kwargs)

    @staticmethod
    def hashtags_old(search_term, count=28, **kwargs) -> Iterator[Hashtag]:
        """
        Searches for hashtags/challenges.

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.

        Example Usage
        ```py
        for user in api.search.hashtags('funny'):
            # do something
        ```
        """
        return Search.discover_type(
            search_term, prefix="challenge", count=count, **kwargs
        )

    @staticmethod
    def discover_type(search_term, prefix, count=28, offset=0, **kwargs) -> Iterator:
        """
        Searches for a specific type of object.
        You should instead use the users/sounds/hashtags as they all use data
        from this function.

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - prefix (str): either user|music|challenge
            - count (int): The amount of videos you want returned.

        Example Usage
        ```py
        for user in api.search.discover_type('therock', 'user'):
            # do something
        ```

        """
        # TODO: Investigate if this is actually working as expected. Doesn't seem to be
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = Search.parent._process_kwargs(kwargs)
        kwargs["custom_device_id"] = device_id

        cursor = offset
        page_size = 28

        while cursor - offset < count:
            query = {
                "discoverType": 0,
                "needItemList": False,
                "keyWord": search_term,
                "offset": cursor,
                "count": page_size,
                "useRecommend": False,
                "language": "en",
            }
            path = "api/discover/{}/?{}&{}".format(
                prefix, Search.parent._add_url_params(), urlencode(query)
            )
            data = Search.parent.get_data(path, **kwargs)

            for x in data.get("userInfoList", []):
                yield User(data=x["user"])

            for x in data.get("musicInfoList", []):
                yield Sound(data=x["music"])

            for x in data.get("challengeInfoList", []):
                yield Hashtag(data=x["challenge"])

            if int(data["offset"]) <= offset:
                Search.parent.logger.info(
                    "TikTok is not sending videos beyond this point."
                )
                return

            offset = int(data["offset"])

    @staticmethod
    def videos(search_term, count=28, offset=0, **kwargs) -> Iterator[Video]:
        """
        Searches for Videos

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.
            TODO: Figure out offset

        Example Usage
        ```py
        for video in api.search.videos('therock'):
            # do something
        ```
        """
        return Search.search_type(
            search_term, "item", count=count, offset=offset, **kwargs
        )

    @staticmethod
    def users(search_term, count=28, offset=0, **kwargs) -> Iterator[User]:
        """
        Searches for users using an alternate endpoint than Search.users

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.

        Example Usage
        ```py
        for user in api.search.users_alternate('therock'):
            # do something
        ```
        """
        return Search.search_type(
            search_term, "user", count=count, offset=offset, **kwargs
        )

    @staticmethod
    def search_type(search_term, obj_type, count=28, offset=0, **kwargs) -> Iterator:
        """
        Searches for users using an alternate endpoint than Search.users

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.
            - obj_type (str): user | item

        Just use .video & .users
        ```
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = Search.parent._process_kwargs(kwargs)
        kwargs["custom_device_id"] = device_id

        cursor = offset

        spawn = requests.head(
            "https://www.tiktok.com",
            proxies=Search.parent._format_proxy(proxy),
            **Search.parent.requests_extra_kwargs
        )
        ttwid = spawn.cookies["ttwid"]

        # For some reason when <= it can be off by one.
        while cursor - offset <= count:
            query = {
                "keyword": search_term,
                "cursor": cursor,
                "app_language": Search.parent.language,
            }
            path = "api/search/{}/full/?{}&{}".format(
                obj_type, Search.parent._add_url_params(), urlencode(query)
            )

            if obj_type == "user":
                subdomain = "www"
            elif obj_type == "item":
                subdomain = "us"
            else:
                raise TypeError("invalid obj_type")

            api_response = Search.parent.get_data(
                path, subdomain=subdomain, ttwid=ttwid, **kwargs
            )

            # When I move to 3.10+ support make this a match switch.
            for result in api_response.get("user_list", []):
                yield User(data=result)

            for result in api_response.get("item_list", []):
                yield Video(data=result)

            if api_response.get("has_more", 0) == 0:
                Search.parent.logger.info(
                    "TikTok is not sending videos beyond this point."
                )
                return

            cursor = int(api_response.get("cursor", cursor))
