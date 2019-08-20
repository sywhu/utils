import asyncio
import json
import logging
import os
import re
import time
import warnings
from argparse import ArgumentParser
from pathlib import Path

import requests
from aiohttp import client
from bs4 import BeautifulSoup


class Spinder():
    ''' 获取所有链接 '''

    def __init__(self, url, headers, book):
        '''
            log 日志对象
            url 爬取的url
            headers requests头部信息
            book 书籍名字
        '''
        self.url = url
        self.headers = headers
        self.book = book
        # 日志初始化
        self.log = self.log_init()

    def log_init(self):
        ''' 日志初始化 '''
        log = logging.getLogger()
        log.setLevel(logging.INFO)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        log.addHandler(console)
        return log

    def get_html(self):
        ''' 获取html '''
        rsp = requests.get(self.url, headers=self.headers)
        self.html = rsp.text

    def beautiful_html(self):
        ''' 修复html '''
        soup = BeautifulSoup(self.html, 'lxml')
        soup.prettify()
        self.soup = soup

    def extract_piece(self):
        ''' 获取卷名 '''
        atts = {
            'class': 'title clearfix'
        }
        pieces = self.soup.find_all('div', atts)
        for piece in pieces:
            piece = piece.get_text(strip=True)
            # 如果没有就 设置为其他
            if piece == '-':
                piece = '其他'
            yield piece

    def extract_section(self):
        ''' 获取文章url '''
        atts = {
            'class': 'book-list clearfix'
        }
        # 获取每一个卷名下面的html对象
        warps = self.soup.find_all('div', atts)
        # 初始化生成器
        a = self.extract_piece()
        # 所有url 保存的对象
        pieces = {}
        # for 获取每一个 卷明下面的html对象
        for warp in warps:
            try:
                # 利用生成器 获取卷名
                piece = next(a)
            except:
                # 获取失败卷名为空
                piece = ''
            # 初始化存放卷下面url的列表
            pieces[piece] = []
            # 获取下面的每个存放url的列表
            sections = warp.ul.find_all('li')
            # 获取每一个url
            for section in sections:
                # html 一些是open 一些是a链接 判断获取url
                if section.a == None:
                    section = section.b
                    link = section.attrs['onclick']
                    try:
                        link = re.findall('window.open\("(.*?)"\)', link)[0]
                    except:
                        link = re.findall("window.open\('(.*?)'\)", link)[0]
                else:
                    section = section.a
                    link = section.attrs['href']
                # 获取每一个li下面的文字就是标题
                title = section.get_text(strip=True)
                # 存放 标题和url
                pieces[piece].append((title, link))
        # 存入类变量中
        self.pieces = pieces

    def save(self):
        ''' 保存到json '''
        with open(self.book + '.json', 'w', encoding='utf-8') as f:
            json.dump(self.pieces, f, ensure_ascii=False)

    def run(self):
        ''' 开始方法 '''
        self.get_html()
        self.beautiful_html()
        self.extract_section()

    def print_data(self):
        ''' 打印 存放的url的字典 '''
        print(self.pieces)


class Download(Spinder):
    def __init__(self, url, headers, book):
        self.texts = {}
        ''' 调用父类的构造方法 '''
        super().__init__(url, headers, book)


    def extract_txt(self, html):
        ''' 提取文章内容 '''
        soup = BeautifulSoup(html, 'lxml')
        soup.prettify()
        texts = soup.select('#nr1')[0].find_all('p', {'class': False})
        p = ''
        for text in texts:
            target = re.match('.*?落.*?霞.*?小.*?(说|說).*?', str(text))
            if not target:
                p += text.get_text('\n')+'\n'
        return p

    async def get_text_html(self, url, title, piece, id_num):
        ''' aiohttp 异步获取内容 '''
        async with self.session.get(url) as rsp:
            html = await rsp.text()
            text = self.extract_txt(html)
            self.texts[piece].append((id_num,title,text))


    def download(self, loop):
        ''' 下载 '''
        if loop:
            asyncio.set_event_loop(loop)
            self.loop = loop
            self.log.setLevel(logging.ERROR)
        else:
            self.loop = asyncio.get_event_loop()
        self.session = client.ClientSession(headers=self.headers)
        tasks = []
        for piece, sections in self.pieces.items():
            self.texts[piece] = []
            id_num = 1

            for title, link in sections:
                task = self.get_text_html(link, title, piece, id_num)
                tasks.append(task)
                id_num += 1
        self.log.info('开始下载 %s' % self.book)
        self.loop.run_until_complete(asyncio.wait(tasks))


    async def clean(self):
        ''' 异步关闭aiohttp '''
        await self.session.close()

    def close(self):
        ''' 关闭aiohttp '''
        self.loop.run_until_complete(self.clean())
        self.loop.close()

    def run(self, save_path='.', loop=None):
        ''' 开始方法 '''
        # 获取开始时间
        start = time.time()
        # 调用父类方法 获取所有url
        super().run()
        # 调用下载方法
        self.download(loop)
        # 打印日志
        self.log.info('开始写入文件 %s.txt' % self.book)
        # 调用保存方法保存文件
        self.save(save_path)
        # 关闭aiohttp
        self.close()
        stop = time.time()
        # 打印日志
        self.log.info('写入文件完成爬取完成 总时间 %s s' % (stop - start))

    def save_file(self, save_path,piece,texts):
        ''' 保存到文件 '''
        texts = sorted(texts, key=lambda x: x[0])
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        path = os.path.join(save_path, f"{self.book}-{piece}.txt")
        if piece == '':
            path = os.path.join(save_path, f"{self.book}.txt")

        if os.path.exists(path):
            os.remove(path)
        f = Path(path).open("w",1024,"utf-8")
        for id_num,  title, text in texts:
                title = re.sub('第(.*)幕', '第\g<1>章', title)
                if not re.match('第.*(章|篇)', title):
                    title = '第%s章 ' % id_num + title
                f.write(title+'\n')
                f.write(text)
                f.write('\n\n\n')
        f.close()

    def save(self,save_path):
        for piece,content in self.texts.items():
            self.save_file(save_path,piece,content)


def initParser():
    ''' 初始化参数解析器 '''
    parser = ArgumentParser("bookdown", "book", "小说爬虫洛霞小说网", "v1")
    parser.add_argument("url", type=str, help="目标url")
    parser.add_argument("-n", dest="name", type=str, help="名字", required=True)
    parser.add_argument("-d", dest="dir", type=str, default="./books", help="下载目录", required=False,nargs="?")
    return parser


def main():
    ''' 总入口 '''
    parser = initParser()
    args = parser.parse_args()


    warnings.filterwarnings("ignore")


    url = 'http://www.luoxia.com/longzu/'
    url = args.url
    book = args.name
    headers = {
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
    }

    s1 = Download(url,
                  headers=headers, book=book)
    s1.run(args.dir)


if __name__ == "__main__":
    import sys
    try:

        main()
    except Exception as e:
        logging.error(e)
        sys.exit(1)
