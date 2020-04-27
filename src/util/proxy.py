import requests
from threading import Thread
import os
import time

import ujson

from src.util import settings

proxy = {}
# VALID_PROXY = [True, True]
# VALID_HTTP_ONLY_PROXY = [True, False]
# VALID_HTTPS_ONLY_PROXY = [False, True]


# 读入本地代理文件
local_path = os.path.join(os.path.abspath("."), os.pardir, "conf", "proxies.json")
with open(local_path) as json_fptr:
    local_proxies = ujson.loads(json_fptr.read())
local_proxies_count = 0  # 本地代理计数
# 全局代理计数
proxy_count = 0
# 全局有效代理计数
valid_proxy_count = 0


# 网络API获得代理
def getFromWeb():
    """
    在此函数写下关于你的代理供应商的API
    :return: {protocol:ip:port}
    """
    path = os.path.join(os.path.abspath("."), os.pardir, "conf", "proxyAPI.cfg")
    with open(path, 'r') as f:
        url = f.readline()
        r = requests.get(url)
        pJson = ujson.loads(r.text)
        if pJson['ERRORCODE'] != "0":
            raise Exception("获取代理失败" + pJson['ERRORCODE'])
        pInfo = {'http': pJson["RESULT"][0]["ip"] + ":" + pJson["RESULT"][0]["port"],
                 'https': pJson["RESULT"][0]["ip"] + ":" + pJson["RESULT"][0]["port"], }
        # {'http':'x.x.x.x:y','https':'x.x.x.x:y'}
        print("从网络获取一个代理")
        # 总代理数+1
        global proxy_count
        proxy_count += 1
        return pInfo


# 本地文件API
def getFromFile():
    global local_proxies_count  # 本地代理数+1
    local_proxies_count += 1
    global local_proxies
    global proxy_count  # 总代理数+1
    proxy_count += 1
    return local_proxies["info"][local_proxies_count - 1]


# 通过 http://icanhazip.com/ https://icanhazip.com/ 来验证
# def testProxy(timeout=6):
#     rslt = [True, True]
#     # http检测
#     try:
#         http = requests.get("http://icanhazip.com/", timeout=timeout, proxies=proxy)
#         http.raise_for_status()
#         if http.text.replace("\n", "") != proxy['http'].split(":")[0]:
#             rslt[0] = False
#     except requests.HTTPError as e:
#         print("检测返回码错误", e)
#         rslt[0] = False
#     except requests.exceptions.ReadTimeout:
#         print("检测连接超时")
#         rslt[0] = False
#     except requests.ConnectionError as e:
#         print("检测连接错误", e)
#         rslt[0] = False
#     except Exception as e:
#         print("检测未知错误", e)
#         rslt[0] = False
#     # https检测
#     try:
#         https = requests.get("https://icanhazip.com/", timeout=timeout, proxies=proxy)
#         https.raise_for_status()
#         if https.text.replace("\n", "") != proxy['https'].split(":")[0]:
#             rslt[1] = False
#     except requests.HTTPError as e:
#         print("检测返回码错误", e)
#         rslt[1] = False
#     except requests.ConnectTimeout as e:
#         print("检测连接超时")
#         rslt[1] = False
#     except requests.ConnectionError as e:
#         print("检测连接错误", e)
#         rslt[1] = False
#     except Exception as e:
#         print("检测未知错误", e)
#         rslt[1] = False
#
#     return rslt


# 直接访问目标网站来验证代理有效性 "https://music.163.com/#" 仅检测https
def test_proxy(p=None):
    """
    :param p: 要测试的代理，默认为当前使用代理
    :return: 代理有效性
    """
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        # 获取数据多了之后，就会被禁用访问,可以使用代理
        'Cookie': 'MUSIC_U=f8b73ab123ddad32d44c37546522e06bb123363f4b813922a1902f2ds2ceb750c52sd32ccbb1ab2b9c23asd3a31522c7067cce3c7469;',
        'DNT': '1',
        'Host': 'music.163.com',
        'Pragma': 'no-cache',
        'Referer': 'http://music.163.com/album?id=71537',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
    }
    if p is None and proxy is None:  # 假如未指定测试代理且当前代理为空
        print("检测代理有效性时发现未设置代理")
        return False
    if p is None:  # 假如未指定测试代理
        p = proxy
    try:
        r = requests.get("https://music.163.com/discover/toplist", headers=headers, proxies=p)
        print("检测{}代理有效".format(p))
        return True
    except Exception:
        print("检测{}代理失效".format(p))
        return False


# 一定时间内检查一次代理是否出错。假如出错则替换
def proxy_detector():
    while True:
        print("检测代理中")
        if test_proxy() is False:
            # print("检测到代理失效")
            change_proxy()
        time.sleep(5)


# def changeProxy():
#     print("获取新代理中")
#     global proxy
#     if settings.proxy["mode"] == "web":
#         newproxy = getFromWeb()
#     elif settings.proxy["mode"] == "file":
#         newproxy = getFromFile()
#     else:
#         newproxy = None
#     print("代理更换完毕{}-->{}".format(proxy, newproxy))
#     proxy = newproxy


# 更换一个有效的代理
def change_proxy():
    """
    负责将全局代理更换成一个有效的
    :return:
    """
    print("更换代理中")
    global proxy
    newproxy = None
    while True:
        if settings.proxy["mode"] == "web":
            newproxy = getFromWeb()
        elif settings.proxy["mode"] == "file":
            newproxy = getFromFile()

        if test_proxy(newproxy) is True:
            global valid_proxy_count
            valid_proxy_count += 1
            break
        else:
            print("获取代理无效，重新获取代理")
    print("代理更换完毕{}-->{}".format(proxy, newproxy))
    proxy = newproxy


if settings.proxy["activate"]:
    print("开启使用代理模式")
    if settings.proxy["mode"] == "web":
        print("代理获取源为网络")
    elif settings.proxy["mode"] == "file":
        print("代理获取源为本地json文件")
    # 如果当前代理为空
    if len(proxy) == 0:
        print("初始化代理中")
        change_proxy()
        print("启动代理检测器")
        detector = Thread(target=proxy_detector)
        detector.start()
else:
    print("开启不使用代理模式")

# if __name__ == "__main__":
#     changeProxy()
#     # proxy = {'http':"123.163.132.204:30402",'https':"123.163.132.204:30402"}  # 测试代理
#     print(proxy)
#     print(testProxy())
