from urllib.parse import urlencode
from lxml.etree import XMLSyntaxError
from pyquery import PyQuery as pq
import requests
import pymongo

MONGO_URL = 'localhost'
MONGO_DB = 'weixin'
MONGO_TABLE = 'articles'
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]
base_url = 'http://weixin.sogou.com/weixin?'
keyword = '扒一扒淘宝美食'

headers = {
    'Cookie': 'CXID=159A55B12E8AB2CC35BD5891C3B66D69; SUV=005E59E8D38E12345AE51B4E8B944494; ad=sFjvvZllll2zTBfYlllllV7RZPclllllLPoGoZllll9lllllVA7ll5@@@@@@@@@@; SUID=A30C1ADA3765860A5ADD9E9800042FF5; ABTEST=1|1527295959|v1; IPLOC=CN1401; ld=5Zllllllll2bVNPLQegYWq7qL4BbVNPihupW7kllll9llllxxylll5@@@@@@@@@@; cd=1528158329&0bd82a3f0526bf76d00f7b561835ac87; rd=5Zllllllll2bVNPLQegYWq7qL4BbVNPihupW7kllll9llllxxylll5@@@@@@@@@@; SUIR=208899598386ED7693E1D2A8846940CF; SNUID=10BEA869B3B6DD461BACDFC7B3FA9F92; JSESSIONID=aaautrKdR_SX9fdL3onnw',
    'Host': 'weixin.sogou.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
}

proxy_pool_url = 'http://127.0.0.1:5000/get'
proxy = requests.get(proxy_pool_url).text
max_count = 5


def get_proxy():
    try:
        response = requests.get(proxy_pool_url)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError as e:
        return None


def get_html(url, count=1):
    global proxy
    if count >= max_count:
        print('Tried too many counts')
        return None
    try:
        if proxy:
            proxies = {'http': 'http://' + proxy}
            response = requests.get(url, allow_redirects=False, headers=headers, proxies=proxies)
        else:
            response = requests.get(url, allow_redirects=False, headers=headers)
        if response.status_code == 200:
            return response.text
        if response.status_code == 302:
            proxy = get_proxy()
            print('current using proxy:', proxy)
            if proxy:
                print(proxy)
                return get_html(url)
            else:
                print('Get Proxy Failed')
                return None
    except ConnectionError as e:
        count += 1
        proxy = get_proxy()
        return get_html(url)


def get_index(keyword, page):
    data = {
        'query': keyword,
        'type': 2,
        'page': page
    }
    queries = urlencode(data)
    url = base_url + queries
    html = get_html(url)
    return html


def parse_index(html):
    doc = pq(html)
    items = doc('.news-box .news-list li .txt-box h3 a').items()
    for item in items:
        yield item.attr('href')


def get_detail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return None
    except ConnectionError:
        return None


def parse_detail(html):
    try:
        doc = pq(html)
        title = doc('#activity-name').text()
        data = doc('#publish_time').text()
        content = doc('#js_content').text()
        nickname = doc('#profileBt').text()
        return {
            'title': title,
            'data': data,
            'content': content,
            'nickname': nickname
        }
    except XMLSyntaxError:
        return None


def save_to_mongo(result):
    if db[MONGO_TABLE].update({'title': result['title']}, {'$set': result}, True):
        print('保存成功', result['title'])
    else:
        print("保存失败", result['title'])


def main():
    for page in range(1, 4):
        html = get_index(keyword, page)
        if html:
            article_urls = parse_index(html)
            for article_url in article_urls:
                html = get_detail(article_url)
                if html:
                    result = parse_detail(html)
                    if result:
                        save_to_mongo(result)


if __name__ == '__main__':
    main()
