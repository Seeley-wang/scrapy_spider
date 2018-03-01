# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request, FormRequest
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from Article_spider.items import LagouJobItemLoader, LagouJobItem
from Article_spider.utils.common import get_md5
from datetime import datetime
import execjs


class lagouSpider(CrawlSpider):
    name = 'lagou'
    allowed_domains = ['www.lagou.com']
    start_urls = ['https://www.lagou.com/']


    # if not settings, it will be redirect to login
    custom_settings = {
        "COOKIES_ENABLED": False,
        "DOWNLOAD_DELAY": 3,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Connection': 'keep-alive',
            'Cookie': 'JHm_lvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1518774740; _ga=GA1.2.668466362.1518774740; user_trace_token=20180216175219-141ab06e-12ff-11e8-8ab5-525400f775ce; LGSID=20180216175219-141ab1ef-12ff-11e8-8ab5-525400f775ce; LGUID=20180216175219-141ab490-12ff-11e8-8ab5-525400f775ce; JSESSIONID=ABAAABAAAGHAABH3094A9BD24636033D42EB2CB1ED1D3C4; _gid=GA1.2.933900909.1518774740; X_HTTP_TOKEN=df764d6327196582f08bad9117e7f80b; _ga=GA1.3.668466362.1518774740; _gat=1; TG-TRACK-CODE=undefined; index_location_city=%E5%B9%BF%E5%B7%9E; gate_login_token=88fc1ecf87ef8192a753c9ac3cd2cf53cbe8a910f2175399; login=false; unick=""; _putrc=""; _gat=1; Hm_lpvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1518779086; LGRID=20180216190445-327d82ff-1309-11e8-b070-5254005c3644',
            'Host': 'www.lagou.com',
            'Origin': 'https://www.lagou.com',
            'Referer': 'https://www.lagou.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36',
        },
        "CONCURRENT_REQUESTS": 100,
        "RETRY_ENABLED": False
    }
    headers = {

    }

    rules = (
        # Rule(LinkExtractor(allow=('zhaopin/.*'),restrict_css=".item_con_list .con_list_item.default_list .list_item_top a::attr(href)"),callback='parse_job'),
        # Rule(LinkExtractor(allow=('gongsi/j\d+.html'))),
        Rule(LinkExtractor(allow=r'jobs/\d+.html'), callback='parse_job', follow=True),
    )

    def parse_job(self, response):
        """
        解析拉勾网的职位
        :param response:
        :return:
        """
        item_loader = LagouJobItemLoader(item=LagouJobItem(), response=response)
        item_loader.add_css("title", ".job-name::attr(title)")
        item_loader.add_value("url", response.url)
        item_loader.add_value("url_object_id", get_md5(response.url))
        item_loader.add_css("salary_min", ".job_request .salary::text")
        item_loader.add_xpath("job_city", "//*[@class='job_request']/p/span[2]/text()")
        item_loader.add_xpath("work_years_min", "//*[@class='job_request']/p/span[3]/text()")
        item_loader.add_xpath("degree_need", "//*[@class='job_request']/p/span[4]/text()")
        item_loader.add_xpath("job_type", "//*[@class='job_request']/p/span[5]/text()")

        item_loader.add_css("tags", '.position-label li::text')
        item_loader.add_css("publish_time", ".publish_time::text")
        item_loader.add_css("job_advantage", ".job-advantage p::text")
        item_loader.add_css("job_desc", ".job_bt div")
        item_loader.add_css("job_addr", ".work_addr")
        item_loader.add_css("company_name", "#job_company dt a img::attr(alt)")
        item_loader.add_css("company_url", "#job_company dt a::attr(href)")
        item_loader.add_value("craw_time", datetime.now())

        job_item = item_loader.load_item()

        return job_item

    # def start_requests(self):
    #     print([Request("https://passport.lagou.com/login/login.json", headers=self.headers, callback=self.post_login)])
    #
    # def post_login(self, response):
    #     print(response.text)
    #     # FormRequeset.from_response是Scrapy提供的一个函数, 用于post表单
    #     # 登陆成功后, 会调用after_login回调函数
    #     param = {
    #         'username': '18734805934',
    #         'password': '5889168f397555fe278b7eb18dde08a2',
    #         'isValidate': 'true',
    #         'request_form_verifyCode:': '',
    #         'submit': ''
    #     }
    #
    #     return [FormRequest.from_response(response,
    #                                       headers=self.headers,
    #                                       formdata=param,
    #                                       callback=self.after_login,
    #                                       dont_filter=True
    #                                       )]
    #     # make_requests_from_url会调用parse，就可以与CrawlSpider的parse进行衔接了
    #
    # def after_login(self, response):
    #     for url in self.start_urls:
    #         yield self.make_requests_from_url(url)
