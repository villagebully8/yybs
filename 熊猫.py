#!/usr/bin/env python3
# coding: utf-8
'''

功能：熊猫代理任务
注册地址: http://www.xiongmaodaili.com?invitationCode=FE66C96A-C72F-48AC-819B-079152005E4F
账号#密码填到环境变量'xmdlck'里，多账号&连接

cron: 7 0 * * *
new Env('熊猫代理');
'''
import requests
import os
from requests_toolbelt.multipart.encoder import MultipartEncoder
try:
    from notify import send
except:
    pass

accounts = os.getenv('xmdlck')

if accounts is None:
    print('未检测到xmdlck')
    exit(1)

accounts_list = accounts.split('&')
print(f"获取到 {len(accounts_list)} 个账号\n")

urls = ["http://www.xiongmaodaili.com/xiongmao-web/user/login",
    "http://www.xiongmaodaili.com/xiongmao-web/points/getSignInDay",
    "http://www.xiongmaodaili.com/xiongmao-web/points/getSignInDayTime",
    "http://www.xiongmaodaili.com/xiongmao-web/points/receivePoints?signInDay=",
    "http://www.xiongmaodaili.com/xiongmao-web/points/getUserPoints",
]

headers = {
        "Host": "www.xiongmaodaili.com",
        "Proxy-Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.95 Safari/537.36",
        "Origin": "http://www.xiongmaodaili.com",
        "Referer": "http://www.xiongmaodaili.com/",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

result = []


for i, account in enumerate(accounts_list, start=1):
    print(f"=======开始执行账号{i}=======\n")
    params_list = account.split('#')
    if len(params_list) != 2:
        result.append(f"参数数量错误！跳过账号{i}！\n")
        continue


    encoded = MultipartEncoder(
        fields={"account": params_list[0], "password": params_list[1], "originType": "1"}
    )
    headers["Content-Type"] = encoded.content_type
    data = requests.post(
        urls[0],
        headers=headers,
        data=encoded,
        cookies={"invitationCode": "FE66C96A-C72F-48AC-819B-079152005E4F"},
        verify=False,
    )
    if data and data.json()["code"] == "0":
        cookies = data.cookies
        print(f"账号{i}登录成功！\n")
    else:
        result.append(f"账号{i}登录失败：{data}\n")
        continue


    headers["Content-Type"] = "application/json;charset=UTF-8"
    data = requests.get(
        urls[1],
        headers=headers,
        cookies=cookies,
        verify=False,
    )
    if data and data.json()["code"] == "0":
        if data.json()["obj"][0]["status"] == 1:
            result.append(f"账号{i}今日已签到！\n")
        elif data.json()["obj"][0]["status"] == 0:
            pass
        else:
            result.append(f"账号{i}查询签到详情失败：{data}\n")
            continue
    else:
        result.append(f"账号{i}查询签到详情失败：{data}\n")
        continue


    data = requests.get(
        urls[2],
        headers=headers,
        cookies=cookies,
        verify=False,
    )
    if data and data.json()["code"] == "0":
        pass
    else:
        result.append(f"账号{i}查询当前签到天数失败：{data}\n")
        continue


    data = requests.get(
        urls[3] + str(data.json()["obj"] + 1),
        headers=headers,
        cookies=cookies,
        verify=False,
    )
    if data and data.json()["msg"] == "领取成功！":
        result.append(f"账号{i}签到成功！\n")
    else:
        result.append(f"账号{i}签到失败：{data}\n")


    data = requests.get(
        urls[4],
        headers=headers,
        cookies=cookies,
        verify=False,
    )
    if data and data.json()["code"] == "0":
        result.append(f"当前积分：{data.json()['obj']}\n")
    else:
        result.append(f"账号{i}查询当前积分失败：{data}\n")

try:
    send("熊猫代理签到",f"{''.join(result)}")
except Exception as e:
    print(f"消息推送失败：{e}！\n{result}\n")
