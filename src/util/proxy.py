import requests
from threading import Thread
import os
import time

import ujson

proxy = {}
VALID_PROXY = [True, True]
VALID_HTTP_ONLY_PROXY = [True, False]
VALID_HTTPS_ONLY_PROXY = [False, True]


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
        return pInfo


# 本地文件API
def getFromFile():
    pass


# 通过 http://icanhazip.com/ https://icanhazip.com/ 来验证
def testProxy(timeout=6):
    rslt = [True, True]
    # http检测
    try:
        http = requests.get("http://icanhazip.com/", timeout=timeout, proxies=proxy)
        http.raise_for_status()
        if http.text.replace("\n", "") != proxy['http'].split(":")[0]:
            rslt[0] = False
    except requests.HTTPError as e:
        print("返回码错误", e)
        rslt[0] = False
    except requests.exceptions.ReadTimeout:
        print("连接超时")
        rslt[0] = False
    except requests.ConnectionError as e:
        print("连接错误", e)
        rslt[0] = False
    except Exception as e:
        print("未知错误", e)
        rslt[0] = False
    # https检测
    try:
        https = requests.get("https://icanhazip.com/", timeout=timeout, proxies=proxy)
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
    except Exception as e:
        print("未知错误", e)
        rslt[1] = False

    return rslt


# 一定时间内检查一次代理是否出错。假如出错则替换
def proxy_detector():
    while True:
        print("检测中")
        if testProxy(10) != VALID_PROXY:
            print("检测到代理失效")
            changeProxy()
        time.sleep(10)


def changeProxy():
    print("获取新代理中")
    global proxy
    newproxy = getFromWeb()
    print("代理更换完毕{}-->{}".format(proxy, newproxy))
    proxy = newproxy


if len(proxy) == 0:
    print("初始化代理")
    changeProxy()
    if testProxy() == [True, True]:
        print("初始化代理有效:", str(proxy))
    print("初始化代理检测器")
    detector = Thread(target=proxy_detector)
    detector.start()

# if __name__ == "__main__":
#     changeProxy()
#     # proxy = {'http':"123.163.132.204:30402",'https':"123.163.132.204:30402"}  # 测试代理
#     print(proxy)
#     print(testProxy())
