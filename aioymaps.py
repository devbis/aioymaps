"""Async library to fetch info about stops from Yandex Maps."""

__version__ = "1.2.3"
__author__ = "Ivan Belokobylskiy"
__author_email__ = "belokobylskij@gmail.com"
__license__ = "MIT"
__url__ = "https://github.com/devbis/aioymaps"


import asyncio
import json
import random
import re
import string
import sys
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
    "init_url1": "https://yandex.ru/maps/2/moscow/",
    "init_url2": "https://yandex.ru/maps/api/taxi/getRoute?ajax=1&csrfToken=0962cd6e52474c553cc6a36275b19ec24aced6b0%3A1656837297&lang=ru_RU&rll=~14.350992%2C50.219835&s=856352337&sessionId=1656837297082_213067",
    "init_url3": "https://yandex.ru/maps/10511/prague/?mode=search&text=%D0%9A%D1%80%D0%B0%D1%81%D0%BE%D1%82%D0%B0&display-text=%D0%A1%D0%B0%D0%BB%D0%BE%D0%BD%D1%8B%20%D0%BA%D1%80%D0%B0%D1%81%D0%BE%D1%82%D1%8B",
    "init_url": "https://yandex-com.translate.goog/maps/?_x_tr_sl=en&_x_tr_tl=ru&_x_tr_hl=ru&_x_tr_pto=wapp",
    "params": {
        AJAX_KEY: 1,
        LANG_KEY: "ru",
        LOCALE_KEY: "ru_RU",
        MODE_KEY: "prognosis",
    },
    "headers": {
        "User-Agent": DEFAULT_USER_AGENT,
        # "X-Retpath-Y": "https://yandex.ru/maps/107270/odolena-voda/?ll=14.410998%2C50.233418&mode=poi&poi%5Bpoint%5D=14.350992%2C50.219835&poi%5Buri%5D=ymapsbm1%3A%2F%2Forg%3Foid%3D152307869062&z=13"
    },
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
        # initial_uid = ''.join(random.choices(string.digits, k=19))
        # initial_gid = ''.join(random.choices(string.digits, k=5))
        # self.client_session.cookie_jar.update_cookies({
        #     "yandexuid": initial_uid,
        #     "yuidss": initial_uid,
        #     "_ym_uid": initial_uid,
        #     "yandex_gid": initial_gid,
        #     "is_gdpr": "1",
        # })

    async def close(self):
        await self.client_session.close()

    async def set_new_session(self):
        """Initialize new session to API."""
        async with self.client_session.get(
            'https://yandex.com', headers=self._config["headers"]
        ) as resp:
            self.client_session.cookie_jar.update_cookies(dict(resp.cookies))

        async with self.client_session.get(
            self._config["init_url"], headers=self._config["headers"]
        ) as resp:
            # domain = resp.url.host
            domain = 'yandex.com'
            reply = await resp.text()
            if 'captcha' in str(resp.real_url) or 'captcha-page' in reply:
                raise CaptchaError("Captcha required")

        print(reply)
        result = re.search(rf'"{CSRF_TOKEN_KEY}":"(\w+.\w+)"', reply)
        self._config[PARAMS][CSRF_TOKEN_KEY] = result.group(1)
        # print(dict(resp.cookies))
        # self._config["cookies"] = dict(resp.cookies)
        self._config["cookies"] = {
            "yandexuid": re.search(r'yandexuid=(\d+)', reply).group(1),
            # # "yuidss": initial_uid,
            # # "_ym_uid": initial_uid,
            # # "yandex_gid": initial_gid,
            # "yandex_login": "ivan.belokobylskiy",
            # "maps_los": "1",
            # # "is_gdpr": "1",
        }

        self._config['uri'] = f'https://{domain}/{RESOURCE_PATH}'
        self._config[PARAMS][SESSION_KEY] = re.search(
            rf'"{SESSION_KEY}":"(\d+.\d+)"', reply
        ).group(1)
        params = {}
        self._config[PARAMS][URI_KEY] = None  # init with none
        self._config[PARAMS][ID_KEY] = None

        for key in SCHEMA:  # according to the order
            params[key] = self._config[PARAMS][key]
        self._config[PARAMS] = params
        # raise RuntimeError()

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
            print(resp.cookies)
            print(list(self.client_session.cookie_jar))
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
            pprint(list(data.keys()))
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
