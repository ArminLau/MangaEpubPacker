import os
import re
import datetime
import time
from uuid import UUID
import zipfile
import imagesize
from http.server import SimpleHTTPRequestHandler
import socketserver
import io,shutil
import logging
import json

#配置日志
logging.basicConfig(filename="./logs/manga_epub_packer.log", format='%(asctime)s - %(name)s - %(levelname)s -%(module)s:  %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S ',
                    level=logging.DEBUG)
logger = logging.getLogger()
console_handler = logging.StreamHandler() #日志同时输出到控制台
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

def validate_value(value):
    if value is None or len(value) < 1:
        return False
    else:
        return True

def set_default_value_if_not_set(value, default_value):
    if value is None or len(value) < 1:
        return default_value
    else:
        return value

class Template:
    def __init__(self, template_dir):
        self.target_dir = template_dir
        if not os.path.exists(self.target_dir):
            logger.error(f"存放epub模板文件的目录不存在，请检查程序包目录是否完整，程序初始化失败\n"
                         f"Directory for epub templates does not exit, failed to init program\n")
            raise Exception(f"Directory for templates does not exist")
        self.file_list = os.listdir(self.target_dir)
        require_templates = ['container.xml', 'content.opf', 'page.xhtml', 'mimetype', 'toc.ncx', 'nav.xhtml', 'style.css'] #必要的模板文件
        for template in require_templates:
            if template not in self.file_list:
                logging.error(f"缺失模板文件{template}, 程序初始化失败\n"
                              f"Template{template} does not exist, failed to init program\n")
        logging.debug(f"Template object init successfully")

    def read_template(self, template_name:str):
        template = ""
        with open(file=self.target_dir + os.path.sep + template_name, encoding="utf-8") as file:
            for line in file:
                template = template + line
        return template

    def get_container_xml_template(self):
        return self.read_template("container.xml")

    def get_content_opf_template(self):
        return self.read_template("content.opf")

    def get_mimetype_template(self):
        return self.read_template("mimetype")

    def get_nav_xhtml_template(self):
        return self.read_template("nav.xhtml")

    def get_page_xhtml_template(self):
        return self.read_template("page.xhtml")

    def get_toc_ncx_template(self):
        return self.read_template("toc.ncx")

    def get_style_css_template(self):
        return self.read_template("style.css")

class ComicInfo:
    def __init__(self, data:dict):
        logging.debug(f"receive comic json data from browser: {data}")
        self.path = data.get("path")
        self.bulk = data.get("bulk")
        self.overwrite = data.get("overwrite")
        if not validate_value(self.path):
            logging.error("没有指定图片的源目录，打包终止\n"
                  "Source path of manga images is not set, stop packing\n")
            raise Exception("Source path of manga images is not set")
        if not self.bulk:
            self.title = data.get("meta_info").get("title")
            if not validate_value(self.title):
                logging.error("非批量模式下没有指定书名，打包终止\n"
                      "Bookname is not set under Non-bulk mode, stop packing\n")
                raise RuntimeError("Bookname is not set under Non-bulk mode")
            self.filename = data.get("meta_info").get("filename")
            self.filename = set_default_value_if_not_set(self.filename, self.title)
            self.meta_info = data.get("meta_info")
            self.toc_info = data.get("toc_info")
        self.target_path = data.get("targetPath")
        self.target_path = set_default_value_if_not_set(self.target_path, self.path)
        logging.info(f"用户指定的源目录是:{self.path}, epub文件生成目录是:{self.target_path}\n"
                     f"Source path is {self.path} and target path for epub file is {self.target_path}\n")
        self.landmarks = ["cover", "toc", "bodymatter", "colophon"]
        logging.debug(f"ComicInfo object init success")

    def get_nav_contents_list(self):
        nav_list = list()
        for key,value in self.toc_info.items():
            type = value.get("type")
            if str(type) not in self.landmarks:
                temp = list()
                temp.append(key)
                temp.append(value.get("title"))
                nav_list.append(temp)
        return nav_list

    def get_nav_guide_dict(self):
        target_types = ["cover", "toc", "bodymatter", "colophon"]
        guide_dict = dict()
        for key,value in self.toc_info.items():
            type = value.get("type")
            if str(type) in target_types:
                guide_dict[type] = key
        return guide_dict

    def get_cover_image_index(self):
        return self.get_nav_guide_dict().get("cover")

