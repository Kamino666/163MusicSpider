# coding=UTF-8
"""
获取所有的榜单信息
"""
import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import logging

import requests
import retrying
import ujson

from src import sql
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


def save_toplist():
    # print("== 爬取数据参数 ==")

    # 爬取
    @retrying.retry(stop_max_attempt_number=settings.connect["max_retries"], wait_fixed=settings.connect["interval"])
    def get():
        return requests.get('http://music.163.com/api/toplist/', headers=headers, timeout=settings.connect["timeout"],
                            proxies=proxy.proxy)

    try:
        r = get()
    except Exception as e:  # 致命网络错误
        logger.critical("致命错误！网络连接失败", exc_info=True)
        return
    # 网页解析
    toplistJson = ujson.loads(r.content.decode())
    for toplist in toplistJson["list"]:
        toplist_id = toplist["id"]
        toplist_name = toplist["name"]
        toplist_subscribedCount = toplist["subscribedCount"]
        try:  # sql 报错try
            sql.conn_lock.acquire()
            sql.insert_toplist(toplist_id, toplist_name, toplist_subscribedCount)
        except Exception as e:
            # 打印错误日志
            logger.debug("sql ERROR:" + str(e))
        finally:
            sql.conn_lock.release()


def toplistSpider():
    logger.info("======= 开始爬 榜单 信息 =======")
    startTime = datetime.datetime.now()

    logger.info("榜单正在{}线程爬取".format(settings.thread["toplists"]))
    # 构建线程池
    pool = ThreadPoolExecutor(max_workers=settings.thread["toplists"])
    pool.submit(save_toplist)
    pool.shutdown()

    endTime = datetime.datetime.now()
    logger.info("======= 结束爬 榜单 信息 =======")
    logger.info("榜单爬取耗时：" + str((endTime - startTime).seconds) + "秒")

# if __name__ == '__main__':
#     toplistSpider()
