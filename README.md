# 简介
本脚本可用于按一定周期保存网页到指定目录。使用方法：

    python3 main.py -u <url> {-d <period>} {-o <directory>}

其中:

-u 选项是必须输入的，url所代表的是所要保存的网页的URL，如http://m.sohu.com 。如不输入该参数，程序运行可能会有问题。

-d 选项指定周期，period为周期，单位为秒，如输入60则表示每60进行一次保存。如果不输入该参数，则默认以60秒为周期运行

-o 选项指定路径，directory为路径，如输入/tmp/backup则会将文件保存至/tmp/backup文件夹下，如没有该文件夹程序会自动创建一个。如果不输入该参数，则默认保存到当前目录。

# 依赖关系
本脚本基于python3.4，并且依赖Beautifulsoup 4的HTML解析库。如果你已经正常安装了python3.4（或以上版本）以及pip3，那么你直接输入：

    pip3 install bs4

便可安装所需要的库来保证本脚本正常运行。

本脚本在Linux和Windows下均测试运行通过。

# 思路简介
1.下载HTML:

很简单，直接使用urllib的request功能即可。

2.下载图片、CSS、JS等：

首先，需要对HTML进行解析，找到图片、CSS、JS等资源所在的标签，然后对标签进行解析，获取图片、CSS、JS等所在的链接，然后用urllib的requesst获取这些资源，保存到所设定的路径下面。

随后，还需要做的事情就是将HTML中图片、CSS、JS等资源所指向的链接改为所保存到的路径下面，这样在离线打开的时候才可以正常显示这些资源。

3.修改指向本地服务器的超链接：

做完1、2两步之后，发现虽然网页可以打开，但是网页里面指向其他内容的链接全都不能打开了。所以接下来需要做的事情就是将原本指向本地服务器的超链接全部改成外部链接（指向你所下载的那个url的外部链接），然后网页内的超链接就都可以打开了。

4.定时运行：

为了让程序能够定时运行，本脚本使用了threading里面的Timer功能。调用Timer相当于创建了一个线程（仅为调试中发现的特点，不能保证是否正确）。那么就是说每隔一段时间所发起的保存网页的任务是有可能会并行发生的（因为没有办法确定保存网页所需要的时间）。所以为了保证并行程序可以正常运行，必须保证函数是可重入的。所以最后对之前的程序进行了一些修改以保证可重入性。

# 参考
本脚本参考了Chrome保存网页的功能，本脚本所保存的网页和Chrome保存网页功能所保存的网页在功能上几乎是一致的。（实现细节还是有所不同）
