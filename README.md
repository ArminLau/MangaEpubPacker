# MangaEpubPacker
### 用于漫画(杂志或者单行本)的Epub电子书打包脚本，处理逻辑用Python实现，GUI采用Web前端
### A script for manga epub packer, process logic is achieved with Python while GUI is realized by Web Front End

### 使用方法(Guidance)
#### 前期准备
本地有漫画的图片存放到一个目录下，目前仅支持jpg, png, jpeg三种格式的图片

#### 启动程序
场景一: 本地有Python环境

本脚本基于Python 3.8.9, Python3的环境应该都可以正常运行，拷贝整个工程目录到本地，进入目录MangaEpubPacker，检查requirements.txt中的第三方依赖本地是否已经安装，
检查命令`pip show 依赖包名`
假如没有安装，使用命令`pip install 依赖包名`
所需依赖都安装好后，执行以下命令启动程序:
* Windows: `python mangaEpubPacker.py`
* Linux: `python3 mangaEpubPacker.py`

场景二: 本地没有Python环境

假如没有或者不想安装Python环境，可以访问[MangaEpubPacker版本发布](https://github.com/ArminLau/MangaEpubPacker/releases "MangaEpubPacker版本发布")下载最新的windows版本(基于pyinstaller和win10环境打包的exe可执行程序)，再解压到某个目录下后，进入程序主目录，双击执行mangaEpubPacker.exe

#### 程序配置
启动程序后会进入控制台，指定一个可用的端口给程序的http服务器绑定(默认是8433)，如果不想自定义，直接回车即可
配置后控制台会返回一个http链接，拷贝该链接用浏览器访问(最好是谷歌浏览器)
![image](https://user-images.githubusercontent.com/51482567/212067617-b96c455c-7f15-43a0-86aa-50a137a7ef87.png)

#### Epub电子书编辑
进入Web页面后，可以点击英文标题旁边的？图标阅读使用指南，剩下的就交给前端页面吧
![image](https://user-images.githubusercontent.com/51482567/212068576-3341b6d7-c51a-4783-b6e8-f1f7e5203417.png)
需要补充的4点如下:
* 预设了四个默认目录选项: 封面，目录，正文起始页，版权页(若不想使用这些预设选项，切记不要给这些选项选择图片)
* 可以添加自定义的目录选项，先填写章节的标题，然后再给新增的选项选择图片，右侧有选择图片的预览
* 一旦刷新页面后，图片预览和表单选项都会清空，千万别手贱
* 批量模式下，用户需要按如下准备，每个子文件夹对应一个Epub文件，Epub文件的书籍标题和文件名采用对应的子文件夹的名字
![image](https://user-images.githubusercontent.com/51482567/212069411-8cb22acd-e241-4a02-815f-8958f799e40c.png)
