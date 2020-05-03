# coding=UTF-8
"""
根据歌单 ID 获取到所有的音乐 ID
"""
import datetime
import json
import math
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
import logging

import requests
from bs4 import BeautifulSoup
import retrying

from src import sql
from src.util.user_agents import agents
from src.util import proxy
from src.util import settings

logger = logging.getLogger('MusicSpider')

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

    # TODO(Kamino): 改进歌曲数据库，来源不再只能是专辑
    # 调用网易云api爬取 歌单所有歌曲
    def save_music_by_api(self, playlist_id):
        url = "http://music.163.com/api/playlist/detail?id=" + str(playlist_id)
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
            logger.critical("代理连接失败" + str(e))
            return
        # r = requests.get(url, headers=self.headers)
        # 解析
        playlist_json = json.loads(r.text)
        # 错误处理
        if playlist_json['code'] != 200:
            logger.error("{} request error :{}".format(url, playlist_json))
            return
        for item in playlist_json.get('result').get('tracks'):
            music_id = item['id']
            music_name = item['name']
            try:
                sql.conn_lock.acquire()
                sql.insert_music(music_id, music_name, playlist_id)
                # print("sql success a song")
            except Exception as e:
                # 打印错误日志
                logger.debug(' insert db error: ' + str(e))
                # traceback.print_exc()
                # time.sleep(1)
            finally:
                sql.conn_lock.release()


# 爬取一批歌单
def saveMusicBatch(index, batch_size):
    my_music = Music()
    try:
        sql.conn_lock.acquire()
        playlists = sql.get_playlist_page(index, batch_size)
    finally:
        sql.conn_lock.release()
    logger.info("index:{} batch_size:{} 开始".format(index, batch_size))
    for i in playlists:
        try:
            # 调用网易云api爬取
            my_music.save_music_by_api(i['playlist_id'])
            # 频率控制
            time.sleep(1)
        except Exception as e:
            # 打印错误日志
            logger.info(str(i) + ' interval error: ' + str(e))
            # 频率控制
            time.sleep(2)
    logger.info("index:{} batch_size:{} 结束".format(index, batch_size))


def musicSpider():
    logger.info("======= 开始爬 歌单音乐 信息 ===========")
    startTime = datetime.datetime.now()

    # 所有歌单数量
    playlists_num = sql.get_playlists_num()['num']
    logger.info("所有歌单数量：{}".format(playlists_num))
    # 分批
    playlist_batch_size = settings.batch["music_by_playlist"]
    batch_num = math.ceil(playlists_num / playlist_batch_size)
    future_list = []
    # 构建线程池
    pool = ThreadPoolExecutor(max_workers=settings.thread["music_by_playlist"])
    logger.info("正在{}线程爬取专辑".format(settings.thread["music_by_playlist"]))
    for i in range(batch_num):
        # saveMusicBatch(index)
        fut = pool.submit(saveMusicBatch, i * playlist_batch_size, playlist_batch_size)
        future_list.append(fut)
    for fut in future_list:
        fut.result()
    pool.shutdown()

    endTime = datetime.datetime.now()
    logger.info("======= 结束爬 音乐 信息 ===========")
    logger.info("耗时：{}秒".format((endTime - startTime).seconds))

# if __name__ == '__main__':
#     musicSpider()
