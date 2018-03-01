from datetime import datetime
from elasticsearch_dsl import DocType, Date, Nested, Boolean, \
    analyzer, InnerDoc, Completion, Keyword, Text, Integer
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.analysis import CustomAnalyzer

connections.create_connection(hosts=["127.0.0.1"])


class CustomAnalyzer(CustomAnalyzer):
    def get_analysis_definition(self):
        return {}


ik_analyzer = CustomAnalyzer("ik_max_word", filter=["lowercase"])


class ZhiHuQuestionType(DocType):
    suggest = Completion(analyzer=ik_analyzer)
    # 知乎的问题 item
    question_id = Keyword()
    topics = Keyword()
    url = Keyword()
    title = Text(analyzer="ik_max_word")
    content = Text(analyzer="ik_max_word")
    answer_num = Integer()
    comments_num = Integer()
    watch_user_num = Integer()
    click_num = Integer()
    crawl_time = Date()

    class Meta:
        index = "zhihu"
        doc_type = "question"


class ZhiHuAnswerType(DocType):
    suggest = Completion(analyzer=ik_analyzer)
    # 知乎的问题 item
    answer_id = Keyword()
    question_id = Keyword()
    topics = Keyword()
    url = Keyword()
    title = Text(analyzer="ik_max_word")
    content = Text(analyzer="ik_max_word")
    answer_num = Integer()
    comments_num = Integer()
    watch_user_num = Integer()
    click_num = Integer()
    crawl_time = Date()
    create_date = Date()

    class Meta:
        index = "zhihu"
        doc_type = "answer"


if __name__ == "__main__":
    ZhiHuQuestionType.init()
    ZhiHuAnswerType.init()
