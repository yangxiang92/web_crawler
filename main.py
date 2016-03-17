#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2016 - yangxiang <yangxiang92@163.com>

import os
from bs4 import BeautifulSoup
import re
from urllib import request
import logging
import config
from datetime import datetime
import sys,getopt
import sched,time,threading

# 如果是Windows的话，需要稍微修改一下输出的默认编码，不然可能会有不能显示的字符的情况
if config.configs['platform'] == 'Windows':
    import io,sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='gb18030') #改变标准输出的默认编码

# 专门用于保存文件的类，用于处理麻烦的路径问题
class FileSaver(object):
    def __init__(self, path_prefix = '.'):
        self._path_prefix = path_prefix;

    def saveFile(self, file_path, content):
        pathes = os.path.split(file_path);
        path = pathes[0];
        if len(path) == 0:
            path = '.';
        path = self._path_prefix + '/' + path;
        if os.path.isdir(path) is not True:
            os.makedirs(path);

        with open(path+'/'+pathes[1], 'wb') as f:
            if isinstance(content, bytes):
                f.write(content);
            elif isinstance(content, str):
                f.write(content.encode('utf-8'));

        logging.info('File %s saved' % (path+'/'+pathes[1]));
        print('File %s saved' % (path+'/'+pathes[1]));
        sys.stdout.flush();

    def setSavePath(self, path_prefix):
        self._path_prefix = path_prefix;

# 获取HTML并把HTML解析的结果放在__soup里面
def getHTML(url):
    html_doc = request.urlopen(url).read();
    return html_doc;

# 下载图像，同时将HTML中的路径替换成本地路径
def downloadImage(url, content, file_saver):
    soup = BeautifulSoup(content, config.configs['bs4_parser']);
    imgs = soup.findAll('img');
    for img in imgs:
        logging.info(img);
        try:
            logging.info(img['src']);
        except KeyError:
            continue;
        match_flag = 0;
        # 图片是外部链接
        matches = re.match(r'^(http|https)://(.*\.)(jpg|png|gif)', str(img['src']))
        if matches is not None:
            logging.info('Image: Match outer link.')
            imgUrl = img['src'];
            imgPath = './images/' + matches.group(2) + matches.group(3);
            match_flag = 1;
        else:
            matches = re.match(r'^/(.*\.)(jpg|png|gif)', img['src']);
            # 图片是本站资源
            if matches is not None:
                logging.info('Image: Match local resouce.')
                imgUrl = url + img['src'];
                imgPath = './images/local' + matches.group(2) + matches.group(3);
                match_flag = 1;
        if match_flag == 1:
            imgContent = request.urlopen(imgUrl).read();
            file_saver.saveFile(imgPath, imgContent);
            content = content.replace(img['src'].encode('utf-8'), imgPath.encode('utf-8'));
    return content;

# 下载CSS，同时将HTML中的路径替换成本地路径
def downloadCss(url, content, file_saver):
    soup = BeautifulSoup(content, config.configs['bs4_parser']);
    csss = soup.findAll('link', attrs={'type':'text/css'});
    for css in csss:
        logging.info(css);
        try:
            logging.info(css['href']);
        except KeyError:
            continue;
        match_flag = 0;
        # CSS是外部链接资源（没看到主页上有除了这种之外的CSS资源。。。）
        if re.match(r'^(http|https)://.*\.css$', str(css['href'])):
            logging.info('CSS: Match outer link.');
            cssStr = re.split(r'://', css['href']);
            cssUrl = css['href'];
            cssPath = './css/' + cssStr[1];
            match_flag = 1;
        if match_flag == 1:
            cssContent = request.urlopen(cssUrl).read();
            file_saver.saveFile(cssPath, cssContent);
            content = content.replace(css['href'].encode('utf-8'), cssPath.encode('utf-8'));
    return content;

# 下载JS，同时将HTML中的路径替换成本地路径
def downloadJavaScript(url, content, file_saver):
    soup = BeautifulSoup(content, config.configs['bs4_parser']);
    jss = soup.findAll('script', attrs={'type':'text/javascript'});
    for js in jss:
        logging.info(js);
        try:
            logging.info(js['src']);
        except KeyError:
            continue;
        match_flag = 0;
        if re.match(r'^(http|https)://.*\.js$', str(js['src'])):
            logging.info('JS: Match outer link.');
            jsStr = re.split(r'://', js['src']);
            jsUrl = js['src'];
            jsPath = './js/' + jsStr[1];
            match_flag = 1;
        if re.match(r'^/.*\.js$', str(js['src'])):
            logging.info('JS: Match local resource');
            jsUrl = url + js['src'];
            jsPath = './js/local' + js['src'];
            match_flag = 1;
        if match_flag == 1:
            jsContent = request.urlopen(jsUrl).read();
            file_saver.saveFile(jsPath, jsContent);
            content = content.replace(js['src'].encode('utf-8'), jsPath.encode('utf-8'));
    return content;

# 将超链接进行转换，以使得在本地打开的时候可以正常访问
def convertHyperLink(url, content):
    content = content.replace(r'href="/'.encode('utf-8'), (r'href="'+url+r'/').encode('utf-8'));
    content = content.replace(r'href="#"'.encode('utf-8'), (r'href="'+url+r'/#"').encode('utf-8'));
    return content;

# 获取当前时间戳，用以设置保存的目录
def getTimeTag():
    return datetime.now().strftime('%Y%m%d%H%M%S');

# 获取命令行输入的参数
def getOpt():
    opts,args = getopt.getopt(sys.argv[1:], "d:u:o");
    period  = config.configs['default_period'];
    url = '';
    store_path = ['default_folder'];

    for op,value in opts:
        if op == '-h':
            period = int(value);
        elif op == '-u':
            url = value;
        elif op == '-o':
            store_path = value;
        else:
            print("Plese input the right parameters.");
            sys.exit();

    if len(url) == 0:
        print("Please input URL.")
        sys.exit();

    return period, url, store_path;

# 保存网页的函数，也是该脚本功能的核心函数
def saveWebPage(url, path):
    time_tag = getTimeTag();
    file_saver = FileSaver();
    if re.match(r'.*/$', path) is not None:
        file_saver.setSavePath(path + time_tag);
    else:
        file_saver.setSavePath(path + '/' + time_tag);
    print('Backup at Time Tag %s starts.' % time_tag);
    sys.stdout.flush();
    html_content = getHTML(url);
    html_content = downloadImage(url, html_content, file_saver);
    html_content = downloadCss(url, html_content, file_saver);
    html_content = downloadJavaScript(url, html_content, file_saver);
    html_content = convertHyperLink(url, html_content);
    file_saver.saveFile('index.html', html_content);
    print('Backup at Time Tag %s is saved.' % time_tag);
    sys.stdout.flush();

def periodTask(period, url, path):
    #global timer;
    timer = threading.Timer(period, periodTask, (period, url, path));
    timer.start();
    saveWebPage(url, path);

def runPeriodTask(period, url, path):
    timer = threading.Timer(period, periodTask, (period, url, path));
    timer.start();
    saveWebPage(url, path);

# 测试函数
if __name__ == '__main__':
    period, url, store_path = getOpt();
    runPeriodTask(period, url, store_path);
