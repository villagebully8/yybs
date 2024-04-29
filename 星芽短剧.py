#软件星芽短剧
#青龙变量xydj，抓取软件变量Authorization
from cgitb import text
import json
import time
import requests as r
import re
import os
import random

adv=1
if os.environ.get("xydj"):
    dvm = os.environ["xydj"]
    if dvm != '':
        if "@" in dvm:
            Coo = dvm.split("@")
        elif "&" in dvm:
            Coo = dvm.split('&')
        else:
            Coo = dvm.split('\n')
    adv=1
    for i in Coo:
        try:
            #个人信息
            xxurl = "https://app.whjzjx.cn/v1/account/detail"
            #签到
            signurl = "https://speciesweb.whjzjx.cn/v1/sign/do"
            #任务列表
            rwlburl = "https://speciesweb.whjzjx.cn/v1/task/list?device_id=252cf01c9b6793c92afb138cb390b5e65"
            #收藏
            scurl = "https://app.whjzjx.cn/v1/theater/doing_look_v2"
            #看广告
            adurl = "https://speciesweb.whjzjx.cn/v1/sign"
            #再看广告&签到看广告
            zkadurl = "https://speciesweb.whjzjx.cn/v1/task_ad/claim"
            #点赞
            dzurl = "https://speciesweb.whjzjx.cn/v1/task/like"
            #加观看时长
            gkscurl = "https://speciesweb.whjzjx.cn/v1/sign/escalation"
            #观看时长奖励领取
            gkjlurl = "https://speciesweb.whjzjx.cn/v1/sign/sign_multi_stage"
            #开宝箱
            kbxurl = "https://speciesweb.whjzjx.cn/v1/box/open"
            #开宝箱广告
            bxadurl = "https://speciesweb.whjzjx.cn/v1/box/view_ad"

            headers = {
                "content-length": "0",
                "pragma": "no-cache",
                "cache-control": "no-cache",
                "os_version": "7.1.2",
                "authorization": i,
                "device_brand": "Redmi",
                "device_platform": "android",
                "accept": "application/json, text/plain, */*",
                "user-agent": "Mozilla/5.0 (Linux; Android 7.1.2; M2012K11AC Build/N6F26Q; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.117 Mobile Safari/537.36 _dsbridge",
                "channel": "default",
                "user_agent": "Mozilla/5.0 (Linux; Android 7.1.2; M2012K11AC Build/N6F26Q; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.117 Mobile Safari/537.36 _dsbridge",
                "app_version": "2.3.0.1",
                "origin": "https://h5static.jzjxwh.cn",
                "x-requested-with": "com.jz.xydj",
                "sec-fetch-site": "cross-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "accept-encoding": "gzip, deflate",
                "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            # 各个任务的请求
            #查看CK是否有问题
            def denglu():
                global adv
                dl = r.get(xxurl, headers=headers)
                dll = json.loads(dl.text)
                if dll["msg"] == "成功":
                    name = dll["data"]["nickname"]
                    print(f'******开始【星芽免费短剧账号{adv}】{name} *********')
                    #获取账号金币数量现金数量
                    print("💰目前金币数量:"+str(dll["data"]["species"]))
                    print("💰可提现:"+str(dll["data"]["cash_remain"]))
                else:
                    print("登录失败，请重新获取Authorization")
                #    continue

            #签到
            def qiandao():
                qd = r.post(signurl, headers=headers)
                qdd = json.loads(qd.text)
                print("📅开始签到")
                if qdd["msg"] == "success":
                    print("✅签到成功获取金币:"+str(qdd["data"]["coin_val"]))
                    time.sleep(2)
                    signad()
                else:
                    print("❌签到失败原因:"+str(qdd["msg"]))

            def signad():
                # 广告body
                zkadbody = {"ad_type":4}
                zkad = r.post(zkadurl, headers=headers, json=zkadbody)
                zkkadd = json.loads(zkad.text)
                if zkkadd["code"] == "ok":
                    print("💱看签到广告成功获取金币:"+str(zkkadd["data"]["coin_val"]))
                else:
                    print("❌再看广告失败，原因:"+str(zkkadd["msg"]))

            #看广告
            def lookad():
                # 广告body
                adbody = {"type":4,"mark":2}
                ad = r.post(adurl, headers=headers, json=adbody)
                add = json.loads(ad.text)
                if add["msg"] == "签到成功":
                    print("💱看广告成功获取金币:"+str(add["data"]["species"]))
                else:
                    print("❌看广告失败原因:"+str(add["msg"]))

            #再看广告
            def looklookad():
                # 广告body
                zkadbody = {"ad_type":2}
                zkad = r.post(zkadurl, headers=headers, json=zkadbody)
                zkkadd = json.loads(zkad.text)
                if zkkadd["code"] == "ok":
                    print("💱再看广告成功获取金币:"+str(zkkadd["data"]["coin_val"]))
                else:
                    print("❌再看广告失败，原因:"+str(zkkadd["msg"]))

            #收藏请求
            def shoucang():
                # 随机数
                sjs = random.randint(1, 2000)
                # 收藏body
                scbody = {"kind": 2, "target_id": sjs, "category": 1, "is_auto_collect": False}
                sc = r.post(scurl, headers=headers, json=scbody)
                scc = json.loads(sc.text)
                if scc["msg"] == "成功":
                    print("✅收藏成功")
                else:
                    print("❌收藏失败")

            #点赞请求
            def dianzan():
                # 随机数
                sjs = random.randint(1, 116161)
                # 点赞body
                dzbody = {"theater_id": sjs}
                dz = r.post(dzurl, headers=headers, json=dzbody)
                dzz = json.loads(dz.text)
                if dzz["msg"] == "success":
                    print("💱点赞成功获取金币:"+str(dzz["data"]["info"]["coin_val"]))
                else:
                    print("❌点赞失败，原因:"+str(dzz["msg"]))

            #观看加时长
            def gksc():
                print("🆙观看加时长运行")
                for _ in range(10):
                    gkbody = {"type": 3}
                    gk = r.post(gkscurl, headers=headers, json=gkbody)
                    gkk = json.loads(gk.text)
                    if gkk["msg"] == "上报成功":
                        print("📈增加时长成功")
                        time.sleep(2)
                    else:
                        print("❌增加失败，原因:"+str(gkk["msg"]))
                        time.sleep(2)
                        lqbody = {"type":3,"makes":[1,2,3,4,5,6,7],"device_id":"87387123-7A4D-4B6A-912A-30CABD9CD4B3"}
                        lq = r.post(gkjlurl, headers=headers, json=lqbody)
                        lqq = json.loads(lq.text)
                        # print(lqq)
                        if lqq["msg"] == "签到成功":
                            print("💱领取观看时长金币成功:"+str(lqq["data"]["coin_value"]))
                        else:
                            print("❌领取观看时长金币失败，原因:"+str(lqq["msg"]))
                        break

            def adbox():
                print("📺观看宝箱广告1")
                bxadbody = {"config_id":3,"coin_val":72,"ad_num":2}
                bxad = r.post(bxadurl, headers=headers, json=bxadbody)
                bxadd = json.loads(bxad.text)
                if bxadd["msg"] == "success":
                    print("💰宝箱广告观看成功获得金币:"+str(bxadd["data"]["coin_val"]))
                else:
                    print("❌开宝箱失败，原因:"+str(bxadd["msg"]))

            def adbox2():
                print("📺观看宝箱广告2")
                bxadbody = {"config_id":3,"coin_val":72,"ad_num":1}
                bxad = r.post(bxadurl, headers=headers, json=bxadbody)
                bxadd = json.loads(bxad.text)
                if bxadd["msg"] == "success":
                    print("💰宝箱广告观看成功获得金币:"+str(bxadd["data"]["coin_val"]))
                else:
                    print("❌开宝箱失败，原因:"+str(bxadd["msg"]))

            #开宝箱
            def openbox():
                print("🆙观看加时长运行")
                time.sleep(2)
                for _ in range(10):
                    boxbody = {"config_id":3}
                    box = r.post(kbxurl, headers=headers, json=boxbody)
                    boxx = json.loads(box.text)
                    if boxx["msg"] == "success":
                        print("🗳️开宝箱成功获得金币:"+str(boxx["data"]["coin_val"]))
                        time.sleep(2)
                        adbox()
                        time.sleep(2)
                        adbox2()
                        time.sleep(2)
                    else:
                        print("❌开宝箱失败，原因:"+str(boxx["msg"]))
                        break



            #主程序       
            #登录
            denglu()
            adv=adv+1
            #等待
            time.sleep(2)
            #签到
            qiandao()
            #观看加时长
            gksc()
            #开宝箱
            openbox()
            #等待
            time.sleep(2)
            print("📊查看任务列表")
            # 获取任务列表
            class Task:
                def __init__(self, code, num, total):
                    self.code = code
                    self.num = num
                    self.total = total

                def is_completed(self):
                    if self.total is not None and self.num >= self.total:
                        return True
                    elif self.total is None:
                        return True
                    else:
                        return False

            # 用请求获取任务列表
            rwlb = r.get(rwlburl, headers=headers)
            rwlbb = json.loads(rwlb.text)
            task_list_data = rwlbb['data']['task_list']

            # 创建任务列表
            tasks = []

            # 填充任务列表
            for task_data in task_list_data:
                code = task_data['code']
                ext_data = task_data.get('ext')

                if ext_data is not None:
                    num = ext_data.get('num', 0)
                    total = ext_data.get('total')
                else:
                    num = 0
                    total = None

                task = Task(code, num, total)
                tasks.append(task)

            # 生成任务描述
            for task in tasks:
                if task.is_completed():
                    #print(f"{task.code} 任务已完成。")
                    # 在这里可以添加相应的任务完成后的操作
                    if task.code == '1030':
                        print(f"🆗收藏新剧任务已完成！({task.num}/{task.total})")
                    elif task.code == '1060':
                        print(f"🆗看视频金币任务已完成！({task.num}/{task.total})")
                    elif task.code == '1080':
                        print(f"🆗点赞剧集任务已完成！({task.num}/{task.total})")
                    elif task.code == '1070':
                        print(f"🆗分享短剧任务已完成！({task.num}/{task.total})")
                else:
                    if task.code == '1030':
                        print(f"收藏新剧({task.num}/{task.total})")
                        print("🔛任务没完成开始收藏新剧")
                        time.sleep(2)
                        for _ in range(task.total - task.num):
                            shoucang()
                            time.sleep(2)
                    elif task.code == '1060':
                        print(f"看视频金币({task.num}/{task.total})")
                        print("🔛任务没完成开始看广告")
                        time.sleep(2)
                        for _ in range(task.total - task.num):
                            lookad()
                            time.sleep(2)
                            looklookad()
                            time.sleep(2)
                    elif task.code == '1080':
                        print(f"点赞剧集({task.num}/{task.total})")
                        time.sleep(2)
                        for _ in range(task.total - task.num):
                            dianzan()
                            time.sleep(2)
                    elif task.code == '1070':
                        print(f"分享短剧({task.num}/{task.total})")
                    else:
                        print(f"{task.code} 任务描述未指定。")
        except:
                print("⚠️⚠️⚠️脚本报错执行下一个账号⚠️⚠️⚠️")