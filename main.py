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
import threading

# 如果是Windows的话，需要稍微修改一下输出的默认编码，不然可能会有不能显示的字符的情况
if config.configs['platform'] == 'Windows':
    import io,sys
    #改变标准输出的默认编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='gb18030') 

# ===============================================================
# 专门用于保存文件的类，用于处理麻烦的路径问题
# ===============================================================
class FileSaver(object):
    # 默认初始化保存目录为当前目录
    def __init__(self, path_prefix = '.'):
        self._path_prefix = path_prefix;

    # 保存文件
    def saveFile(self, file_path, content):
        pathes = os.path.split(file_path);
        path = pathes[0];
        # 防止没有文件路径的情况
        if len(path) == 0:
            path = '.';
        # 将保存文件的路径设置到总路径下面的子路径里
        #（总路径在其他函数设置）
        path = self._path_prefix + '/' + path;
        # 如果路径不存在的话就强制创建路径
        if os.path.isdir(path) is not True:
            os.makedirs(path);

        # 对文件进行写入
        with open(path+'/'+pathes[1], 'wb') as f:
            if isinstance(content, bytes):
                f.write(content);
            elif isinstance(content, str):
                f.write(content.encode('utf-8'));

        # 对写入的文件进行日志记录
        logging.info('File %s saved' % (path+'/'+pathes[1]));

    # 设定保存的总路径
    def setSavePath(self, path_prefix):
        self._path_prefix = path_prefix;

# ===============================================================
# 获取HTML
# ===============================================================
def getHTML(url):
    html_doc = request.urlopen(url).read();
    return html_doc;

# ===============================================================
# 下载图像，同时将HTML中的路径替换成本地路径
# ===============================================================
def downloadImage(url, content, file_saver):
    # 解析HTML
    soup = BeautifulSoup(content, config.configs['bs4_parser']);
    # 获取img的标签，也就是包含图片的标签
    imgs = soup.findAll('img');
    for img in imgs:
        logging.info(img);
        try:
            # 防止img标签不存在‘src’属性
            logging.info(img['src']);
        except KeyError:
            continue;
        match_flag = 0;
        matches = re.match(r'^(http|https)://(.*\.)(jpg|png|gif)', str(img['src']))
         # 图片是外部链接
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
        # 检测到有图片时，就需要将图片下载下来，并修改相应的的HTML文件内容
        if match_flag == 1:
            # 获取并保存图片文件
            imgContent = request.urlopen(imgUrl).read();
            file_saver.saveFile(imgPath, imgContent);
            # 修改html内容
            content = content.replace(img['src'].encode('utf-8'), imgPath.encode('utf-8'));
    return content;

# ===============================================================
# 下载CSS，同时将HTML中的路径替换成本地路径
# ===============================================================
def downloadCss(url, content, file_saver):
    # 解析HTML
    soup = BeautifulSoup(content, config.configs['bs4_parser']);
    # 找到所有css文件所在的标签
    csss = soup.findAll('link', attrs={'type':'text/css'});
    for css in csss:
        logging.info(css);
        try:
            # 防止css文件不存在外链的属性
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
            # 获取CSS文件并保存
            cssContent = request.urlopen(cssUrl).read();
            file_saver.saveFile(cssPath, cssContent);
            # 修改HTML中的CSS文件所指向的内容
            content = content.replace(css['href'].encode('utf-8'), cssPath.encode('utf-8'));
    return content;

