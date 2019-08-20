from pathlib import Path
from argparse import ArgumentParser
import sys
# 小工具 转 字符编码


def list_file(path, files):
    ''' 获取需要的文件对象  '''
    if path.is_file():
        files.append(path)
        return
    for item in path.iterdir():
        if item.is_file() and not item.name.startswith("."):
            if item.suffix.lower() in [".txt", ".md", ".java", ".py", ".go", ".yml", ".config"]:
                files.append(item)
        elif item.is_dir():
            list_file(item, files)


def convert(files,old_encode):
    ''' 转化编码 '''
    for file in files:
        try:
            with file.open("r", 1024, encoding=old_encode) as f:
                text = f.read()
            with file.open("w", 1024, encoding="utf-8") as f:
                f.write(text)
        except:
            print(f"\033[31m 转换失败跳过：{file} \033[0m")
        else:
            print(f"\033[32m 转化成功：{file} \033[0m")

def main():
    # 初始化 参数解析器
    parser = ArgumentParser("code", description="批量转字符编码工具", epilog="v1")
    parser.add_argument("-d", dest="dir",
                        type=str, help="换的文件或者目录", required=True)

    parser.add_argument('-s',dest="old_encode",default="gbk",nargs="?",help="原子符编码")

    # 解析参数
    args = parser.parse_args()

    # 获取文件列表
    path = Path(args.dir)
    files = []
    list_file(path,files)

    # 开始转换
    convert(files,args.old_encode)

if __name__ == "__main__":
    main()