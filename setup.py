#!/usr/bin/env python

from setuptools import setup

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='aioymaps',
    version='1.2.3',
    description='Async client for Yandex Maps',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author='Ivan Belokobylskiy',
    author_email='belokobylskij@gmail.com',
    url='https://github.com/devbis/aioymaps/',
    py_modules=['aioymaps'],
    install_requires=['aiohttp>=3.0.0'],
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
    ],
)
