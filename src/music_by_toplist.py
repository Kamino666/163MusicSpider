"""
根据榜单 ID 获取到所有的音乐 ID
"""
import datetime
import ujson
import math
import random
import time
import traceback
from concurrent.futures.process import ProcessPoolExecutor

import requests
import retrying

from src import sql
from src.util.user_agents import agents
from src.util import proxy
from src.util import settings


class Music(object):
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

    # 调用网易云api爬取
    def save_music_by_api(self, toplist_id):
        url = "http://music.163.com/api/playlist/detail?id=" + str(toplist_id)
        # 访问
        agent = random.choice(agents)
        self.headers["User-Agent"] = agent

        @retrying.retry(stop_max_attempt_number=settings.connect["max_retries"],
                        wait_fixed=settings.connect["interval"])
        def get():
            return requests.get(url, headers=self.headers, proxies=proxy.proxy)

        try:
            r = get()
        except Exception as e:
            print("代理连接失败", e)
            return
        # r = requests.get(url, headers=self.headers)
        # 解析
        toplist_json = ujson.loads(r.text)
        # 保存redis去重缓存
        if toplist_json['code'] == 200:
            # redis_util.saveUrl(redis_util.musicPrefix, str(toplist_id))
            pass
        else:
            print(url, " request error :", toplist_json)
            return
        for item in toplist_json['result']['tracks']:
            music_id = item['id']
            music_name = item['name']
            album_id = item['album']['id']
            try:
                sql.conn_lock.acquire()
                sql.insert_music(music_id, music_name, album_id)
            except Exception as e:
                # 打印错误日志
                print(music_id, music_name, toplist_id, ' insert db error: ', str(e))
                # traceback.print_exc()
                # time.sleep(1)
            finally:
                sql.conn_lock.release()


def saveMusicByToplist():
    my_music = Music()
    try:
        sql.conn_lock.acquire()
        toplists = sql.get_toplists()  # 获取所有榜单信息
    finally:
        sql.conn_lock.release()
    print("total:", len(toplists), "toplists", "start")
    for i in toplists:
        try:
            # 调用网易云api爬取
            my_music.save_music_by_api(i['toplist_id'])
            # 采用模仿网易云页面请求的方式爬取
            # my_music.save_music(i['toplist_id'])
            time.sleep(2)
        except Exception as e:
            # 打印错误日志
            print(str(i) + ' interval error: ' + str(e))
            time.sleep(2)
    print("total:", len(toplists), "toplists", "finished")


def musicSpider():
    print("======= 开始爬 音乐 信息 ===========")
    startTime = datetime.datetime.now()
    print(startTime.strftime('%Y-%m-%d %H:%M:%S'))
    # 所有榜单数量
    try:
        sql.conn_lock.acquire()
        toplists_num = sql.get_toplists_num()
    finally:
        sql.conn_lock.release()
    print("所有榜单数量：", toplists_num)
    saveMusicByToplist()
    print("======= 结束爬 音乐 信息 ===========")
    endTime = datetime.datetime.now()
    print(endTime.strftime('%Y-%m-%d %H:%M:%S'))
    print("耗时：", (endTime - startTime).seconds, "秒")

# if __name__ == '__main__':
#     musicSpider()
