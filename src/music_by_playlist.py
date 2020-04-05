"""
根据歌单 ID 获取到所有的音乐 ID
"""
import datetime
import json
import math
import random
import time
import traceback
from concurrent.futures.process import ProcessPoolExecutor

import requests
from bs4 import BeautifulSoup

from src import sql, redis_util
from src.util.user_agents import agents


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
        r = requests.get(url, headers=self.headers)
        # 解析
        album_json = json.loads(r.text)
        # 错误处理
        if album_json['code'] != 200:
            print(url, " request error :", album_json)
            return
        for item in album_json.get('result').get('tracks'):
            music_id = item['id']
            music_name = item['name']
            try:
                sql.insert_music(music_id, music_name, playlist_id)
                print("sql success a song")
            except Exception as e:
                # 打印错误日志
                print(music_id, music_name, playlist_id, ' insert db error: ', str(e))
                # traceback.print_exc()
                # time.sleep(1)


# 爬取一批歌单 播放量高优先
def saveMusicBatch(index):
    my_music = Music()
    offset = 1000 * index
    playlists = sql.get_playlist_page(offset, 1000)
    print("index:", index, "offset:", offset, " playlists :", len(playlists), "start")
    for i in playlists:
        try:
            # 调用网易云api爬取
            my_music.save_music_by_api(i['playlist_id'])
            # 暂停
            time.sleep(1)
        except Exception as e:
            # 打印错误日志
            print(str(i) + ' interval error: ' + str(e))
            time.sleep(2)
    print("index:", index, "finished")


def musicSpider():
    print("======= 开始爬 歌单音乐 信息 ===========")
    startTime = datetime.datetime.now()
    print(startTime.strftime('%Y-%m-%d %H:%M:%S'))
    # 所有歌单数量
    playlists_num = sql.get_playlists_num()['num']
    print("所有歌单数量：", playlists_num)
    # 批次
    batch = math.ceil(playlists_num / 1000.0)
    # 构建线程池
    # pool = ProcessPoolExecutor(1)
    for index in range(0, batch):
        saveMusicBatch(index)
        # pool.submit(saveMusicBatch, index)
    # pool.shutdown(wait=True)
    print("======= 结束爬 音乐 信息 ===========")
    endTime = datetime.datetime.now()
    print(endTime.strftime('%Y-%m-%d %H:%M:%S'))
    print("耗时：", (endTime - startTime).seconds, "秒")

# if __name__ == '__main__':
#     musicSpider()