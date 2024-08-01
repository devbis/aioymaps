"""Async library to fetch info about stops from Yandex Maps."""

__version__ = "1.2.5"
__author__ = "Ivan Belokobylskiy"
__author_email__ = "belokobylskij@gmail.com"
__license__ = "MIT"
__url__ = "https://github.com/devbis/aioymaps"


import asyncio
import json
import re
from urllib.parse import urlencode

import aiohttp

DEFAULT_USER_AGENT = "https://pypi.org/project/aiomaps/"
RESOURCE_PATH = "maps/api/masstransit/getStopInfo"
AJAX_KEY = "ajax"
LANG_KEY = "lang"
LOCALE_KEY = "locale"
MODE_KEY = "mode"
SIGNATURE = "s"

CONFIG = {
    # this url bypasses bot checking in yandex
    "init_url": "https://yandex.ru/maps/2/moscow/",
    "params": {
        AJAX_KEY: 1,
        LANG_KEY: "ru",
        LOCALE_KEY: "ru_RU",
        MODE_KEY: "prognosis",
    },
    "headers": {"User-Agent": DEFAULT_USER_AGENT},
}
PARAMS = "params"
ID_KEY = "id"
URI_KEY = "uri"
CSRF_TOKEN_KEY = "csrfToken"
SESSION_KEY = "sessionId"

SCHEMA = [
    AJAX_KEY,
    CSRF_TOKEN_KEY,
    ID_KEY,
    LANG_KEY,
    LOCALE_KEY,
    MODE_KEY,
    SESSION_KEY,
    URI_KEY,
]


class CaptchaError(ValueError):
    pass


class NoSessionError(ValueError):
    pass


class YandexMapsRequester:
    """Class for requesting json with data from Yandex API."""

    def __init__(
        self,
        user_agent: str = None,
        client_session: aiohttp.ClientSession = None,
    ):
        """Set up the Yandex Map requester."""

        self._config = CONFIG.copy()  # need copy this dict
        if user_agent is not None:
            self._config["headers"]["User-Agent"] = user_agent
        if client_session:
            self.client_session = client_session
        else:
            self.client_session = aiohttp.ClientSession(
                requote_redirect_url=False,
            )
        # helps to avoid captcha by default (multiple requests still cause it)
        self.client_session.cookie_jar.update_cookies({
            "yandexuid": "1234567890123456789",
        })

    async def close(self):
        await self.client_session.close()

    async def set_new_session(self):
        """Initialize new session to API."""
        async with self.client_session.get(
            self._config["init_url"], headers=self._config["headers"]
        ) as resp:
            domain = resp.url.host
            reply = await resp.text()
            if 'captcha' in str(resp.real_url):
                raise CaptchaError("Captcha required")

        result = re.search(rf'"{CSRF_TOKEN_KEY}":"(\w+.\w+)"', reply)
        self._config[PARAMS][CSRF_TOKEN_KEY] = result.group(1)
        self._config["cookies"] = dict(resp.cookies)
        self._config['uri'] = f'https://{domain}/{RESOURCE_PATH}'

        # "sessionId":"1722498498103433-6243089018341556883-balancer-l7leveler-kubr-yp-sas-84-BAL"
        rx = re.search(rf'"{SESSION_KEY}":"([^"]+)"', reply)
        if not rx:
            raise NoSessionError("No session id found")
        self._config[PARAMS][SESSION_KEY] = rx.group(1)

        params = {}
        self._config[PARAMS][URI_KEY] = None  # init with none
        self._config[PARAMS][ID_KEY] = None

        for key in SCHEMA:  # according to the order
            params[key] = self._config[PARAMS][key]
        self._config[PARAMS] = params

    @staticmethod
    def _get_yandex_signature(params) -> str:
        """
        Original JS code on Yandex Maps.

        var t = i.stringify(e, {
            sort: function (e, t) {
                var n = e.toLowerCase(),
                r = t.toLowerCase();
                return n < r ? - 1 : n > r ? 1 : 0
            }
        });
        return t ? String(function (e) {
            for (var t = e.length, n = 5381, r = 0; r < t; r++)
                n = 33 * n ^ e.charCodeAt(r);
            return n >>> 0
            }(t))  : ''};
        """
        sort_params = dict(sorted(params.items(), key=lambda x: x[0].lower()))
        str_to_sign = urlencode(sort_params)
        if not str_to_sign:
            return ""

        result = 5381
        for char in str_to_sign:
            result = ((33 * result) ^ ord(char)) & 0xFFFFFFFF
        return str(result)

    @classmethod
    def _sign(cls, params):
        return {
            **params,
            SIGNATURE: cls._get_yandex_signature(params),
        }

    async def get_stop_info(self, stop_id):
        """Get transport data for stop_id in json."""
        if "cookies" not in self._config:
            await self.set_new_session()

        self._config[PARAMS][ID_KEY] = stop_id
        uri = f"ymapsbm1://transit/stop?id={stop_id}"
        self._config[PARAMS][URI_KEY] = uri
        async with self.client_session.get(
            self._config["uri"],
            params=self._sign(self._config[PARAMS]),
            cookies=self._config["cookies"],
            headers=self._config["headers"],
        ) as resp:
            result = await resp.text()
        try:
            return json.loads(result)
        except json.JSONDecodeError as loads_reply_error:
            return {
                "error": {"exception": loads_reply_error, "response": result},
            }


if __name__ == "__main__":
    import argparse
    from pprint import pprint

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--stop-id",
        help="ID of the stop from Yandex Maps",
    )

    async def do_request(value):
        requester = YandexMapsRequester()
        try:
            data = await requester.get_stop_info(value)
            pprint(data)
        finally:
            await requester.close()

    args = parser.parse_args()
    if args.stop_id:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(do_request(args.stop_id))
        finally:
            loop.close()
    else:
        parser.print_help()
