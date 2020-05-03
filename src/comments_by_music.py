"""
根据歌曲 ID 获得所有的歌曲所对应的热门评论和歌词
"""
import datetime
import json
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor
import logging

import requests
import retrying

from src import sql
from src.util.user_agents import agents
from src.util import proxy
from src.util import settings

logger = logging.getLogger('MusicSpider')


class Comment(object):
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
    commentsCount = 0

    # 保存一首歌的评论，返回获取到的数量
    def saveComment(self, music_id):
        self.commentsCount = 0  # 归零
        params = {'limit': 100, 'offset': 0}
        # 获取歌手个人主页
        agent = random.choice(agents)
        self.headers["User-Agent"] = agent
        url = 'http://music.163.com/api/v1/resource/comments/R_SO_4_' + str(music_id)

        # 访问
        @retrying.retry(stop_max_attempt_number=settings.connect["max_retries"],
                        wait_fixed=settings.connect["interval"])
        def get():
            return requests.get(url, headers=self.headers, params=params, proxies=proxy.proxy)

        try:
            r = get()
        except Exception as e:
            logger.critical("代理连接失败" + str(e))
            return

        # r = requests.get(url, headers=self.headers, params=params)
        # 结果解析
        commentsJson = json.loads(r.text)
        # 保存redis去重缓存 放弃
        if commentsJson['code'] == 200:
            # redis_util.saveUrl(redis_util.commentPrefix, str(music_id))
            pass
        else:
            logger.error("{} request error :{}".format(url, commentsJson))
            return 0
        # 热评
        for item in commentsJson['hotComments']:
            self.dbsave(item, music_id)
        # 顶评
        for item in commentsJson['topComments']:
            self.dbsave(item, music_id)
        # 普通评*100
        for item in commentsJson['comments']:
            self.dbsave(item, music_id)
        # 评论数
        total = commentsJson['total']

        def saveCommentSmallBatch(limit, offset):
            """
            :param limit: 一次获取的数量
            :param offset: 偏移
            :return:
            """

            # sb代表small batch
            # 请求
            @retrying.retry(stop_max_attempt_number=settings.connect["max_retries"],
                            wait_fixed=settings.connect["interval"])
            def get_sb():
                return requests.get(url, headers=self.headers, params={'limit': limit, 'offset': offset}
                                    , proxies=proxy.proxy)

            try:
                r_sb = get_sb()
            except Exception as e_sb:
                logger.critical("代理连接失败" + str(e_sb))
                return

            # r_sb = requests.get(url, headers=self.headers, params={'limit': limit, 'offset': offset})
            # 结果解析
            commentsJson_sb = json.loads(r_sb.text)
            # 普通评论
            for item_sb in commentsJson_sb['comments']:
                self.dbsave(item_sb, music_id)

        # 根据获取到的评论数分批访问
        full = 0  # 访问100个的次数
        leftover = 0  # 最后一次访问的评论数
        if total <= 0:
            raise Exception("未知错误，获取评论数量失败")
        elif total <= 100:  # 评论数小于100时
            return self.commentsCount
        elif total >= settings.comments["max_comment_num_of_a_music"]:  # 评论数大于最大获取数时
            full = settings.comments["max_comment_num_of_a_music"] // 100 - 1
        else:  # 评论数位于100和max之间
            full = (total - 100) // 100
            leftover = (total - 100) % 100
        time.sleep(1)  # 第一次访问后暂停1秒
        # 访问 先访问完full，再访问一次leftover
        for i in range(full):
            # print("访问sb中",i)
            saveCommentSmallBatch(100, (i + 1) * 100)
            time.sleep(1)  # 每次访问暂停1秒
        saveCommentSmallBatch(leftover, full * 100)
        return self.commentsCount

    # 保存数据库
    def dbsave(self, item, music_id):
        user = item['user']
        # 用户id
        userId = user['userId']
        nickname = user['nickname']
        # 用户头像
        userImg = user['avatarUrl']
        # 评论内容
        content = item['content']
        # 点赞数
        likedCount = item['likedCount']
        # 时间
        remarkTime = item['time']
        # 评论id
        commentId = item['commentId']
        try:
            # 持久化
            sql.conn_lock.acquire()
            sql.insert_comment(commentId, music_id, content, likedCount, remarkTime, userId, nickname, userImg)
            self.commentsCount += 1
        except Exception as e:
            # 打印错误日志
            logger.debug('insert error : ' + str(e))
            # time.sleep(1)
        finally:
            sql.conn_lock.release()


def saveCommentBatch(index, batch_size):
    my_comment = Comment()
    allValidNum = 0
    try:
        sql.conn_lock.acquire()
        musics = sql.get_music_page(index, batch_size)
    finally:
        sql.conn_lock.release()
    logger.info("index:{} batch_size:{} 开始".format(index, batch_size))
    for item in musics:
        try:
            validNum = my_comment.saveComment(item['music_id'])
            allValidNum += validNum
            # 频率控制
            time.sleep(2)
        except Exception as e:
            # 打印错误日志
            logger.error(' internal  error : ' + str(e))
            # 频率控制
            time.sleep(3)
    logger.info("index:{} batch_size:{} 结束，共获取有效评论{}条".format(index, batch_size, allValidNum))


def commentSpider():
    logger.info("======= 开始爬 评论 信息 ===========")
    startTime = datetime.datetime.now()

    # 所有歌曲数量
    try:
        sql.conn_lock.acquire()
        musics_num = sql.get_all_music_num()['num']
    finally:
        sql.conn_lock.release()
    # 分批
    music_batch_size = settings.batch["comments_by_music"]
    batch_num = math.ceil(musics_num / music_batch_size)
    future_list = []
    # 构建线程池
    pool = ThreadPoolExecutor(max_workers=settings.thread["comments_by_music"])
    logger.info("正在{}线程爬取评论".format(settings.thread["comments_by_music"]))
    for i in range(batch_num):
        # saveMusicBatch(index)
        fut = pool.submit(saveCommentBatch, i * music_batch_size, music_batch_size)
        future_list.append(fut)
    for fut in future_list:
        fut.result()
    pool.shutdown()

    endTime = datetime.datetime.now()
    logger.info("======= 结束爬 评论 信息 ===========")
    logger.info("耗时：{}秒".format((endTime - startTime).seconds))

# if __name__ == '__main__':
#     commentSpider()
