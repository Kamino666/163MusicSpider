# coding=UTF-8
"""
根据上一步获取的歌手的 ID 来用于获取所有的专辑 ID
"""
import datetime
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup
import retrying
import logging

from src import sql
from src.util.user_agents import agents
from src.util import proxy
from src.util import settings

logger = logging.getLogger('MusicSpider')

class Album(object):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Cookie': '_ntes_nnid=7eced19b27ffae35dad3f8f2bf5885cd,1476521011210; _ntes_nuid=7eced19b27ffae35dad3f8f2bf5885cd; usertrack=c+5+hlgB7TgnsAmACnXtAg==; Province=025; City=025; _ga=GA1.2.1405085820.1476521280; NTES_PASSPORT=6n9ihXhbWKPi8yAqG.i2kETSCRa.ug06Txh8EMrrRsliVQXFV_orx5HffqhQjuGHkNQrLOIRLLotGohL9s10wcYSPiQfI2wiPacKlJ3nYAXgM; P_INFO=hourui93@163.com|1476523293|1|study|11&12|jis&1476511733&mail163#jis&320100#10#0#0|151889&0|g37_client_check&mailsettings&mail163&study&blog|hourui93@163.com; JSESSIONID-WYYY=189f31767098c3bd9d03d9b968c065daf43cbd4c1596732e4dcb471beafe2bf0605b85e969f92600064a977e0b64a24f0af7894ca898b696bd58ad5f39c8fce821ec2f81f826ea967215de4d10469e9bd672e75d25f116a9d309d360582a79620b250625859bc039161c78ab125a1e9bf5d291f6d4e4da30574ccd6bbab70b710e3f358f%3A1476594130342; _iuqxldmzr_=25; __utma=94650624.1038096298.1476521011.1476588849.1476592408.6; __utmb=94650624.11.10.1476592408; __utmc=94650624; __utmz=94650624.1476521011.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
        'DNT': '1',
        'Host': 'music.163.com',
        'Pragma': 'no-cache',
        'Referer': 'http://music.163.com/',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
    }

    def saveAlbums(self, artist_id):
        # limit 分页，截止2019-08-26，发现专辑数大于1000的歌手
        params = {'id': artist_id, 'limit': '9999'}
        logger.info("爬取歌手专辑参数:{}".format(str(params)))
        # 获取歌手个人主页
        agent = random.choice(agents)
        self.headers["User-Agent"] = agent
        url = 'http://music.163.com/artist/album?id=' + str(artist_id)

        # 访问
        @retrying.retry(stop_max_attempt_number=settings.connect["max_retries"],
                        wait_fixed=settings.connect["interval"])
        def get():
            return requests.get('http://music.163.com/artist/album', headers=self.headers, params=params
                                , proxies=proxy.proxy, timeout=settings.connect["timeout"])

        try:
            r = get()
        except Exception as e:
            logger.critical("代理连接失败", exc_info=True)
            return

        # r = requests.get('http://music.163.com/artist/album', headers=self.headers, params=params)
        # 网页解析
        soup = BeautifulSoup(r.content.decode(), 'html.parser')
        # 所有图片
        imgs = soup.find_all('div', attrs={'class': 'u-cover u-cover-alb3'})
        # 专辑信息
        albums = soup.find_all('a', attrs={'class': 'tit s-fc0'})  # 获取所有专辑
        if len(albums) == 0:
            return
        for index, album in enumerate(albums):
            # 专辑id
            album_id = album['href'].replace('/album?id=', '')
            # 专辑图片地址
            img_url = imgs[index].img.get('src').replace('?param=120y120', '')
            try:
                sql.conn_lock.acquire()
                sql.insert_album(album_id, artist_id, imgs[index].get('title'), img_url)
            except Exception as e:
                # 打印错误日志
                logger.debug(str(album) + ' insert error : ' + str(e))
            finally:
                sql.conn_lock.release()


def saveAlbumBatch(index, batch_size):
    my_album = Album()
    try:  # 获取数据库锁
        sql.conn_lock.acquire()
        artists = sql.get_artist_page(index, batch_size)
    finally:
        sql.conn_lock.release()
    logger.info("index:{} batch_size:{} 开始".format(index, batch_size))
    for i in artists:
        try:
            my_album.saveAlbums(i['artist_id'])
            # 频率控制
            time.sleep(1)
        except Exception as e:
            # 打印错误日志
            logger.error(str(i) + ' internal  error : ' + str(e))
            # 频率控制
            time.sleep(2)
    logger.info("index:{} batch_size:{} 结束".format(index, batch_size))


def albumSpider():
    logger.info("======= 开始爬 专辑 信息 ===========")
    startTime = datetime.datetime.now()

    # 所有歌手数量
    artists_num = sql.get_all_artist_num()
    # batch = math.ceil(artists_num.get('num') / 1000.0)
    # 分批
    artist_batch_size = settings.batch["album_by_artist"]
    batch_num = math.ceil(artists_num.get('num') / artist_batch_size)
    future_list = []
    # 构建线程池
    pool = ThreadPoolExecutor(max_workers=settings.thread["album_by_artist"])
    logger.info("正在{}线程爬取专辑".format(settings.thread["album_by_artist"]))
    for i in range(batch_num):
        # saveAlbumBatch(i*playlist_batch_size, playlist_batch_size)
        fut = pool.submit(saveAlbumBatch, i * artist_batch_size, artist_batch_size)
        future_list.append(fut)
    for fut in future_list:
        fut.result()
    pool.shutdown()

    endTime = datetime.datetime.now()
    logger.info("======= 结束爬 专辑 信息 ===========")
    logger.info("耗时：{}秒".format((endTime - startTime).seconds))

# if __name__ == '__main__':
#     albumSpider()
