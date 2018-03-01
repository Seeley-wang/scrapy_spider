from datetime import datetime
from elasticsearch_dsl import DocType, Date, Nested, Boolean, \
    analyzer, InnerDoc, Completion, Keyword, Text, Integer
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.analysis import CustomAnalyzer

connections.create_connection(hosts=["localhost"])


class CustomAnalyzer(CustomAnalyzer):
    def get_analysis_definition(self):
        return {}


ik_analyzer = CustomAnalyzer('ik_max_word', filter=['lowercase'])


class ArticleType(DocType):
    # 伯乐在线文章类型
    suggest = Completion(analyzer=ik_analyzer)
    title = Text(analyzer='ik_max_word')
    create_date = Date()
    url = Keyword()
    content = Text(analyzer='ik_max_word')
    tags = Text(analyzer='ik_max_word')

    class Meta:
        index = 'jobbole'
        doc_type = 'article'


if __name__ == '__main__':
    ArticleType.init()