class Packer:
    def __init__(self, ComicInfo, Template):
        self.path = ComicInfo.path
        self.target_path = ComicInfo.target_path
        self.is_bulk = ComicInfo.bulk
        self.is_overwrite = ComicInfo.overwrite
        for path in [self.path, self.target_path]:
            if not os.path.exists(path):
                logging.error(f"指定的目录{path}不存在，打包失败，请重试\n"
                              f"Specified source path:{path} does not exist, failed to pack, please try again\n")
                raise Exception(f"Specified source path {path} does not exist")
        self.template = Template
        self.cover_index = ""
        if not self.is_bulk:
            self.title = ComicInfo.title
            self.filename = f"{ComicInfo.filename}.epub"
            self.comicInfo = ComicInfo
        logging.debug(f"Packer object init success")

    #获取某个目录下所有图片的信息，返回的数据结构是列表: [[图片名称不带文件拓展符,文件拓展符,图片宽度,图片高度],例如图片000.jpg:["000","jpg",1100,1500]]
    def get_images_info(self, path:str, images:list):
        images_info = list()
        for image in images:
            temp = list()
            image_name_prefix, image_name_postfix = str(image).split(".")
            temp.append(image_name_prefix)
            temp.append(image_name_postfix)
            width, height = imagesize.get(path + os.sep + image)
            temp.append(width)
            temp.append(height)
            images_info.append(temp)
        return images_info

    def close(self):
        self.epubFile.close()

    def create_container_xml(self):
        self.epubFile.writestr('META-INF/container.xml', self.template.get_container_xml_template(),
                               compress_type=zipfile.ZIP_STORED)
        logging.debug(f"Sucessful to create container.xml")

    def create_mimetype(self):
        self.epubFile.writestr('mimetype', self.template.get_mimetype_template(), compress_type=zipfile.ZIP_STORED)
        logging.debug(f"Sucessful to create mimetype")

    def write_image(self, source_path, images):
        for image in images:
            self.epubFile.write(source_path+os.sep+image, "OEBPS/Images/"+image, compress_type=zipfile.ZIP_STORED)
        logging.debug(f"Sucessful to write images under source path{source_path}")

    def get_index_str(self, num:int):
        zero_num = 0
        if num < 10:
            zero_num = 2
        elif num < 100:
            zero_num = 1
        return "0"*zero_num+str(num)

    def create_content_opf(self, title, images_info, mange_identifier):
        context = str(self.template.get_content_opf_template())
        default_date = time.strftime("%Y-%m-%d")
        dcterms_modified = '{:%Y-%m-%dT%H:%M:%SZ}'.format(datetime.datetime.utcnow())
        default_value = "default"
        if not self.is_bulk: #非批量模式下才会处理书籍的基本信息
            cover_image_index = self.comicInfo.get_cover_image_index()
            if not validate_value(cover_image_index):
                cover_image_index = images_info[0][0]
            context = context.replace("$[cover_index]", cover_image_index)
            for key,value in self.comicInfo.meta_info.items():
                if len(value) > 0:
                    if key == "subject": #subject做特殊处理，前端页面是以符号"|"做分隔，中英文没有区分
                        subjects = str(value).split("|")
                        value = ""
                        for subject in subjects:
                            value = value + f"<dc:subject>{subject}</dc:subject>\n"
                        value = value[12:-14] #裁剪掉多余的subject标签
                    context = context.replace("${"+key+"}", value)
                else:
                    if key == "date":
                        context = context.replace("${"+key+"}", default_date) #若出版日期的没有指定，默认使用打包时间
                    else:
                        context = context.replace("${"+key+"}", default_value)
        else:
            context = re.sub("\$\{([x00-xF]+)}",default_value,context) #批量模式下匹配所有的${变量}为空字符串
            context = context.replace("$[cover_index]", self.cover_index)
        context = context.replace("$[title]", title).replace("$[dcterms_modified]", dcterms_modified)
        context = context.replace("$[identifier]", mange_identifier)
        context = context.replace(f"<dc:date>{default_value}</dc:date>", f"<dc:date>{default_date}</dc:date>")
        count = 0
        items1 = ""
        items2 = ""
        items3 = ""
        for item in images_info:
            image_prefix, image_postfix = item[0:2]
            count = count + 1
            index = self.get_index_str(count)
            template1 = f"<item id=\"x_{index}\" href=\"Text/{image_prefix}.xhtml\" media-type=\"application/xhtml+xml\" properties=\"svg\"/>"
            template2_append = ""
            if count == 1:
                template2_append = " properties=\"cover-image\""
            template2 = f"<item id=\"i_{index}\" href=\"Images/{image_prefix}.{image_postfix}\" media-type=\"image/{image_postfix}\"{template2_append}/>"
            template3 = f"<itemref idref=\"x_{index}\"/>"
            items1 = items1 + template1 + "\n"
            items2 = items2 + template2 + "\n"
            items3 = items3 + template3 + "\n"
        context = context.replace("$[items]", str(items1[0:-1]+items2[0:-1])).replace("$[itemrefs]",str(items3[0:-1]))
        self.epubFile.writestr('OEBPS/content.opf',context, compress_type=zipfile.ZIP_STORED)
        logging.debug(f"Sucessful to create content.opf")

    def create_image_page_xhtml(self, images_info, title):
        for item in images_info:
            image_prefix, image_postfix, image_width, image_heigh = item
            template = self.template.get_page_xhtml_template()
            template = str(template).replace("${title}", title).replace("${image_name_with_suffix}",str(image_prefix+"."+image_postfix)).replace("${imageWidth}",str(image_width)).replace("${imageHeight}",str(image_heigh))
            self.epubFile.writestr(f'OEBPS/Text/{image_prefix}.xhtml', template, compress_type=zipfile.ZIP_STORED)
        logging.debug(f"Sucessful to create image_page.xhtml")

    def create_style_css(self):
        self.epubFile.writestr('OEBPS/Styles/style.css', self.template.get_style_css_template(), compress_type=zipfile.ZIP_STORED)
        logging.debug(f"Sucessful to create style.css")

    def create_nav_xhtml(self, title):
        template = str(self.template.get_nav_xhtml_template()).replace("${title}",title)
        catalog_items_template = "<li><a href=\"Text/${image_index}.xhtml\">${toc_title}</a></li>"
        catalog_items = ""
        if (not self.is_bulk) and len(list(self.comicInfo.toc_info.keys())[0]) > 0: #确保包含有效的目录信息
            toc_info = self.comicInfo.toc_info
            toc_list = list(toc_info.keys())
            toc_list.sort()
            for toc in toc_list:
                catalog_items = catalog_items + (catalog_items_template.replace("${image_index}", toc).replace("${toc_title}", toc_info.get(toc).get("title")) + "\n")
        if len(catalog_items) == 0:
            catalog_items = catalog_items_template.replace("${image_index}", self.cover_index).replace("${toc_title}", "封面") + "\n"
        template = template.replace("${catalog_items}", catalog_items)
        self.epubFile.writestr(f'OEBPS/nav.xhtml', template, compress_type=zipfile.ZIP_STORED)
        logging.debug(f"Sucessful to create nav.xhtml")

    def create_toc_ncx(self, title, mange_identifier):
        template = str(self.template.get_toc_ncx_template()).replace("${title}", title).replace("${uuid}", mange_identifier)
        author = ""
        nav_points = ""
        nav_point_template = "<navPoint id=\"navPoint-${count}\" playOrder=\"${count}\">\n" + \
                             "<navLabel>\n" + \
                             "<text>${toc_title}</text>\n" + \
                             "</navLabel>\n" + \
                             "<content src=\"Text/${image_index}.xhtml\"/>\n" + \
                             "</navPoint>\n"
        if not self.is_bulk:
            creator = self.comicInfo.meta_info.get("creator")
            if creator is not None and len(creator)> 0:
                author = creator
            toc_info = self.comicInfo.toc_info
            if len(toc_info) > 0:
                count = 0
                toc_list = list()
                for key in toc_info.keys():
                    if validate_value(key):
                        toc_list.append(key)
                toc_list.sort()  # 将目录信息根据图片文件名的顺序进行排序
                for toc in toc_list:
                    count = count+1
                    nav_points = nav_points+nav_point_template.replace("${count}", str(count))\
                        .replace("${toc_title}", toc_info.get(toc).get("title"))\
                        .replace("${image_index}", str(toc))
                nav_points = nav_points[0:-1] #去除最后一个换行符
        if len(nav_points) == 0:
            nav_points = nav_point_template.replace("${count}", "1").replace("${toc_title}", "封面").replace("${image_index}", self.cover_index)
        template = template.replace("${navPoints}", nav_points).replace("${author}", author)
        self.epubFile.writestr(f'OEBPS/toc.ncx', template, compress_type=zipfile.ZIP_STORED)
        logging.debug(f"Sucessful to create toc.ncx")

    def pack_manga_ebup(self, source_path, target_path, title, filename):
        logging.info(f"Start pack manga: {filename}, source_path is {source_path}, target_path is {target_path}")
        mange_identifier = str(UUID(bytes=os.urandom(16), version=4)) #生成默认的书籍identifier
        if not self.is_bulk:
            define_identifier = self.comicInfo.meta_info.get("identifier")
            if define_identifier is not None and len(define_identifier) > 0:
                mange_identifier = define_identifier
        if filename is None:
            filename = title
        os.chdir(target_path)
        if os.path.exists(filename) and self.is_overwrite is False:
            raise RuntimeError(f"{filename} has been existed under path:{target_path}, stop packing")
        self.epubFile = zipfile.ZipFile(filename, 'w')
        images = get_files_under_path(path=source_path, postfix_filter=["jpg", "png", "jpeg"], sort_by_name=True)
        logging.debug(f"Successful to get images {images} from path: {source_path}")
        if not validate_value(images):
            raise RuntimeError(f"there is no image under path: {source_path}, failed to pack")
        images_info = self.get_images_info(path=source_path, images=images)
        if self.is_bulk or self.comicInfo.get_cover_image_index() is None:
            self.cover_index = images_info[0][0] #批量模式下或者目录信息缺失的情况下，设定第一页为封面页
        self.create_mimetype()
        self.create_container_xml()
        self.create_style_css()
        self.create_image_page_xhtml(images_info=images_info, title=title)
        self.create_content_opf(title=title, images_info=images_info, mange_identifier=mange_identifier)
        #self.create_toc_ncx(title=title, mange_identifier=mange_identifier)
        self.create_nav_xhtml(title=title)
        self.write_image(source_path=source_path, images=images)
        self.close()

