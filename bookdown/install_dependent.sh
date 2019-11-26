#!/bin/sh

Get_Dist_Name()
{
    if grep -Eqii "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
        DISTRO='CentOS'
        PM='yum'
    elif grep -Eqi "Red Hat Enterprise Linux Server" /etc/issue || grep -Eq "Red Hat Enterprise Linux Server" /etc/*-release; then
        DISTRO='RHEL'
        PM='yum'
    elif grep -Eqi "Aliyun" /etc/issue || grep -Eq "Aliyun" /etc/*-release; then
        DISTRO='Aliyun'
        PM='yum'
    elif grep -Eqi "Fedora" /etc/issue || grep -Eq "Fedora" /etc/*-release; then
        DISTRO='Fedora'
        PM='yum'
    elif grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
        DISTRO='Debian'
        PM='apt'
    elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
        DISTRO='Ubuntu'
        PM='apt'
    elif grep -Eqi "Raspbian" /etc/issue || grep -Eq "Raspbian" /etc/*-release; then
        DISTRO='Raspbian'
        PM='apt'
    else
        DISTRO='unknow'
    fi
    echo $PM;
}

install_python()
{
    if [ $pm -z  ]; then 
        printf "没有你的Linux 发行版本 请手动安装 python3 再试试吧 \n"
        exit 1
    fi
    $pm install python3 -y
}

install_dep(){
    pip3 install lxml requests BeautifulSoup4 aiohttp
}

install() 
{
    case $1 in
    "python")
        install_python
        ;;

    "dep")
        install_dep
        ;;
    * )
        install_python
        install_dep
    esac

}

pm=`Get_Dist_Name`


version=`python -V | awk '{print $2}' `
if expr "$version" : '^3'
then 
    install dep
else 
    install
fi