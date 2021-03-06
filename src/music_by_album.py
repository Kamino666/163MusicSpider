# coding=UTF-8
"""
根据专辑 ID 获取到所有的音乐 ID
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

    # 调用网易云api爬取
    def save_music_by_api(self, album_id):
        url = "http://music.163.com/api/album/" + str(album_id)

        # 访问
        agent = random.choice(agents)
        self.headers["User-Agent"] = agent

        @retrying.retry(stop_max_attempt_number=settings.connect["max_retries"],
                        wait_fixed=settings.connect["interval"])
        def get():
            return requests.get(url, headers=self.headers, proxies=proxy.proxy, timeout=settings.connect["timeout"])

        try:
            r = get()
        except Exception as e:
            logger.critical("代理连接失败" + str(e))
            return
        # r = requests.get(url, headers=self.headers)
        # 解析
        album_json = json.loads(r.text)
        # 保存redis去重缓存 放弃
        if album_json['code'] == 200:
            # redis_util.saveUrl(redis_util.albumPrefix, str(album_id))
            pass
        else:
            logger.error("{} api请求错误: {}".format(url, album_json))
            return
        for item in album_json.get('album').get('songs'):
            music_id = item['id']
            music_name = item['name']
            try:
                sql.conn_lock.acquire()
                sql.insert_music(music_id, music_name, album_id)
            except Exception as e:
                # 打印错误日志
                logger.debug(' insert db error: ' + str(e))
                # traceback.print_exc()
                # time.sleep(1)
            finally:
                sql.conn_lock.release()


def saveMusicBatch(index, batch_size):
    logger.info("index: {} batchsize:{} 开始".format(index, batch_size))
    my_music = Music()
    try:
        sql.conn_lock.acquire()
        albums = sql.get_album_page(index, batch_size)
    finally:
        sql.conn_lock.release()
    for i in albums:
        try:
            # 调用网易云api爬取
            my_music.save_music_by_api(i['album_id'])
            # 频率控制
            time.sleep(1)
        except Exception as e:
            # 打印错误日志
            logger.error(str(i) + ' interval error: ' + str(e))
            # 频率控制
            time.sleep(2)
    logger.info("index: {} batchsize:{} 结束".format(index, batch_size))


def musicSpider():
    logger.info("======= 开始爬 音乐 信息 ===========")
    startTime = datetime.datetime.now()

    # 所有专辑数量
    try:
        sql.conn_lock.acquire()
        albums_num = sql.get_all_album_num().get('num')
    finally:
        sql.conn_lock.release()
    logger.info("所有专辑数量：{}".format(albums_num))
    # 分批
    album_batch_size = settings.batch["music_by_album"]
    batch_num = math.ceil(albums_num / album_batch_size)
    future_list = []
    # 构建线程池
    pool = ThreadPoolExecutor(max_workers=settings.thread["music_by_album"])
    logger.info("正在{}线程爬取专辑".format(settings.thread["music_by_album"]))
    for i in range(batch_num):
        # saveMusicBatch(index)
        fut = pool.submit(saveMusicBatch, i * album_batch_size, album_batch_size)
        future_list.append(fut)
        time.sleep(1)  # debug
    for fut in future_list:
        fut.result()
    pool.shutdown()

    endTime = datetime.datetime.now()
    logger.info("======= 结束爬 音乐 信息 ===========")
    logger.info("耗时：{} 秒".format((endTime - startTime).seconds))

# if __name__ == '__main__':
#     musicSpider()
