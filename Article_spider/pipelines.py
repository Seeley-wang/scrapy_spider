import codecs
import json
from scrapy.exceptions import DropItem
from scrapy.exporters import JsonItemExporter
from scrapy.pipelines.images import ImagesPipeline
from twisted.enterprise import adbapi  # mysqldb操作变成异步化
import codecs
import MySQLdb
import MySQLdb.cursors


class ArticlespiderPipeline(object):
    def process_item(self, item, spider):
        return item


# 异步操作mysql插入
class MysqlTwistedPipeline(object):
    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    # 自定义组件或扩展很有用的方法: 这个方法名字固定, 是会被scrapy调用的。
    # 这里传入的cls是指当前的MysqlTwistedPipline class
    def from_settings(cls, settings):
        # setting值可以当做字典来取值
        dbparms = dict(
            host=settings["MYSQL_HOST"],
            db=settings["MYSQL_DBNAME"],
            user=settings["MYSQL_USER"],
            passwd=settings["MYSQL_PASSWORD"],
            charset='utf8',
            cursorclass=MySQLdb.cursors.DictCursor,
            use_unicode=True,
        )
        # 连接池ConnectionPool
        # def __init__(self, dbapiName, *connargs, **connkw):
        dbpool = adbapi.ConnectionPool("MySQLdb", **dbparms)

        # 此处相当于实例化pipeline, 要在init中接收。
        return cls(dbpool)

    def process_item(self, item, spider):
        # 使用twisted将mysql插入变成异步执行：参数1：我们自定义一个函数,里面可以写我们的插入逻辑
        query = self.dbpool.runInteraction(self.do_insert, item)
        # 添加自己的处理异常的函数
        query.addErrback(self.handle_error, item, spider)

    def do_insert(self, cursor, item):
        # 执行具体的插入
        # 根据不同的item 构建不同的sql语句并插入到mysql中
        insert_sql, params = item.get_insert_sql()
        cursor.execute(insert_sql, params)

    def handle_error(self, failure, item, spider):
        # 处理异步插入的异常
        print(failure)


# 自定义的将伯乐在线内容保存到本地json的pipeline


class JsonWithEncodingPipeline(object):
    # 自定义json文件的导出
    def __init__(self):
        # 使用codecs打开避免一些编码问题。
        self.file = codecs.open('article.json', 'w', encoding="utf-8")

    def process_item(self, item, spider):
        # 将item转换为dict,然后调用dumps方法生成json对象，false避免中文出错
        lines = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(lines)
        return item

    # 当spider关闭的时候: 这是一个spider_closed的信号量。
    def spider_closed(self, spider):
        self.file.close()


# 调用scrapy提供的json export导出json文件
class JsonExporterPipeline(object):
    def __init__(self):
        self.file = open('articleexport.json', 'wb')
        self.exporter = JsonItemExporter(
            self.file, encoding="utf-8", ensure_ascii=False)
        self.exporter.start_exporting()

    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item


# 自定义的pipeline,可实现下载图片的同时获取本地地址。
class ArticleImagePipeline(ImagesPipeline):
    # 重写该方法可从result中获取到图片的实际下载地址
    def item_completed(self, results, item, info):
        image_paths = [x['path'] for ok, x in results if ok]
        if not image_paths:
            raise DropItem('没有图片')
        item['front_image_path'] = image_paths
        return item


class ElasticSearchPipeline(object):
    def process_item(self, item, spider):
        # 将item转化为es的数据
        item.save_to_es()

        return item
