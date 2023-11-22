import asyncio
import json
import logging
import os
import re
import time
import warnings
from argparse import ArgumentParser
from pathlib import Path
from threading import Thread

import requests
from aiohttp import client
from bs4 import BeautifulSoup


class Spinder():
    ''' 获取所有链接 '''

    def __init__(self, url, headers):
        '''
            log 日志对象
            url 爬取的url
            headers requests头部信息
            book 书籍名字
        '''
        self.url = url
        self.headers = headers
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
        return rsp.text

    def beautiful_html(self,html):
        ''' 修复html '''
        soup = BeautifulSoup(html, 'lxml')
        soup.prettify()
        return soup

    def book_name(self):
        ''' 获取书籍名字 '''
        book = self.soup.select("#content-list > div.book-intro.clearfix > div.book-describe > h1")[0].get_text()
        return book


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

    def extract_section(self) -> int:
        '''
         获取文章url
         return url_num 
        '''
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
        url_num = 0
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
                url_num += 1
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
        return url_num

    def save(self):
        ''' 保存到json '''
        with open(self.book + '.json', 'w', encoding='utf-8') as f:
            json.dump(self.pieces, f, ensure_ascii=False)

    def run(self):
        ''' 开始方法 '''
        self.progress = [100,0] # 进度 第一个 总的url数量
        html = self.get_html()
        self.soup = self.beautiful_html(html)
        self.book = self.book_name()
        self.progress[0]  = self.extract_section()

    def print_data(self):
        ''' 打印 存放的url的字典 '''
        print(self.pieces)


class Download(Spinder):
    def __init__(self, url, headers):
        self.texts = {}
        ''' 调用父类的构造方法 '''
        super().__init__(url, headers)


    def extract_txt(self, html):
        ''' 提取文章内容 '''
        # 修复html
        soup = BeautifulSoup(html, 'lxml')
        soup.prettify()

        # 获取文章内容的html 列表
        texts = soup.select('#nr1')[0].find_all('p', {'class': False})
        # 初始化文章内容
        p = ''
        for text in texts:
            # 去除 不需要的
            target = re.match('.*?落.*?霞.*?小.*?(说|說).*?', str(text))
            if not target:
                # 获取文章内容
                p += text.get_text('\n')+'\n'
        return p


    def print_progress(self):
        ''' 打印进度条 '''
        while True:
            progress = self.progress[1]/self.progress[0]
            text = "\r["+">"*int(progress*40)+"-"*int((1-progress)*40)+ "] \033[35m {book} \033[0m   \033[32m{}%     ({}/{})\033[0m".format(round(progress*100,2),self.progress[1],self.progress[0],book=self.book)
            print(text,end="")
            time.sleep(0.5)


    async def get_text_html(self, url, title, piece, id_num):
        ''' aiohttp 异步获取内容 '''
        async with self.session.get(url) as rsp:
            html = await rsp.text()
            # 提取需要的内容
            text = self.extract_txt(html)
            # 进度+1 
            self.progress[1] += 1
            # 文章内容添加到字典
            self.texts[piece].append((id_num,title,text))


    async def async_download(self,loop):
        # loop 无关紧要
        if loop:
            asyncio.set_event_loop(loop)
            self.loop = loop
            self.log.setLevel(logging.ERROR)
        else:
            self.loop = asyncio.get_event_loop()
        # aiohttp 获取session
        self.session = client.ClientSession(headers=self.headers)
        # 协程任务列表
        tasks = []
        # 添加协程任务
        # pieces {卷名:[(章节名称,链接),]}
        for piece, sections in self.pieces.items():
            # 初始化 存文章内容的列表
            # texts {
            #        卷名:[(序号,章节名,内容),]
            #   }
            self.texts[piece] = []
            # 序号
            id_num = 1

            for title, link in sections:
                # tile 章节名
                # link 章节链接
                # piece 卷名
                # id_num 序号
                # 创建一个协程任务 获取html
                task = self.get_text_html(link, title, piece, id_num)
                # 加入列表
                task = asyncio.create_task(task)
                tasks.append(task)
                await task
                id_num += 1
        await self.session.close()
    def download(self, loop):
        ''' 下载 '''

        self.log.info('开始下载 %s' % self.book)
        # 打印进度 
        Thread(target=self.print_progress,name="print_progress",daemon=True).start()
        # 运行协程任务
        task = self.async_download(None)
        asyncio.run(task)




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
        stop = time.time()
        # 打印日志
        self.log.info('写入文件完成爬取完成 总时间 %s s' % (stop - start))

    def save_file(self, save_path,piece,texts):
        ''' 保存到文件 '''
        # 通过序号排序
        texts = sorted(texts, key=lambda x: x[0])
        # 判断目录是否存在 不存在创建
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        # 保存的文件名
        path = os.path.join(save_path, f"{self.book}-{piece}.txt")
        if piece == '':
            # 没有卷名就直接保存书名
            path = os.path.join(save_path, f"{self.book}.txt")
        
        # 打开文件
        f = Path(path).open("w",1024,"utf-8")
        # texts 
        #       [(序号,章节名,内容),]
        #   
        for id_num,  title, text in texts:
                title = re.sub('第(.*)幕', '第\g<1>章', title)
                if not re.match('第.*([章篇])', title):
                    title = '第%s章 ' % id_num + title
                f.write(title+'\n')
                f.write(text)
                f.write('\n\n\n')
        f.close()

    def save(self,save_path):
        ''' 不同卷名保存不同文件 '''
        # texts {
        #        卷名:[(序号,章节名,内容),],
        #   }

        # 不止一个文件时 创建文件夹保存
        if len(self.texts.keys()) > 1:
            save_path = os.path.join(save_path,self.book)
        for piece,content in self.texts.items():
            self.save_file(save_path,piece,content)


def initParser():
    ''' 初始化参数解析器 '''
    parser = ArgumentParser("bookdown", "bookdown", "小说爬虫洛霞小说网", "v1.0")
    parser.add_argument("url", type=str, help="目标url 示例 http://www.luoxia.com/longzu/")
    parser.add_argument("-d", dest="dir", type=str, default="./books", help="下载目录 默认./books", required=False,nargs="?")
    return parser


def main():
    ''' 总入口 '''
    parser = initParser()
    args = parser.parse_args()


    warnings.filterwarnings("ignore")

    url = args.url
    headers = {
        "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
    }

    s1 = Download(url,
                  headers=headers,)
    s1.run(args.dir)


if __name__ == "__main__":
    import sys,traceback
    try:
        main()
    except Exception as e:
        logging.error(e)
        traceback.print_exc()
        sys.exit(1)
