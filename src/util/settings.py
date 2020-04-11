import ujson
import os

path = os.path.join(os.path.abspath("."), os.pardir, os.pardir, "conf", "settings.json")
_SETTINGS = ujson.load(open(path))
thread = _SETTINGS["thread"]
batch = _SETTINGS["batch"]
MySQL = _SETTINGS["MySQL"]
proxy = _SETTINGS["proxy"]
comments = _SETTINGS["comments"]
connect = _SETTINGS["connect"]

# print(_SETTINGS)
