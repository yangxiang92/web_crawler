# 简介
本脚本可用于按一定周期保存网页到指定目录。使用方法：

python3 main.py -u <url> {-d <period>} {-o <directory>}

其中:
    -u 选项是必须输入的，<url>所代表的是所要保存的网页的URL，如http://m.sohu.com。如不输入该参数，程序运行可能会有问题。
    -d 选项指定周期，<period>为周期，单位为秒，如输入60则表示每60进行一次保存。
    -o 选项指定路径，<directory>为路径，如/tmp/backup则会将文件保存至/tmp/backup文件夹下，如没有该文件夹程序会自动创建一个。

# 依赖关系
本脚本基于python3.4，并且依赖Beautifulsoup 4的HTML解析库。如果你已经正常安装了python3.4（或以上版本）以及pip3，那么你直接输入：
    pip3 install bs4
便可安装所需要的库来保证本脚本正常运行。

# 思路简介
