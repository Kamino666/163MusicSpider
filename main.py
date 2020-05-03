import datetime
import sys
import os
import logging
import time

logger = logging.getLogger('MusicSpider')


def init_logger():
    # 初始化logger
    time_str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    logger.setLevel(logging.DEBUG)  # Log等级总开关
    debug_filter = logging.Filter()
    debug_filter.filter = lambda record: record.levelno > logging.DEBUG  # 设置过滤等级
    formatter = logging.Formatter('[%(levelname)s]%(asctime)s - %(threadName)s:%(funcName)s ->> %(message)s')
    # 详细日志文件输出
    detail_handler = logging.FileHandler(os.path.join(os.path.abspath("."), "logs", "DETAIL" + time_str + ".log"))
    detail_handler.setLevel(logging.NOTSET)
    detail_handler.setFormatter(formatter)
    # 简明日志文件输出
    simple_handler = logging.FileHandler(os.path.join(os.path.abspath("."), "logs", "SIMPLE" + time_str + ".log"))
    simple_handler.setFormatter(formatter)
    simple_handler.addFilter(debug_filter)
    # 简明日志控制台输出
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(debug_filter)

    logger.addHandler(detail_handler)
    logger.addHandler(simple_handler)
    logger.addHandler(console)


# if __name__ == '__main__':
#     init_logger()
#     logger.debug("debug")
#     logger.info("info")
#     logger.error("error")
#     logger.warning("warning")
#     logger.critical("critical")
#     pass
pass
# if __name__ == '__main__':
#     path = os.path.abspath(os.path.dirname(__file__))
#     type = sys.getfilesystemencoding()
#     print("开始爬干净网易云音乐")
#     startTime = datetime.datetime.now()
#     print(startTime.strftime('%Y-%m-%d %H:%M:%S'))
#     # 清空数据库
#     sql.truncate_all()
#     print("清空数据库完成")
#     # 开始执行
#     artistSpider()
#     albumSpider()
#     musicSpider()
#     lyricSpider()
#     commentSpider()
#     endTime = datetime.datetime.now()
#     print(endTime.strftime('%Y-%m-%d %H:%M:%S'))
#     print("耗时：", (endTime - startTime).seconds, "秒")

if __name__ == '__main__':
    init_logger()
    try:
        # from src import sql
        # from src.album_by_artist import albumSpider
        # from src.artists import artistSpider
        # from src.comments_by_music import commentSpider
        # from src.lyric_by_music import lyricSpider
        # from src.music_by_album import musicSpider
        from src.playlists import playlistSpider
    except Exception:
        print("初始化错误")
        pass
    playlistSpider()
