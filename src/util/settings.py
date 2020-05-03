# coding=UTF-8
import ujson
import os

path = os.path.join(os.path.abspath("."), "conf", "settings.json")  # , os.pardir
_SETTINGS = ujson.load(open(path))
thread = _SETTINGS["thread"]
batch = _SETTINGS["batch"]
MySQL = _SETTINGS["MySQL"]
proxy = _SETTINGS["proxy"]
comments = _SETTINGS["comments"]
connect = _SETTINGS["connect"]

# print(_SETTINGS)
