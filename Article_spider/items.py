# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html
import datetime

import re

import redis
import scrapy
from elasticsearch_dsl.connections import connections
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, Join, MapCompose
from Article_spider.settings import SQL_DATETIME_FORMAT, SQL_DATE_FORMAT

from w3lib.html import remove_tags

from Article_spider.models.es_jobbole import ArticleType
from Article_spider.models.es_lagou import LagouType
from Article_spider.models.es_zhihu import ZhiHuQuestionType, ZhiHuAnswerType
from Article_spider.utils.common import get_nums

es = connections.create_connection(ArticleType._doc_type.using)
redis_cli = redis.StrictRedis()


class JobboleItemLoader(ItemLoader):  # 重载属性.设置直选第一个值
    default_output_processor = TakeFirst()


def get_time(value):
    try:
        creat_date = datetime.datetime.strptime(value, '%Y/%m/%d').date()
    except Exception as e:
        creat_date = datetime.datetime.now().date()
    return creat_date


def filter_tag_list(value):
    if "评论" in value:
        return ""
    else:
        return value


def get_value(value):
    return value


def gen_suggests(index, info_tuple):
    # 根据字符串生成搜索建议数组
    used_words = set()
    suggests = []
    for text, weight in info_tuple:
        if text:
            # 调用es的analyze接口分析字符串
            words = es.indices.analyze(index=index, params={'filter': ['lowercase'], 'analyzer': "ik_max_word"},
                                       body=text)
            analyzed_words = set([r['token'] for r in words['tokens'] if len(r['token']) > 1])
            new_words = analyzed_words - used_words
        else:
            new_words = set()
        if new_words:
            suggests.append({'input': list(new_words), 'weight': weight})
    return suggests


class JobboleItem(scrapy.Item):
    # define the fields for your item here like:
    title = scrapy.Field()
    front_image_url = scrapy.Field(
        output_processor=MapCompose(get_value)
    )
    front_image_path = scrapy.Field()
    create_date = scrapy.Field(
        input_processor=MapCompose(get_time)
    )
    url = scrapy.Field()
    url_object_id = scrapy.Field()
    praise_nums = scrapy.Field(
        inut_processor=MapCompose(get_nums)
    )
    fav_nums = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    comment_nums = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    content = scrapy.Field()
    tags = scrapy.Field(
        input_processor=MapCompose(filter_tag_list),
        output_processor=Join(',')
    )

    def get_insert_sql(self):
        insert_sql = """
               insert into jobbole_ariticle(title,create_date,url,url_object_id,front_image_url2,front_image_path,tags,comment_nums,fav_nums,praise_nums,content)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE content=VALUES(content),comment_nums=VALUES(comment_nums),praise_nums=VALUES(praise_nums),fav_nums=VALUES(fav_nums)

          """
        params = (self["title"], self["create_date"], self["url"],
                  self["url_object_id"], self["front_image_url"], self["front_image_path"],
                  self["tags"], self["comment_nums"], self["fav_nums"], self["praise_nums"],
                  self["content"])
        return insert_sql, params

    def save_to_es(self):
        article = ArticleType()
        article.title = self['title']
        article.create_date = self["create_date"]
        article.url = self["url"]
        article.praise_nums = self["praise_nums"]
        article.fav_nums = self["fav_nums"]
        article.comment_nums = self["comment_nums"]
        article.content = remove_tags(self["content"])
        article.tags = self["tags"]

        article.suggest = gen_suggests(ArticleType._doc_type.index, ((article.title, 10), (article.tags, 7)))

        article.save()
        redis_cli.incr('jobbole_count')
        return