def get_file_postfix(filename:str):
    postfix = ""
    if(len(filename) > 0):
        filename_array = filename.split(".")
        if len(filename_array) > 1:
            postfix = filename_array[len(filename_array) - 1]
    return postfix

def get_files_under_path(path, postfix_filter:list, sort_by_name=False):
    if not os.path.exists(path):
        return None
    files = list()
    for item in os.listdir(path):
        if os.path.isfile(path + os.sep + item) and (get_file_postfix(item) in postfix_filter):
            files.append(item)
    if sort_by_name:
        files.sort()
    return files

def get_dirs_under_path(path):
    if not os.path.exists(path):
        return None
    dirs = list()
    for item in os.listdir(path):
        if os.path.isdir(path + os.sep + item):
            dirs.append(item)
    return dirs

class EpubHandler(SimpleHTTPRequestHandler):
    def send_datas(self, contents):
        # 指定返回编码
        enc = "UTF-8"
        content = contents.encode(enc)
        f = io.BytesIO()
        f.write(content)
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(contents)))
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)

    def do_GET(self):
        logging.debug("Handle Get http request: " + str(self.path))
        if self.path == "/" :
            self.path = "/resources/static/index.html" #配置默认路径指向resources/static/index.html
        elif str(self.path).find("/static") != -1:
            self.path = "/resources" + self.path #映射static目录下的静态资源文件
        super(EpubHandler, self).do_GET()

    def do_POST(self):
        logging.debug("Handle Post http request: " + str(self.path))
        start_time = datetime.datetime.now()
        if (str(self.path).endswith("/pack")):
            #获取消息内容的长度
            context_length = self.headers['content-length']
            #根据消息内容长度读取字节并转化成字典类型
            datasets = json.loads(self.rfile.read(int(context_length)))
            bulk = datasets['bulk']
            mode = "single"
            if bulk:
                mode = "bulk"
            logging.info(f"Handle {mode} epub pack request")
            result = handle_ebup_request(datasets)
            flag = 0
            log_file = f"{os.getcwd() + os.sep}logs{os.sep}manga_epub_packer.log"
            #这里可以自定义消息的html风格，出错的信息标红显示
            msg = "<font color=\"red\">打包失败，请查看日志了解详情</font><br/>"
            success_count = 0
            if len(result) > 0:
                msg = ""
                for key,value in result.items():
                    if len(value) > 0:
                        msg = msg + f"成功打包漫画<strong>{key}</strong>, 存放路径:{value}<br/>"
                        success_count = success_count+1
                    else:
                        msg = msg +f"<font color=\"red\">打包漫画<strong>{key}</strong>时出现错误，请查看日志文件了解详情</font><br/>"
                if len(result) == success_count:
                    flag = 1
            if flag == 0:
                msg = msg + f"<font color=\"red\">日志文件存放路径: {log_file}</font><br/>"
            end_time = datetime.datetime.now()
            msg = msg + f"本次请求共耗费{datetime.timedelta.total_seconds(end_time - start_time)}秒" #统计响应本次Post请求花费的时长(秒)
            results = {"status": flag, "msg": msg}
            self.send_datas(json.dumps(results))

