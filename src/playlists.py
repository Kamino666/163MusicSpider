# coding=UTF-8
"""
获取所有的歌单信息
"""
import datetime
import random
import time
from concurrent.futures import ThreadPoolExecutor
import threading
import math
import logging

import requests
from bs4 import BeautifulSoup
import retrying

from src import sql
from src.util import user_agents
from src.util import proxy
from src.util import settings

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Cookie': '_ntes_nnid=8400bf2c060bc31cf9594e45f27a3fec,1563176153301; _ntes_nuid=8400bf2c060bc31cf9594e45f27a3fec; mail_psc_fingerprint=3bb841d2e82c66a598e20c722a2bc7e6; _ga=GA1.2.1695844012.1563176156; hb_MA-BFF5-63705950A31C_source=www.baidu.com; vinfo_n_f_l_n3=83751e6d9da80baf.1.0.1565690525602.0.1565937929199; JSESSIONID-WYYY=G9GF8EdTBb4vKhW07sJl%2FzJ1SngYTglBRTjO7pWuQZWjmsrUoRtEe2oeB7UtNmUsBb%2FeQI3TUZOi9nMwMrvCRkuvXnto7BSelMqYKpBkcb8o2XwvYtH0WfechA2y6lehTIxYrSDXu6mY%5CRxDbsqTXGaKCPDzQsyo2l%2B26c4w3MB0WwJ7%3A1566543736167; _iuqxldmzr_=32; WM_NI=OoTiNDHx4qjSbYmG1PqXdQwej8FpE8h7U6NpcM3jHZDCQ6aI8rzlAViZue3Y9BfwmA7KveDdl0cNeAVoAYihzax6fSnCEvmHwaSDyUKE5YEOpbfQFz4guPGT%2F7J8cWqCR1o%3D; WM_NIKE=9ca17ae2e6ffcda170e2e6eeb6b843b7b5bc8bb663a2928ea2d54e929b9aaab7339af5a6a4e55db6f0a399ec2af0fea7c3b92a8db19c8acd508ca8fc92e959a287a3a8b45cb388acb2f66faae88a91c834ace99bd7cd7ca193fd8bcb52889d9fd7e443fcaeb68dc45eab86bb86b253fb9eaa98f04bf595ba86c770b0f0adafe84b96b18fbaec64babfb8d7e559ae9d8b97f044b5bf9da5fc5f899bfbbac845b4beaab2c572f8b9bbb1c660ede986d9e25db39d9ed2ee37e2a3; WM_TID=lKkihvPjbwBAUFVEBQZ45Y%2FzXbD7xygm',
    'DNT': '1',
    'Host': 'music.163.com',
    'Pragma': 'no-cache',
    'Referer': 'https://music.163.com/',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
}
logger = logging.getLogger('MusicSpider')


def save_playlist(cat_url):
    logger.info("爬取歌单url:{}".format(cat_url))
    offset = 0
    while offset < 1300:  # 备用出口
        weakCount = 0
        pageCount = 0
        # 访问
        params = None
        addparams = "&limit=" + "35" + "&offset=" + str(offset)
        url = "https://music.163.com" + cat_url + addparams

        @retrying.retry(stop_max_attempt_number=settings.connect["max_retries"],
                        wait_fixed=settings.connect["interval"])
        def get():
            return requests.get(url, headers=headers, params=params, proxies=proxy.proxy,
                                timeout=settings.connect["timeout"])

        try:
            r = get()
        except Exception as e:
            logger.critical("致命错误！网络连接失败", exc_info=True)
            return
        # logger.debug("爬取数据url:" + url)
        # 网页解析
        soup = BeautifulSoup(r.content.decode(), 'html.parser')
        playlists_apage = soup.find(attrs={"class": "m-cvrlst f-cb"})
        if playlists_apage is None:  # 爬到大概38页 出口1
            logger.info("风格歌单全部爬完")
            break
        else:
            offset += 35
        for playlist in playlists_apage.children:
            if playlist == "\n":  # 反爬？
                continue
            # 存储要上传sql的信息
            playlist_id = playlist.p.a.get("href").split("=")[1]  # id
            playlist_name = playlist.p.a.get("title")  # 名字
            playCount = playlist.find(attrs={"class": "nb"}).string.replace("万", "0000")  # 播放数
            img_url = playlist.div.img.get("src").replace('?param=140y140', '')  # 封面
            # 获取总歌单数和播放量极少的歌单数
            if int(playCount) < 10000:
                weakCount += 1
            pageCount += 1
            try:
                sql.conn_lock.acquire()  # 取得锁
                sql.insert_playlist(playlist_id, playlist_name, playCount, img_url)
                # print("sql success")
            except Exception as e:
                # 打印错误日志
                logger.debug(str(e))
            finally:
                sql.conn_lock.release()
        # 计算单页小于某一数值的歌单数量，若播放量少的歌单多，那就不爬下一页
        if weakCount / pageCount > 0.3:  # 出口2
            logger.warning("风格歌单爬取到热门页，停止")
            break
        # 频率控制
        time.sleep(1)


def save_playlist_batch(catTmpList):
    for i in catTmpList:
        save_playlist(i)


def save_cat():
    # 访问
    url = "https://music.163.com/discover/playlist"
    agent = random.choice(user_agents.agents)
    headers['User-Agent'] = agent

    @retrying.retry(stop_max_attempt_number=settings.connect["max_retries"], wait_fixed=settings.connect["interval"])
    def get():
        return requests.get(url, headers=headers, proxies=proxy.proxy, timeout=settings.connect["timeout"])

    try:
        r = get()
    except Exception as e:
        logger.critical("致命错误！网络连接失败", exc_info=True)
        raise Exception("save_cat中网络连接失败")
    # 解析
    soup = BeautifulSoup(r.content.decode(), 'html.parser')
    cats = soup.find_all('a', attrs={"class": "s-fc1"})
    for cat in cats:
        catList.append(cat.get("href"))
    # 频率控制
    time.sleep(1)


catList = []


def playlistSpider():
    logger.info("======= 开始爬 歌单 信息 =======")
    startTime = datetime.datetime.now()
    try:
        save_cat()
        logger.info("获取到{}个歌单分类".format(len(catList)))
        pool = ThreadPoolExecutor(max_workers=settings.thread["playlists"])
        logger.info("歌单正在{}线程爬取".format(settings.thread["playlists"]))
        # 分批
        playlist_batch_size = settings.batch["playlists"]
        batch_num = math.ceil(len(catList) / playlist_batch_size)
        logger.info("歌单爬取批次大小为{}".format(playlist_batch_size))
        future_list = []
        for i in range(batch_num):
            fut = pool.submit(save_playlist_batch
                              , catTmpList=catList[i * settings.batch["playlists"]:i * settings.batch["playlists"] +
                                                                                   settings.batch["playlists"]])
            future_list.append(fut)
        for fut in future_list:  # 等待结果
            fut.result()
        pool.shutdown()
    except Exception as e:  # 捕获save_cat的错误
        logger.critical(str(e))
    endTime = datetime.datetime.now()
    logger.info("======= 结束爬 歌单 信息 =======")
    logger.info("歌单爬取耗时：" + str((endTime - startTime).seconds) + "秒")

# if __name__ == '__main__':
#     playlistSpider()
# save_cat()
# save_playlist("/discover/playlist/?cat=%E5%8D%8E%E8%AF%AD")