class ZhihuQuestionItem(scrapy.Item):
    question_id = scrapy.Field()
    topics = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    answer_num = scrapy.Field()
    comments_num = scrapy.Field()
    watch_user_num = scrapy.Field()
    click_num = scrapy.Field()
    crawl_time = scrapy.Field()

    def get_insert_sql(self):
        # 插入知乎question表的sql语句
        insert_sql = """
             insert into zhihu_question(question_id,topics,url,title,content,answer_num,comments_num,watch_user_num,click_num,crawl_time)
             VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE content=VALUES(content),comments_num=VALUES(comments_num),watch_user_num=VALUES(watch_user_num),click_num=VALUES(click_num),answer_num=VALUES(answer_num),

        """

        question_id = self['question_id'][0]
        topics = ','.join(self['topics'])
        url = self['url'][0]
        title = self['title'][0]
        try:
            content = "".join(self["content"])
        except BaseException:
            content = "无"
        answer_num = get_nums(self['answer_num'][0])
        comments_num = get_nums(self['comments_num'][0])
        watch_user_num = get_nums(self['watch_user_num'][0])
        click_num = get_nums(self['watch_user_num'][1])
        crawl_time = datetime.datetime.now().strftime(SQL_DATETIME_FORMAT)

        params = (
            question_id, topics, url, title, content, answer_num, comments_num, watch_user_num, click_num, crawl_time)
        return insert_sql, params

    def save_to_es(self):
        ZhihuQ = ZhiHuQuestionType()
        ZhihuQ.question_id = self['question_id'][0]
        ZhihuQ.topics = ','.join(self['topics'])
        ZhihuQ.url = self['url'][0]
        ZhihuQ.title = self['title'][0]
        try:
            ZhihuQ.content = "".join(self["content"])
        except BaseException:
            ZhihuQ.content = "无"
        ZhihuQ.answer_num = get_nums(self['answer_num'][0])
        ZhihuQ.comments_num = get_nums(self['comments_num'][0])
        ZhihuQ.watch_user_num = get_nums(self['watch_user_num'][0])
        ZhihuQ.click_num = get_nums(self['watch_user_num'][1])
        ZhihuQ.suggest = gen_suggests(ArticleType._doc_type.index, ((ZhihuQ.title, 10), (ZhihuQ.content, 7)))

        ZhihuQ.save()
        redis_cli.incr('ZhihuQ_count')
        return


class ZhihuAnswerItem(scrapy.Item):
    answer_id = scrapy.Field()
    url = scrapy.Field()
    question_id = scrapy.Field()
    author_id = scrapy.Field()
    content = scrapy.Field()
    praise_num = scrapy.Field()
    comments_num = scrapy.Field()
    create_time = scrapy.Field()
    update_time = scrapy.Field()
    crawl_time = scrapy.Field()
    title = scrapy.Field()

    def get_insert_sql(self):
        # 插入知乎answer表的sql语句
        insert_sql = """
             insert into zhihu_answer(answer_id,url,question_id,author_id,title,content,praise_num,comments_num,create_time,update_time,crawl_time)
             VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE content=VALUES(content),comments_num=VALUES(comments_num),praise_num=VALUES(praise_num),update_time=VALUES(update_time)

        """
        create_time = datetime.datetime.fromtimestamp(self['create_time']).strftime(SQL_DATE_FORMAT)
        update_time = datetime.datetime.fromtimestamp(self['update_time']).strftime(SQL_DATE_FORMAT)

        params = (
            self['answer_id'], self['url'], self['question_id'], self['author_id'], self['title'], self['content'],
            self['praise_num'],
            self['comments_num'], create_time, update_time, self['crawl_time'].strftime(SQL_DATETIME_FORMAT))
        return insert_sql, params

    def save_to_es(self):
        ZhihuA = ZhiHuAnswerType()
        ZhihuA.answer_id = self['answer_id']
        ZhihuA.question_id = self['question_id']
        ZhihuA.url = self['url']
        ZhihuA.content = remove_tags(self['content'])
        ZhihuA.praise_num = self['praise_num']
        ZhihuA.comments_num = self['comments_num']
        ZhihuA.create_time = datetime.datetime.fromtimestamp(self['create_time']).strftime(SQL_DATE_FORMAT)
        ZhihuA.update_time = datetime.datetime.fromtimestamp(self['update_time']).strftime(SQL_DATE_FORMAT)
        ZhihuA.title = self['title']
        # ZhihuA.suggest = gen_suggests(ArticleType._doc_type.index, (ZhihuA.content, 10))
        ZhihuA.save()
        return


class LagouJobItemLoader(ItemLoader):
    default_output_processor = TakeFirst()


def remove_splash(value):
    # 去掉工作城市的斜杠
    return value.replace('/', '')


def handle_jobaddr(value):
    # 去掉html的tag
    addr_list = value.split('\n')
    addr_list = [item.strip() for item in addr_list if item.strip() != '查看地图']
    return ''.join(addr_list)


