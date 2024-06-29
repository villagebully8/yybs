"""
 * 丰信客户端
 * 设置变量 FX_TOKEN,多号使用&隔开，青龙直接新建变量即可
 * ck格式1:手机号#密码
 * cron 一天5-10次
"""

import hashlib
import os
import time
import requests

ck = ''

class FX:
    def __init__(self, cki):
        self.uid = None
        self.phone = cki.split('#')[0]
        self.password = cki.split('#')[1]
        self.task_name = None
        self.ck = None
        self.name = self.phone[:3] + '****' + self.phone[7:]
        self.id = None
        self.taskCode = None
        self.hd = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'plat': "1",
            'version': "3.1.0"
        }

    def login(self):
        url = "https://capp.phtion.com/api/applogin/sign-v2"
        payload = {
            "password": self.password,
            "phone": self.phone,
            "jpushId": "170976fa8b88b40765c",
            "plat": 1
        }
        self.hd['time'] = str(int(time.time() * 1000))
        self.hd['Content-Type'] = "application/json; charset=utf-8"
        r = requests.post(url, json=payload, headers=self.hd).json()
        if r['status'] == '200':
            self.ck = r['data']['yxUser']['token']
            self.uid = r['data']['yxUser']['uid']
            print(f"[{self.name}] 登录成功,积分余额--[{self.con(self.uid)}]")
            return True
        else:
            print(f"[{self.name}] 登录失败")
            return False

    def con(self, uid):
        url = "https://capp.phtion.com/api/account/getintegral"
        params = {
            'uid': uid
        }
        self.hd['token'] = self.ck
        try:
            r = requests.get(url, params=params, headers=self.hd).json()
            if r['status'] == '200':
                return r['data']['num']
            else:
                print(r)
                return 0
        except:
            return 0

    def signinfo(self):
        url = "https://capp.phtion.com/api/signlogin/get-check-day"
        timestamp = str(int(time.time() * 1000))
        sign_string = f'{timestamp}{self.uid}sKtXzNtqHeiaahROvJRLkITP'
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        self.hd['sign'] = sign
        self.hd['time'] = timestamp
        try:
            r = requests.post(url, headers=self.hd).json()
            if r['status'] == '200':
                if r['data']['data'] == 0:
                    self.sign()
        except:
            print(f'[{self.name}] --获取签到信息失败')

    def sign(self):
        url = "https://capp.phtion.com/api/sign/daily-sign"
        timestamp = str(int(time.time() * 1000))
        sign_string = f'{timestamp}{self.uid}sKtXzNtqHeiaahROvJRLkITP'
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        self.hd['sign'] = sign
        self.hd['time'] = timestamp
        self.hd['token'] = self.ck
        try:
            r = requests.get(url, headers=self.hd).json()
            if r['status'] == '200':
                print(f"[{self.name}] 签到成功--[{r['message']}]")
                self.sign1()
            else:
                print(f"[{self.name}] 签到失败--[{r['message']}]")
        except:
            print(f'[{self.name}] --签到失败')

    def sign1(self):
        timestamp = str(int(time.time() * 1000))
        sign_string = f'finishType0taskCode1010taskDetail1taskType任务奖励-签到翻倍{timestamp}{self.uid}sKtXzNtqHeiaahROvJRLkITP'
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        payload = f"taskDetail=1&taskType=%E4%BB%BB%E5%8A%A1%E5%A5%96%E5%8A%B1-%E7%AD%BE%E5%88%B0%E7%BF%BB%E5%80%8D&taskCode=1010&finishType=0"
        url = 'https://capp.phtion.com/api/task/add-task-rate'
        self.hd['sign'] = sign
        self.hd['time'] = timestamp
        self.hd['token'] = self.ck
        self.hd['Content-Type'] = "application/x-www-form-urlencoded"
        try:
            r = requests.post(url, headers=self.hd, data=payload).json()
            if r['status'] == '200':
                print(f"[{self.name}] 签到翻倍成功--[{r['message']}]")
            else:
                print(f"[{self.name}] 签到翻倍失败--[{r['message']}]")
        except:
            print(f"【{self.name}】 --完成签到翻倍失败")

    def task_list(self):
        try:
            url = "https://capp.phtion.com/api/task/all-current-task-detail-v2"
            self.hd['time'] = str(int(time.time() * 1000))
            self.hd['token'] = self.ck
            r = requests.get(url, headers=self.hd).json()
            if r['status'] == '200':
                task_list = [(item['id'], item['taskName'], item['taskCode']) for item in r['data'] if int(item['taskDetail']) < int(item['taskNum'])]
                for self.id, self.task_name, self.taskCode in task_list:
                    if self.task_name == "每日签到":
                        self.signinfo()
                    if self.task_name == "任务奖励-签到翻倍":
                        self.sign1()
                    elif self.task_name in ["看激励视频解锁", "看广告赚积分", "看广告赚积分", "看广告赚积分PLUS", "分享APP", "激励视频PLUS", "激励视频MAX"]:
                        self.task(None)
                        time.sleep(5)
                    elif self.task_name in ["迷你短剧场", "抖音短视频", "迷你短剧场PLUS", "抖音短视频PLUS", "浏览商品", "一起来猜歌", "玩游戏"]:
                        self.task(1)
                        time.sleep(5)
            else:
                print(f"【{self.name}】任务列表获取失败")
        except:
            print(f"【{self.name}】任务列表获取失败")

    def task(self, N):
        timestamp = str(int(time.time() * 1000))
        if N is not None:
            sign_string = f'finishType0taskCode{self.taskCode}taskDetail30{timestamp}{self.uid}sKtXzNtqHeiaahROvJRLkITP'
            payload = f"taskDetail=30&taskCode=" + self.taskCode + "&finishType=0"
        else:
            sign_string = f'finishType0taskCode{self.taskCode}taskDetail1taskId{self.id}' + timestamp + f'{self.uid}sKtXzNtqHeiaahROvJRLkITP'
            payload = f"taskDetail=1&taskCode={self.taskCode}&taskId={self.id}&finishType=0"
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        url = 'https://capp.phtion.com/api/task/add-task-rate'
        self.hd['sign'] = sign
        self.hd['time'] = timestamp
        self.hd['token'] = self.ck
        self.hd['Content-Type'] = "application/x-www-form-urlencoded"
        try:
            r = requests.post(url, headers=self.hd, data=payload).json()
            if r['status'] == '200':
                print(f"[{self.name}] 完成任务[{self.task_name}]成功 --[{r['message']}]")
            else:
                print(f"[{self.name}] 完成任务[{self.task_name}失败 --[{r['message']}]")
        except:
            print(f"【{self.name}】任务失败")

    def start(self):
        try:
            if self.login():
                self.task_list()
        except:
            print(f"【{self.name}】任务失败")

if __name__ == '__main__':
    if 'FX_TOKEN' in os.environ:
        cookie = os.environ.get('FX_TOKEN')
    else:
        print("环境变量中不存在[FX_TOKEN],启用本地变量模式")
        cookie = ck
    if cookie == "":
        print("本地变量为空，请设置其中一个变量后再运行")
        exit(-1)
    cookies = cookie.split("&")
    print(f"丰信客户端共获取到 {len(cookies)} 个账号")
    for i, ck in enumerate(cookies):
        print(f"======开始第{i + 1}个账号======")
        FX(ck).start()
        print("2s后进行下一个账号")
        time.sleep(2)