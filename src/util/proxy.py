import requests
from threading import Lock
import os

import ujson

proxyLock = Lock()
proxy = {}


def getFromWeb():
    """
    在此函数写下关于你的代理供应商的API
    :return: {protocol:ip:port}
    """
    path = os.path.join(os.path.abspath("."), os.pardir, os.pardir, "conf", "proxy.cfg")
    with open(path, 'r') as f:
        url = f.readline()
        r = requests.get(url)
        pJson = ujson.loads(r.text)
        if pJson['ERRORCODE'] != "0":
            raise Exception("获取代理失败" + pJson['ERRORCODE'])
        pInfo = {'http': pJson["RESULT"][0]["ip"] + ":" + pJson["RESULT"][0]["port"],
                 'https': pJson["RESULT"][0]["ip"] + ":" + pJson["RESULT"][0]["port"], }
        return pInfo


# 通过 http://icanhazip.com/ https://icanhazip.com/ 来验证
def testProxy():
    rslt = [True, True]
    # http检测
    try:
        http = requests.get("http://icanhazip.com/", timeout=2, proxies=proxy)
        http.raise_for_status()
        if http.text.replace("\n", "") != proxy['http'].split(":")[0]:
            rslt[0] = False
    except requests.HTTPError as e:
        print("返回码错误", e)
        rslt[0] = False
    except requests.ConnectTimeout:
        print("连接超时")
        rslt[0] = False
    except requests.ConnectionError as e:
        print("连接错误", e)
        rslt[0] = False
    # https检测
    try:
        https = requests.get("https://icanhazip.com/", timeout=2, proxies=proxy)
        https.raise_for_status()
        if https.text.replace("\n", "") != proxy['https'].split(":")[0]:
            rslt[1] = False
    except requests.HTTPError as e:
        print("返回码错误", e)
        rslt[1] = False
    except requests.ConnectTimeout:
        print("连接超时")
        rslt[1] = False
    except requests.ConnectionError as e:
        print("连接错误", e)
        rslt[1] = False

    return rslt


def changeProxy():
    global proxy
    newproxy = getFromWeb()
    proxy = newproxy


if __name__ == "__main__":
    changeProxy()
    # proxy = {'http':"123.163.132.204:30402",'https':"123.163.132.204:30402"}  # 测试代理
    print(proxy)
    print(testProxy())
