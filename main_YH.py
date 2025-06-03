import os
import requests
import re
from bs4 import BeautifulSoup
import logging

# 配置日志记录器
logging.basicConfig(filename='update.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', encoding='utf-8')

# 定义接口相关的URL
INTERFACE_URL = "https://smtapi.smtoem.cn/updateFlie/Autoupdater.xml"
INSTALL_PACKAGE_URL = "https://smtapi.smtoem.cn/updateFlie/羽华SMT快速编程系统NetworkSetup.exe"
INCREMENTAL_UPDATE_URL = "https://smtapi.smtoem.cn/updateFlie/update.zip"
LOG_FILE_URL = "https://smtapi.smtoem.cn/updateFlie/update.html"
BASE_URL = "https://smtapi.smtoem.cn/updateFlie/"

def get_latest_version_from_interface():
    """从接口获取最新版本号"""
    retries = 3
    for i in range(retries):
        try:
            response = requests.get(INTERFACE_URL, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml-xml')
            return soup.find('version').text
        except requests.exceptions.RequestException as e:
            logging.warning(f"从接口获取版本号时出错: {str(e)}， 重试 {i+1}/{retries} 次")
    logging.error(f"从接口获取版本号失败，重试 {retries} 次后仍未成功")
    print(f"从接口获取版本号失败，重试 {retries} 次后仍未成功")
    return None

def get_local_versions():
    """获取本地已存在的版本号列表（从已有的版本文件夹名称中提取）"""
    local_versions = []
    for folder in os.listdir('.'):
        if folder.startswith('版本-'):
            version = folder.replace('版本-', '')
            local_versions.append(version)
    return local_versions

def download_file(url, save_path, base_url=None):
    """下载文件并显示进度，支持处理 HTML 的相对路径补全"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        if base_url and save_path.endswith('.htm'):
            # 如果是 HTML 文件，解析并补全相对路径
            soup = BeautifulSoup(response.content, 'lxml')
            for tag in soup.find_all(['img', 'link', 'script']):
                attr = 'src' if tag.name in ['img', 'script'] else 'href'
                if tag.get(attr) and not re.match(r'^https?://', tag[attr]):
                    tag[attr] = requests.compat.urljoin(base_url, tag[attr])
            # 将补全后的 HTML 保存
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
        else:
            # 普通文件下载
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            with open(save_path, 'wb') as f:
                for data in response.iter_content(chunk_size=1024):
                    downloaded_size += len(data)
                    f.write(data)
                    progress = int(downloaded_size / total_size * 100)
                    print(f"下载进度: {progress}%", end='\r')
            print()
    except requests.exceptions.RequestException as e:
        logging.error(f"下载文件 {save_path} 时出错: {str(e)}")
        print(f"下载文件时出错: {str(e)}")

def parse_version(version_str):
    """将版本号字符串转为整数列表，便于比较"""
    return [int(x) for x in version_str.split('.')]

def compare_versions(v1, v2):
    """
    比较两个版本号字符串
    返回值: 1 表示v1>v2, -1 表示v1<v2, 0 表示相等
    """
    parts1 = parse_version(v1)
    parts2 = parse_version(v2)
    # 补齐位数
    maxlen = max(len(parts1), len(parts2))
    parts1 += [0] * (maxlen - len(parts1))
    parts2 += [0] * (maxlen - len(parts2))
    for a, b in zip(parts1, parts2):
        if a > b:
            return 1
        elif a < b:
            return -1
    return 0

def update_software():
    """检查并更新软件"""
    # 从接口获取最新版本号
    latest_version_interface = get_latest_version_from_interface()
    if not latest_version_interface:
        return

    # 获取本地已有的版本号列表
    local_versions = get_local_versions()
    if not local_versions:
        # 如果本地没有任何版本文件夹，直接下载并创建文件夹
        version_folder = f"版本-{latest_version_interface}"
        os.makedirs(version_folder, exist_ok=True)

        # 下载安装包、增量更新包和日志文件到版本文件夹
        install_package_path = os.path.join(version_folder, "羽华SMT快速编程系统NetworkSetup.exe")
        incremental_update_path = os.path.join(version_folder, "update.zip")
        log_path_folder = os.path.join(version_folder, "UpdateLogv5.0.htm")
        download_file(INSTALL_PACKAGE_URL, install_package_path)
        download_file(INCREMENTAL_UPDATE_URL, incremental_update_path)
        download_file(LOG_FILE_URL, log_path_folder, base_url=BASE_URL)
        logging.info("首次下载软件相关文件，爬取完成。 %s", latest_version_interface)
        return

    # 对比接口获取的版本号和本地最大版本号
    local_versions.sort(key=lambda x: parse_version(x), reverse=True)
    local_max_version = local_versions[0]
    cmp_result = compare_versions(latest_version_interface, local_max_version)
    if cmp_result > 0:
        # 如果接口版本号更大，创建新版本文件夹并下载文件
        version_folder = f"版本-{latest_version_interface}"
        os.makedirs(version_folder, exist_ok=True)
        install_package_path = os.path.join(version_folder, "羽华SMT快速编程系统NetworkSetup.exe")
        incremental_update_path = os.path.join(version_folder, "update.zip")
        log_path_folder = os.path.join(version_folder, "UpdateLogv5.0.htm")
        download_file(INSTALL_PACKAGE_URL, install_package_path)
        download_file(INCREMENTAL_UPDATE_URL, incremental_update_path)
        download_file(LOG_FILE_URL, log_path_folder, base_url=BASE_URL)
        logging.info("软件有更新，已完成爬取操作。 %s", latest_version_interface)
    else:
        logging.info("软件已是最新版本，无需爬取。 %s", local_max_version)


if __name__ == "__main__":
    update_software()