def handle_ebup_request(datasets):
    cwd_path = os.getcwd()
    pack_result = dict()
    is_bulk = datasets.get("bulk")
    try:
        template_obj = Template(cwd_path + os.sep + "resources" + os.sep + "template")
        comicinfo_obj = ComicInfo(datasets)
        epub_packer = Packer(ComicInfo=comicinfo_obj, Template=template_obj)
        if is_bulk:
            logging.info(f"Start to handle bulk epub pack")
            pack_result = handle_bulk_ebup(epub_packer=epub_packer)
        else:
            logging.info(f"Start to single bulk epub pack")
            handle_single_ebup(epub_packer=epub_packer)
            pack_result[epub_packer.title] = f"{epub_packer.target_path+os.sep+epub_packer.filename}"
    except Exception as e:
        logging.error(f"打包出错，相关的错误信息\n"
                      f"Failed to pack, error message that matter: {e}")
    finally:
        os.chdir(cwd_path)
        return pack_result

def handle_single_ebup(epub_packer):
    epub_packer.pack_manga_ebup(source_path=epub_packer.path, target_path=epub_packer.target_path,
                                filename=epub_packer.filename, title=epub_packer.title)
    target = epub_packer.target_path + os.sep + epub_packer.filename
    logging.info(f"成功打包生成epub文件: {target}\n"
                 f"Success to pack singe epub file: {target}\n")

