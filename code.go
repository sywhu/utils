package main

import (
	"flag"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/axgle/mahonia"
)

var (
	root       = flag.String("d", "", "转化字符串的目录 必须")
	srcCode    = flag.String("s", "", "转换的原字符编码 必须")
	tagCode    = flag.String("t", "utf8", "目标字符编码")
	suffixs    = flag.String("suffixs", "", "目标后缀名 多个, 分割如 html,txt")
	cover      = flag.Bool("cover", false, "--cover 会覆盖")
	suffixList []string
)

func init() {
	flag.Parse()
	if *root == "" || *srcCode == "" {
		log.Fatalln("请使用-h 查看帮助")
	}
	if *suffixs == "" {
		*suffixs = "txt,md,html,java"
	}

	suffixList = strings.Split(*suffixs, ",")
}

func main() {
	a := GetFiles(*root, suffixList)
	ConvertFiles(a, *srcCode, *tagCode)
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
		//判断是不是文件
		if !info.IsDir() {
			// 有没有传入后缀
			if suffixs != nil {
				// 循环查看是不是有对应的后缀
				for _, suffix := range suffixs {
					if ok, _ := filepath.Match("*."+suffix, info.Name()); ok {
						*fileList = append(*fileList, path)
					}
				}
			} else {
				//没有传直接添加
				*fileList = append(*fileList, path)
			}

		}
		return err
	}

	filepath.Walk(root, workfunc)
	return *fileList
}

//ConvertFiles 传入对应的路径列表进行字符编码转换
func ConvertFiles(files []string, srcCode, tagCode string) {
	for _, file := range files {
		data, _ := ioutil.ReadFile(file)
		log.Println(file)
		dest := ConvertToStr(data, srcCode, tagCode)
		// 覆盖获取文件名 修改文件名
		if !*cover {
			index := strings.LastIndex(file, ".")
			if index != -1 {
				temp := file[:index] + "_" + tagCode
				suffix := file[index:]
				file = temp + suffix
			} else {
				file = file + "_" + tagCode
			}
		}
		// 写入文件
		err := ioutil.WriteFile(file, []byte(dest), 0644)
		if err != nil {
			log.Println("错误！", err.Error())
		} else {
			log.Println("成功转换", file)
		}
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
