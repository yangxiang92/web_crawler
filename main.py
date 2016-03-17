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
    import io
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
# 获取URL内容
# ===============================================================
def getUrl(url):
    req = request.Request(url);
    req.add_header('User-Agent', config.configs['browser_symbol']);
    with request.urlopen(req) as f:
        return f.read();

# ===============================================================
# 获取HTML
# ===============================================================
def getHTML(url):
    html_doc = getUrl(url);
    return html_doc;

# ===============================================================
# 下载图像，同时将HTML中的路径替换成本地路径
# ===============================================================
def downloadImage(url, soup, file_saver):
    # 获取img的标签，也就是包含图片的标签
    imgs = soup.findAll('img');
    for img in imgs:
        logging.info(img);
        match_flag = 0;
        # 既有‘src’又有‘original’属性的，一定是延迟加载的
        # 对于延迟加载的，需要去下载‘original’所指向的图片，
        # 然后再把‘src’指向所下载下来的图片
        if img.has_attr('src') and img.has_attr('original'):
            logging.info('Lazy load image.');
            # 对original进行正则匹配，看是否符合图片文件的规律
            matches = re.match((r'^(http://|https://|/)(.*\.)(%s)' % config.configs['picture_formats']), img['original']);
            # 匹配上了
            if matches is not None:
                # 链接是外部链接
                if re.match(r'^(http|https)', matches.group(1)):
                    logging.info('Image: Matches outer link.');
                    # 下载文件的url就是original
                    imgUrl = img['original'];
                # 链接是内部路径
                elif re.match(r'^/', matches.group(1)):
                    logging.info('Image: Matches local resouce');
                    # 需要将url添加到路径前面
                    imgUrl = url + img['original'];
                # 修改original属性，指向图片的位置
                img['original'] = './images/' + matches.group(2) + matches.group(3);
                match_flag = 1;
        elif img.has_attr('src'):
            logging.info('Normal image.');
            # 对src进行正则匹配
            matches = re.match((r'^(http://|https://|/)(.*\.)(%s)' % config.configs['picture_formats']), img['src']);
            # 匹配上了
            if matches is not None:
                # 若匹配的是外部链接
                if re.match(r'^(http|https)', matches.group(1)):
                    logging.info('Image: Matches outer link.');
                    imgUrl = img['src'];
                # 若匹配的是内部路径
                elif re.match(r'^/', matches.group(1)):
                    logging.info('Image: Matches local resouce');
                    imgUrl = url + img['src'];
                match_flag = 1;

        if match_flag == 1:
            # 获取图片所在地址内容
            imgContent = getUrl(imgUrl);
            # 保存图片
            imgPath = './images/' + matches.group(2) + matches.group(3);
            file_saver.saveFile(imgPath, imgContent);
            # 修改src属性
            img['src'] = imgPath;

    return soup;


# ===============================================================
# 下载CSS，同时将HTML中的路径替换成本地路径
# ===============================================================
def downloadCss(url, soup, file_saver):
    # 找到所有css文件所在的标签
    csss = soup.findAll('link', attrs={'type':'text/css'});
    for css in csss:
        logging.info(css);
        # 不知道css里面的地址是不是都是以href属性形式存在的
        # 但至少在m.sohu.com上都是这样的
        if css.has_attr('href'):
            logging.info('Got CSS.');
            # 匹配是否是CSS后缀文件
            matches = re.match(r'^(http://|https://|/)(.*\.)(css)', css['href']);
            if matches is not None:
                # CSS文件为外部链接
                if re.match(r'^(http|https)', matches.group(1)):
                    logging.info('CSS: Matches outer link');
                    cssUrl = css['href'];
                # CSS文件为内部路径
                elif re.match(r'^/', matches.group(1)):
                    logging.info('CSS: Matches local resouce');
                    cssUrl = url + css['href'];
                # 获取CSS文件
                cssContent = getUrl(cssUrl);
                # 保存CSS文件
                cssPath = './css/' + matches.group(2) + matches.group(3);
                file_saver.saveFile(cssPath, cssContent);
                # 改变CSS所指路径为本机路径
                css['href'] = cssPath;

    return soup;

# ===============================================================
# 下载JS，同时将HTML中的路径替换成本地路径
# ===============================================================
def downloadJavaScript(url, soup, file_saver):
    # 找到所有JavaScript所在的标签
    jss = soup.findAll('script', attrs={'type':'text/javascript'});
    for js in jss:
        logging.info(js);
        # 必须有src属性才是指向javascript源文件的内容
        if js.has_attr('src'):
            logging.info('Got JS.');
            # 匹配javascript文件
            matches = re.match(r'^(http://|https://|/)(.*\.)(js)', js['src']);
            if matches is not None:
                # 匹配到外部链接
                if re.match(r'^(http|https)', matches.group(1)):
                    logging.info('JS: Matches outer link');
                    jsUrl = js['src'];
                # 匹配到本地路径
                elif re.match(r'^/', matches.group(1)):
                    logging.info('JS: Matches local resouce');
                    jsUrl = url + js['src'];
                # 获取javascript内容
                jsContent = getUrl(jsUrl);
                # 保存javascript
                jsPath = './js/' + matches.group(2) + matches.group(3);
                file_saver.saveFile(jsPath, jsContent);
                # 将所指向的路径改为本机路径
                js['src'] = jsPath;

    return soup;

# ===============================================================
# 将超链接进行转换，以使得在本地打开的时候可以正常访问
# ===============================================================
def convertHyperLink(url, content):
    content = content.replace(r'href="/', (r'href="'+url+r'/'));
    content = content.replace(r'href="#"', (r'href="'+url+r'/#"'));
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
    soup = BeautifulSoup(getHTML(url), config.configs['bs4_parser']);
    # 下载图片并修改HTML
    soup = downloadImage(url, soup, file_saver);
    # 下载CSS并修改HTML
    soup = downloadCss(url, soup, file_saver);
    # 下载JS并修改HTML
    soup = downloadJavaScript(url, soup, file_saver);
    # 修改HTML中的指向本地服务器的超链接
    html_content = convertHyperLink(url, soup.prettify());
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