def handle_bulk_ebup(epub_packer):
    pack_result = dict()
    source_path = epub_packer.path
    target_path = epub_packer.target_path
    target_dir = get_dirs_under_path(source_path)
    if len(target_dir) < 1:
        return pack_result
    cwd = os.getcwd()
    for dir in target_dir:
        filename = f"{dir}.epub"
        try:
            epub_packer.pack_manga_ebup(source_path=source_path + os.sep + dir, target_path=target_path,
                                        filename=filename, title=dir)
            pack_result[dir] = epub_packer.target_path + os.sep + filename
        except Exception as e:
            logging.error(f"打包漫画[{dir}]时出现异常\n"
                          f"Issue arises when packing manga [{dir}], error: {e}\n")
            pack_result[dir] = ""
            continue #某个目录打包出错时跳过该目录继续下个文件夹的打包
        finally:
            os.chdir(cwd)
    return pack_result

def start_server(server_port):
    server_host = 'localhost'
    httpd = socketserver.TCPServer((server_host, server_port), EpubHandler)
    logging.info(f"Epub打包服务器启动成功，请用浏览器访问以下链接:\n"
                f"EpubHandler server launchs successfully, please go to browser for accessing the following link:\n"
                 f"http://{server_host}:{server_port}\n"
                 f"访问成功后可以点击页面上的帮助信息(问号图标)阅读用户手册，如不能正常访问，请检查控制台输出信息\n"
                 f"After accessing web page, User Manuals can be obtained by clicking question icon in page; it is recommended to check console output information if it is not able to access web page\n")
    httpd.serve_forever()

if __name__ == "__main__":
    server_port = input("请输入服务器绑定的端口, 直接回车使用默认配置(8433)\n"
                        "Please select a spare port for program, with pressing enter button to use default port(8433): ")
    try:
        server_port = int(server_port)
    except:
        server_port = 8433
    start_server(server_port)