# ===============================================================
# 下载JS，同时将HTML中的路径替换成本地路径
# ===============================================================
def downloadJavaScript(url, content, file_saver):
    # 解析HTML
    soup = BeautifulSoup(content, config.configs['bs4_parser']);
    # 找到所有JavaScript所在的标签
    jss = soup.findAll('script', attrs={'type':'text/javascript'});
    for js in jss:
        logging.info(js);
        try:
            # 防止不存在‘src’属性
            logging.info(js['src']);
        except KeyError:
            continue;
        match_flag = 0;
        # CSS是外部链接文件
        if re.match(r'^(http|https)://.*\.js$', str(js['src'])):
            logging.info('JS: Match outer link.');
            jsStr = re.split(r'://', js['src']);
            jsUrl = js['src'];
            jsPath = './js/' + jsStr[1];
            match_flag = 1;
        # CSS是本地服务器资源
        if re.match(r'^/.*\.js$', str(js['src'])):
            logging.info('JS: Match local resource');
            jsUrl = url + js['src'];
            jsPath = './js/local' + js['src'];
            match_flag = 1;
        if match_flag == 1:
            # 获取并保存CSS
            jsContent = request.urlopen(jsUrl).read();
            file_saver.saveFile(jsPath, jsContent);
            # 修改HTML中CSS所指向的内容
            content = content.replace(js['src'].encode('utf-8'), jsPath.encode('utf-8'));
    return content;

# ===============================================================
# 将超链接进行转换，以使得在本地打开的时候可以正常访问
# ===============================================================
def convertHyperLink(url, content):
    content = content.replace(r'href="/'.encode('utf-8'), (r'href="'+url+r'/').encode('utf-8'));
    content = content.replace(r'href="#"'.encode('utf-8'), (r'href="'+url+r'/#"').encode('utf-8'));
    return content;

# ===============================================================
# 获取当前时间戳，用以设置保存的目录
# ===============================================================
def getTimeTag():
    return datetime.now().strftime('%Y%m%d%H%M');

# ===============================================================
# 获取命令行输入的参数
# ===============================================================
def getOpt():
    opts,args = getopt.getopt(sys.argv[1:], "d:u:o:");
    period  = config.configs['default_period'];
    url = config.configs['default_url'];
    store_path = config.configs['default_folder'];

    for op,value in opts:
        if op == '-d':
            period = int(value);
        elif op == '-u':
            url = value;
        elif op == '-o':
            store_path = value;
        else:
            print("Plese input the right parameters.");
            sys.exit();

    if re.match(r'(http|https)://.*', url) is None:
        print("Please input a correct URL.(by using -u option)")
        sys.exit();

    return period, url, store_path;

#=================================================================
# 保存网页的函数，也是该脚本功能的核心函数
# 由于没有办法保证所有的备份线程都可以在下一个备份线程开始之前结束
# 所以必须要保证备份进程是可重入的，这样才可以保证多线程正常运行
# ================================================================
def saveWebPage(url, path):
    # 获取当前时间戳（只能获取一次，以保持一致性）
    time_tag = getTimeTag();
    file_saver = FileSaver();
    # 防止所设定的路径没有加斜杠作为路径结尾
    if re.match(r'.*/$', path) is not None:
        file_saver.setSavePath(path + time_tag);
    else:
        file_saver.setSavePath(path + '/' + time_tag);
    # 输出备份开始的提示
    print('Backup at Time Tag %s starts.' % time_tag);
    sys.stdout.flush();
    # 获取HTML
    html_content = getHTML(url);
    # 下载图片并修改HTML
    html_content = downloadImage(url, html_content, file_saver);
    # 下载CSS并修改HTML
    html_content = downloadCss(url, html_content, file_saver);
    # 下载JS并修改HTML
    html_content = downloadJavaScript(url, html_content, file_saver);
    # 修改HTML中的指向本地服务器的超链接
    html_content = convertHyperLink(url, html_content);
    file_saver.saveFile('index.html', html_content);
    # 输出备份完成的提示
    print('Backup at Time Tag %s is saved.' % time_tag);
    sys.stdout.flush();

# ===============================================================
# 该函数利用定时器保证了每隔period周期就执行一个任务
# ===============================================================
def runPeriodTask(period, url, path):
    timer = threading.Timer(period, runPeriodTask, (period, url, path));
    timer.start();
    saveWebPage(url, path);

# ===============================================================
# 测试函数
# ===============================================================
if __name__ == '__main__':
    period, url, store_path = getOpt();
    runPeriodTask(period, url, store_path);