class LagouJobItem(scrapy.Item):
    # 拉勾网职位信息
    title = scrapy.Field()
    url = scrapy.Field()
    url_object_id = scrapy.Field()
    salary_min = scrapy.Field(
        input_processor=MapCompose(remove_splash)
    )
    salary_max = scrapy.Field(
        input_processor=MapCompose(remove_splash)
    )
    job_city = scrapy.Field(
        input_processor=MapCompose(remove_splash)
    )
    work_years_min = scrapy.Field()
    work_years_max = scrapy.Field()
    degree_need = scrapy.Field(
        input_processor=MapCompose(remove_splash)
    )
    job_type = scrapy.Field()
    publish_time = scrapy.Field()
    tags = scrapy.Field(
        input_processor=Join(',')
    )
    job_advantage = scrapy.Field()
    job_desc = scrapy.Field()
    job_addr = scrapy.Field(
        input_processor=MapCompose(remove_tags, handle_jobaddr)
    )
    company_url = scrapy.Field()
    company_name = scrapy.Field()
    craw_time = scrapy.Field()

    def get_insert_sql(self):
        # 插入lagou表的sql语句
        insert_sql = """
             insert into lagou_job(title,url,url_object_id,salary_min,salary_max,job_city,work_years_min,work_years_max,degree_need,job_type,publish_time,tags,job_advantage,job_desc,job_addr,company_url,company_name,craw_time)
             VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
             ON DUPLICATE KEY UPDATE salary_min=VALUES(salary_min),salary_max=VALUES(salary_max),work_years_min=VALUES(work_years_min),work_years_max=VALUES(work_years_max),degree_need=VALUES(degree_need),publish_time=VALUES(publish_time),job_advantage=VALUES(job_advantage),job_desc=VALUES(job_desc)

        """

        # 清洗薪资
        match_salary = re.match("(\d+)[Kk]-(\d+)[Kk]", self['salary_min'])
        if match_salary:
            self['salary_min'] = match_salary.group(1)
            self['salary_max'] = match_salary.group(2)
        else:
            self['salary_min'] = 666
            self['salary_max'] = 666

        # 清洗工作经验
        match_obj1 = re.match("经验(\d+)-(\d+)年", self['work_years_min'])
        match_obj2 = re.match("经验应届毕业生", self['work_years_min'])
        match_obj3 = re.match("经验不限", self['work_years_min'])
        match_obj4 = re.match("经验(\d+)年以下", self['work_years_min'])
        match_obj5 = re.match("经验(\d+)年以上", self['work_years_min'])

        if match_obj1:
            self['work_years_min'] = match_obj1.group(1)
            self['work_years_max'] = match_obj1.group(2)
        elif match_obj2:
            self['work_years_min'] = 0.5
            self['work_years_max'] = 0.5
        elif match_obj3:
            self['work_years_min'] = 0
            self['work_years_max'] = 0
        elif match_obj4:
            self['work_years_min'] = 0
            self['work_years_max'] = match_obj4.group(1)
        elif match_obj5:
            self['work_years_min'] = match_obj4.group(1)
            self['work_years_max'] = match_obj4.group(1) + 100
        else:
            self['work_years_min'] = 999
            self['work_years_max'] = 999

        # 发布时间
        match_time1 = re.match("(\d+):(\d+).*", self["publish_time"])
        match_time2 = re.match("(\d+)天前.*", self["publish_time"])
        match_time3 = re.match("(\d+)-(\d+)-(\d+)", self["publish_time"])
        if match_time1:
            today = datetime.datetime.now()
            hour = int(match_time1.group(1))
            minutues = int(match_time1.group(2))
            time = datetime.datetime(
                today.year, today.month, today.day, hour, minutues)
            self["publish_time"] = time.strftime(SQL_DATETIME_FORMAT)
        elif match_time2:
            days_ago = int(match_time2.group(1))
            today = datetime.datetime.now() - datetime.timedelta(days=days_ago)
            self["publish_time"] = today.strftime(SQL_DATETIME_FORMAT)
        elif match_time3:
            year = int(match_time3.group(1))
            month = int(match_time3.group(2))
            day = int(match_time3.group(3))
            today = datetime.datetime(year, month, day)
            self["publish_time"] = today.strftime(SQL_DATETIME_FORMAT)
        else:
            self["publish_time"] = datetime.datetime.now(
            ).strftime(SQL_DATETIME_FORMAT)

        params = (
            self['title'], self['url'], self['url_object_id'], self['salary_min'], self['salary_max'], self['job_city'],
            self['work_years_min'],
            self['work_years_max'], self['degree_need'], self['job_type'], self["publish_time"], self['tags'],
            self['job_advantage'], self['job_desc'],
            self['job_addr'],
            self['company_url'], self['company_name'], self['craw_time'].strftime(SQL_DATETIME_FORMAT)
        )
        return insert_sql, params

    def save_to_es(self):
        Lagou = LagouType()
        Lagou.title = self['title']
        Lagou.url = self['url']
        Lagou.url_object_id = self['url_object_id']
        Lagou.job_city = self['job_city']
        Lagou.degree_need = self['degree_need']
        Lagou.job_type = self['job_type']
        Lagou.publish_time = self['publish_time']
        Lagou.job_advantage = self['job_advantage']
        Lagou.job_desc = self['job_desc']
        Lagou.job_addr = self['job_addr']
        Lagou.company_name = self['company_name']
        Lagou.company_url = self['company_url']
        Lagou.tags = self['tags']
        Lagou.crawl_time = self['craw_time']
        Lagou.suggest = gen_suggests(ArticleType._doc_type.index, ((Lagou.title, 10), (Lagou.tags, 7)))

        Lagou.save()
        redis_cli.incr('Lagou_count')
        return
