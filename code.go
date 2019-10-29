package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/axgle/mahonia"
)

var (
	root       = flag.String("d", "", "转化字符串的目录或者文件 必须")
	srcCode    = flag.String("s", "", "转换的原字符编码 必须")
	tagCode    = flag.String("t", "utf8", "目标字符编码")
	suffixs    = flag.String("suffixs", "txt,md,html,java", "目标后缀名 多个, 分割如 html,txt")
	cover      = flag.Bool("cover", false, "--cover 会覆盖")
	clear      = flag.Bool("c", false, "-c 清理编码文件")
	suffixList []string
)

func init() {
	flag.Parse()

	if *root == "" {
		flag.Usage()
		log.Fatalln("目录或者文件不能为空")
	}

	if !*clear && (*srcCode == "") {
		flag.Usage()
		log.Fatalln("不清理时 需要一个原字符编码")
	}

	if *clear && *cover {
		log.Fatalln("不能同时清理 并且覆盖 会删除原始文件的！！！")
	}

	suffixList = strings.Split(*suffixs, ",")
	for i, suffix := range suffixList {
		suffixList[i] = "*." + suffix
	}
}

func main() {
	a := GetFiles(*root, suffixList)
	if *clear {
		removeFile(a, *tagCode)
	} else {
		ConvertFiles(a, *srcCode, *tagCode)
	}
}

func addFile(info os.FileInfo, path string, suffixs []string, fileList *[]string) {
	//判断是不是文件
	if !info.IsDir() {
		index := len(info.Name()) - (len(*tagCode) + 1)

		stop := strings.LastIndex(info.Name(), ".")
		// 判断是不是自己生成的文件 并且不是隐藏文件
		if !(index > 0 && index < stop && info.Name()[index:stop] == "_"+*tagCode) && !(info.Name()[0:1] == ".") {
			// 有没有传入后缀
			if suffixs != nil {
				// 循环查看是不是有对应的后缀
				for _, suffix := range suffixs {
					if ok, _ := filepath.Match(suffix, info.Name()); ok {
						*fileList = append(*fileList, path)
					}
				}
			} else {
				//没有传直接添加
				*fileList = append(*fileList, path)
			}
		}

	}

}

//GetFiles 获取需要的文件 返回路径列表
func GetFiles(root string, suffixs []string) []string {

	log.Println("开始获取文件....")
	fileList := &[]string{}
	if info, _ := os.Stat(root); !info.IsDir() {
		*fileList = append(*fileList, root)
		return *fileList
	}
	// 获取需要的文件
	workfunc := func(path string, info os.FileInfo, err error) error {
		addFile(info, path, suffixs, fileList)
		return err
	}

	filepath.Walk(root, workfunc)
	return *fileList
}

func rename(file string, tagCode string) string {
	index := strings.LastIndex(file, ".")
	if index != -1 {
		temp := file[:index] + "_" + tagCode
		suffix := file[index:]
		file = temp + suffix
	} else {
		file = file + "_" + tagCode
	}
	return file
}

func readFile(file string) []byte {
	data, err := ioutil.ReadFile(file)
	if err != nil {
		log.Println("错误了:", err.Error())
	}
	return data
}

func writeFile(file string, data string) {
	err := ioutil.WriteFile(file, []byte(data), 0644)
	if err != nil {
		log.Println("错误！", err.Error())
	}
}

func removeFile(files []string, tagCode string) {
	allnum := len(files)
	for i, file := range files {
		file := rename(file, tagCode)
		os.Remove(file)
		fmt.Printf("\r当前进度 (%v,%v)", i+1, allnum)

	}

}

//ConvertFiles 传入对应的路径列表进行字符编码转换
func ConvertFiles(files []string, srcCode, tagCode string) {
	allnum := len(files)
	for i, file := range files {
		data := readFile(file)
		dest := ConvertToStr(data, srcCode, tagCode)
		// 覆盖获取文件名 修改文件名
		if !*cover {
			file = rename(file, tagCode)
		}
		// 写入文件
		writeFile(file, dest)
		fmt.Printf("\r当前进度 (%v,%v)", i+1, allnum)
	}
}

//ConvertToStr 转成指定的字符编码
func ConvertToStr(src []byte, srcCode, tagCode string) string {
	srcCoder := mahonia.NewDecoder(srcCode)
	_, data, err := srcCoder.Translate(src, true)
	if err != nil {
		log.Println("失败了")
		return string(src)
	}
	tagCoder := mahonia.NewEncoder(tagCode)
	dest := tagCoder.ConvertString(string(data))
	return dest
}
