``aioymaps`` is an asynchronous library provides API to fetch json information
about transport stops from Yandex Maps


Requirements
============
``aioymaps`` requires python 3.5 or higher due to async/await syntax and aiohttp
library


Installation
============

Use pip to install the library:
::

    pip install aioymaps

Or install manually.
::

    sudo python ./setup.py install


Usage
=====
::

    from aioymaps import YandexMapsRequester

    requester = YandexMapsRequester()
    data = await requester.get_stop_info(10067199)
    print(data)


Or you can use it in your shell:
::

    python -m aioymaps -s 10067199

