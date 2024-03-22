# 软件:建行生活
# 活动信息: 奋斗季cc豆 功能：每日营收，签到 浏览任务，答题，抽奖，专区任务
# 先开抓包，先开抓包，进建行生活app，没抓到等两小时在抓
# https://yunbusiness.ccb.com/basic_service/txCtrl?  请求头中token值，deviceid值。请求体meb_id或者userid值
# 专区任务，专区抓fission-events.ccbft.com，全部cookie,或者cookie里面_ck_bbq_224的 键和值  已去除，不需要了
# 格式 ccdck =  deviceid值#meb_id值#手机号#token值
# 定时：0 0 8,9 * * *
# 注: 此脚本仅限个人使用,不得传播
# 作者: 洋洋不瘦
# 更新 1.19
# 修复专区,去除专区cookie值
import os
import random
import json
import re
from urllib.parse import quote
import time
from os import path
from datetime import datetime
import requests
import hashlib

'''
doll_flag  1开启抓娃娃，0关闭
doll_draw 抓娃娃次数，总数小于10
'''
doll_flag = 0  # 1开启抓娃娃，0关闭
doll_draw = 1

'''
box_flag   1开启开盲盒，0关闭
box_id  开盲盒类型，1为88豆，2为188豆，3为10000豆
box_draw   开盲盒次数，总数小于5
'''
box_flag = 0
box_id = 1
box_draw = 2
'''
basket_flag  1开启投篮球，0关闭
'''
basket_flag = 1
'''
竞猜专区，step，投入竞猜cc豆数量,guess_flag 0关闭，1开启
'''
guess_flag = 0

GLOBAL_DEBUG = 0
send_msg = ''


# 发送通知
def load_send():
    cur_path = path.abspath(path.dirname(__file__))
    notify_file = cur_path + "/notify.py"

    if path.exists(notify_file):
        try:
            from notify import send  # 导入模块的send为notify_send
            print("加载通知服务成功！")
            return send  # 返回导入的函数
        except ImportError:
            print("加载通知服务失败~")
    else:
        print("加载通知服务失败~")

    return False  # 返回False表示未成功加载通知服务


# AI答题
def ai_answer(question_name, answer_str, knowledge_points='', tips=''):
    try:
        tips = f'提示：{tips} ' if tips else ''
        question_str = (
            f'{knowledge_points}生活安全知识问答，请以安全为主，回答以下问题，仅需要回复答案前的选项id，不需要包含空格之后的中文及符号！ {tips}'
            f'问题：{question_name} \n选项：\n{answer_str}')
        print(question_str)
        # 生成时间戳和签名
        t = str(int(time.time() * 1000))
        secret_key = ""  # 固定密钥
        to_be_signed = f"{t}:{question_str}:{secret_key}"
        signature = hashlib.sha256(to_be_signed.encode()).hexdigest()

        # 发送请求
        url = 'https://gemini.fakeopen.link/api/generate'
        data = {
            "messages": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": question_str
                        }
                    ]
                }
            ],
            "time": t,
            "pass": None,
            "sign": signature
        }
        response = requests.post(url, json = data)
        if not response.text or 'None' in response.text:
            return ''
        print(f'AI答题结果: {response.text}')
        return response.text
    except Exception as e:
        print(f'错误信息:{e}')
        return ''


class CCD:
    base_header = {
        'Host': 'event.ccbft.com',
        'accept': 'application/json, text/plain, */*',
        'origin': 'https://event.ccbft.com',
        'x-requested-with': 'com.ccb.longjiLife',
        'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json'
    }

    def __init__(self, ccb_cookie):
        ccb_cookie_parts = ccb_cookie.split("#")
        self.deviceid, self.meb_id, self.phone, self.ccb_token = ccb_cookie_parts
        self.ccb_uuid = None
        self.zhc_token = None
        self.dmsp_st = None
        self.session = requests.Session()
        self.zq_headers = {
            'Host': 'fission-events.ccbft.com',
            'accept': 'application/json, text/plain, */*',
            'x-requested-with': 'XMLHttpRequest',
            'origin': 'https://fission-events.ccbft.com',
            'content-type': 'application/json'
        }

    # 随机延迟默认1-1.5
    def sleep(self, min_delay=1, max_delay=1.5):
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def send_request(self, url, headers=None, cookies=None, data=None, params=None, method='GET', debug=None,
                     retries=5):

        debug = debug if debug is not None else GLOBAL_DEBUG

        self.session.headers.update(headers or {})
        if cookies:
            self.session.cookies.update(cookies)
        request_args = {'json': data} if isinstance(data, dict) else {'data': data}

        for attempt in range(retries):
            try:
                response = self.session.request(method, url, params = params, **request_args)
                response.raise_for_status()
                if debug:
                    print(f'\n【{url}】响应数据:\n{response.text}')
                return response.json()
            except (requests.RequestException, ConnectionError, TimeoutError) as e:
                print(f"请求异常: {e}")
                if attempt >= retries - 1:
                    print("达到最大重试次数。")
                    return None
                time.sleep(1)

    def encrypt(self, text):
        res = requests.post('http://82.157.10.108:8086/get_jhenc', data = {'encdata': text})
        return res.text

    # 刷新session
    def get_ccbParam(self):
        cookies = {
        }

        headers = {
            'Host': 'yunbusiness.ccb.com',
            'user-agent': '%E5%BB%BA%E8%A1%8C%E7%94%9F%E6%B4%BB/2023031502 CFNetwork/1404.0.5 Darwin/22.3.0',
            'devicetype': 'iOS',
            'mbc-user-agent': f'MBCLOUDCCB/iPhone/iOS16.3.1/2.15/2.1.5/7E1BDB39-5CF8-4B88-BB12-AFF439B6A249/chinamworld/750*1334/2.1.5.002/1.0/{self.deviceid}/iPhone8Global/iOS/iOS16.3.1',
            'appversion': '2.1.5.002',
            'ua': 'IPHONE',
            'clientallver': '2.1.5.002',
            'deviceid': self.deviceid,
            'accept-language': 'zh-CN,zh-Hans;q=0.9',
            'c-app-id': '03_64e1367661ee4091acc04ce98f3660e6',
            'accept': 'application/json',
            'content-type': 'application/json',
        }

        params = {
            'txcode': 'autoLogin',
        }

        data = {
            "Token": self.ccb_token}
        data = json.dumps(data)
        data = quote(self.encrypt(data))
        response = requests.post('https://yunbusiness.ccb.com/clp_service/txCtrl', params = params,
                                 cookies = cookies,
                                 headers = headers, data = data)

        setCookie = response.headers.get('Set-Cookie')
        if setCookie:
            session_cookie = re.search(r'SESSION=([^;]+)', setCookie)
            session_value = session_cookie.group(1)

            param_url = 'https://yunbusiness.ccb.com/basic_service/txCtrl?txcode=A3341SB06'
            param_payload = {
                "regionCode": "110000",
                "PLATFORM_ID": "YS44000010000078",
                "chnlType": "1",
                "APPEND_PARAM": "",
                "ENCRYPT_MSG": f"BGCOLOR=&userid={self.meb_id}&mobile={self.phone}&orderid=&PLATFLOWNO=1051000101693904952945620&cityid=610100&openid=&Usr_Name=&USERID={self.meb_id}&MOBILE={self.phone}&ORDERID=&CITYID=610100&OPENID=&userCityId=360400&lgt=116.25548583307314&ltt=29.36255293895674&USERCITYID=360400&LGT=116.25548583307314&LTT=29.36255293895674&GPS_TYPE=gcj02&MOBILE={self.phone}&CrdtType=1010&CrdtNo=231212"
            }

            headers['cookie'] = f'SESSION={session_value}'
            param_data = requests.post(param_url, headers = headers, json = param_payload).json()
            errCode = param_data.get('errCode')
            if errCode != '0':
                print(param_data)
                return None
            else:
                ccbParam = param_data.get('data', {}).get('ENCRYPTED_MSG', '')
                return ccbParam
        else:
            print(f'session刷新失败，{response.text}')
            return None

    def get_ccb_uuid(self):
        ccbParam = self.get_ccbParam()
        try:
            url = f"https://event.ccbft.com/api/flow/nf/shortLink/redirect/ccb_gjb?CCB_Chnl=2030023&ccbParamSJ={ccbParam}&cityid=110000&CITYID=110000&userCityId=110000&USERCITYID=110000"

            payload = {
                "shortId": "polFsWD2jPnjhOx9ruVBcA",
                "archId": "ccb_gjb",
                "ccbParamSJ": ccbParam,
                "channelId": "ccbLife",
                "ifCcbLifeFirst": True
            }

            return_data = self.send_request(url, headers = self.base_header, data = payload, method = 'POST')

            redirect_url = return_data['data'].get('redirectUrl')
            ccb_uuid = return_data['data'].get('ccbLifeUUID')
            return redirect_url, ccb_uuid
        except Exception as e:
            print(e)

    def extract_token(self, redirect_url):
        pattern = f"__dmsp_token=([^&]+)"
        match = re.search(pattern, redirect_url)
        return match.group(1) if match else None

    # 登录
    def auth_login(self):
        redirect_url, ccb_uuid = self.get_ccb_uuid()
        token = self.extract_token(redirect_url)
        self.zhc_token = token
        self.ccb_uuid = ccb_uuid

        url = 'https://event.ccbft.com/api/businessCenter/auth/login'
        payload = {"token": token, "channelId": "ccbLife"}
        return_data = self.send_request(url, headers = self.base_header, data = payload, method = 'POST')
        self.sleep()
        if return_data['code'] != 200:
            print(return_data['message'])
        else:
            self.user_info()
            self.activation_medal()
            self.getlist()
            self.answer_state()
            print('\n======== 专区任务 ========')
            time.sleep(random.randint(3, 5))
            self.get_csrftoken()
            self.sleep()
            self.get_user_ccd()

    # 查询用户等级
    def user_info(self):
        url = f'https://event.ccbft.com/api/businessCenter/mainVenue/getUserState?zhc_token={self.zhc_token}'
        return_data = self.send_request(url, headers = self.base_header, method = 'POST')

        if return_data['code'] != 200:
            print(return_data['message'])
        else:
            current_level = return_data['data'].get('currentLevel')
            level = return_data['data'].get('currentProtectLevel')
            zhcRewardInfo = return_data['data'].get('zhcRewardInfo')
            if zhcRewardInfo is None:
                return print('查询用户信息失败，请手动领取一次营收奖励')
            reward_id = zhcRewardInfo.get('id')
            reward_type = zhcRewardInfo.get('rewardType')
            reward_value = zhcRewardInfo.get('rewardValue')
            receive_result = return_data.get('data').get('receiveResult')
            print(f"当前用户等级{current_level}级")
            if receive_result == '00':
                print('-今日营收已领取')
            else:
                self.income(level, reward_id, reward_type, reward_value)

    # 每日营收
    def income(self, level, reward_id, reward_type, reward_value):
        url = f'https://event.ccbft.com/api/businessCenter/mainVenue/receiveLevelReward?zhc_token={self.zhc_token}'
        payload = {"level": level, "rewardId": reward_id, "levelRewardType": reward_type}
        return_data = self.send_request(url, headers = self.base_header, data = payload, method = 'POST')
        self.sleep()
        if return_data['code'] != 200:
            print(return_data['message'])
        else:
            print(f"-今日营收: {reward_value}cc豆")

    # 每日勋章
    # 领取点亮所有勋章奖励
    def receive_500ccd_reward(self):
        light_url = f'https://event.ccbft.com/api/businessCenter/zhc/medalPage/allGather?zhc_token={self.zhc_token}'
        light_payload = {}
        light_data = self.send_request(light_url, headers = self.base_header, data = light_payload, method = 'POST')
        print(light_data.get('message'))

    # 激活勋章页
    def activation_medal(self):
        # 每日勋章奖励
        # daily_url = f'https://event.ccbft.com/api/businessCenter/zhc/medalPage/receiveDailyReward?zhc_token={self.zhc_token}'
        # daily_payload = {"medalPageId": "14"}
        # daily_data = self.send_request(daily_url, headers = self.base_header, data = daily_payload, method = 'POST')
        # print(f"每日勋章奖励领取: {daily_data.get('message')}")

        info_url = f'https://event.ccbft.com/api/businessCenter/zhc/medalPage/getUserLightUpStatus?zhc_token={self.zhc_token}'
        info_payload = {}
        info_data = self.send_request(info_url, headers = self.base_header, data = info_payload, method = 'POST')

        if info_data.get('data').get('hasPopupLightUpMedal') == 'Y' and info_data.get('data').get(
                'hasReceiveAllGatherReward') == 'N':
            print('所有勋章已激活，开始领取额外CC豆奖励！')
            self.receive_500ccd_reward()
        light_up_status_dict: dict = info_data.get('data').get('lightUpStatus')
        for medal_id, status in light_up_status_dict.items():
            if status.get('isReach') == 'Y' and status.get('isPopup') == 'N':
                print(f'开始激活{status.get("medalName")}勋章')
                url = f'https://event.ccbft.com/api/businessCenter/zhc/medalPage/confirmMedalPopup?zhc_token={self.zhc_token}'
                _json = {"medalId": medal_id}
                response = self.send_request(url, headers = self.base_header, data = _json, method = 'POST')
                print(response.get('message'))

    # 获取浏览任务列表
    def getlist(self):
        try:
            list_url = f'https://event.ccbft.com/api/businessCenter/taskCenter/getTaskList?zhc_token={self.zhc_token}'
            payload = {"publishChannels": "02", "regionId": "120000"}  # 440300

            list_res = self.send_request(url = list_url, headers = self.base_header, data = payload, method = 'POST')

            if list_res['code'] != 200:
                print(list_res['message'])
            else:
                task_list = list_res.get('data').get('ALL')

                for value in task_list:
                    complete_status = value['taskDetail'].get('completeStatus')
                    task_id = value['id']
                    task_name = value['taskName']
                    if complete_status == '02':
                        print(f"--已完成: {task_name}")
                    elif complete_status == '01':
                        print(f"-去领取: {task_name}")
                        self.receive(task_id)
                    else:

                        print(f'---去完成: {task_name}')
                        browse_url = f'https://event.ccbft.com/api/businessCenter/taskCenter/browseTask?zhc_token={self.zhc_token}'
                        payload = {"taskId": task_id, "browseSec": 5}

                        browse_data = self.send_request(browse_url, headers = self.base_header, data = payload,
                                                        method = 'POST')
                        print(browse_data['message'])
                        time.sleep(6)
                        self.send_request(url = list_url, headers = self.base_header, data = payload, method = 'POST')
                        self.receive(task_id)
        except Exception as e:
            print(e)

    def receive(self, task_id):
        receive_url = f'https://event.ccbft.com/api/businessCenter/taskCenter/receiveReward?zhc_token={self.zhc_token}'

        receive_payload = {"taskId": task_id}
        receive_data = self.send_request(receive_url, headers = self.base_header, data = receive_payload,
                                         method = 'POST')
        print(receive_data['message'])

    # 获取答题state
    def answer_state(self):
        try:
            state_url = f'https://event.ccbft.com/api/businessCenter/zhcUserDayAnswer/getAnswerStatus?zhc_token={self.zhc_token}'
            state_data = self.send_request(state_url, headers = self.base_header)
            if state_data['data'].get('answerState') == 'Y':
                print(state_data['message'])
                return
            # 获取今日题目
            print('获取今日题目')
            question_url = f'https://event.ccbft.com/api/businessCenter/zhcUserDayAnswer/queryQuestionToday?zhc_token={self.zhc_token}'
            question_data = self.send_request(question_url, headers = self.base_header)
            if question_data.get('code') != 200:
                print(question_data.get('message'))
                return
            question_id = question_data['data'].get('questionId')  # 问题id
            question_name = question_data.get('data').get('questionName')
            remark = question_data['data'].get('remark')  # 提示
            answer_list = question_data['data'].get('answerList')  # 选项

            answer_str = ''
            for answer in answer_list:
                answer_str += f"{answer.get('id')} {answer.get('answerResult')}\n"
            ai_text = ai_answer(question_name, answer_str, tips = remark)

            for answer in answer_list:
                answer_id = str(answer.get('id'))
                answer_text = answer.get('answerResult')
                if answer_id in ai_text or answer_text in ai_text:
                    _json = {"questionId": question_id, "answerIds": str(answer.get('id'))}
                    break
            else:
                print(f'使用AI回答问题失败！')
                print('开始随机选择！')
                _json = {"questionId": question_id, "answerIds": str(random.choice(answer_list).get('id'))}

            time.sleep(3)
            ans_url = f'https://event.ccbft.com/api/businessCenter/zhcUserDayAnswer/userAnswerQuestion?zhc_token={self.zhc_token}'
            ans__data = self.send_request(ans_url, headers = self.base_header, data = _json, method = 'POST')
            print(ans__data['message'])
        except Exception as e:
            print(f'错误信息: {e}')

    # ---------下面是精彩专区任务--------
    def get_csrftoken(self):
        refresh_url = 'https://event.ccbft.com/api/flow/nf/shortLink/redirect/ccb_gjb?CCB_Chnl=2030023'
        payload = '{{"shortId":"KJZQZFJMK001","archId":"ccb_gjb","ccbParamSJ":null,"channelId":"ccbLife","ifCcbLifeFirst":false,"ccbLifeUUID":"{}"}}'.format(
            self.ccb_uuid)

        return_data = requests.post(refresh_url, headers = self.base_header, data = payload).json()
        if return_data['code'] != 200:
            print(return_data['message'])

        else:
            redirect_url = return_data['data'].get('redirectUrl')
            csrf_token, authorization, ck = self.extract_csrf_and_auth(redirect_url)

            if csrf_token and authorization:
                self.zq_headers['x-csrf-token'] = csrf_token
                self.zq_headers['authorization'] = f'Bearer {authorization}'
                self.zq_headers['Cookie'] = ck
                self.sleep()

                print('\n---猜涨跌----')
                self.guess()
                print('\n----代发专区----')
                # self.game_id()
                print('\n----养老专区----')
                self.turn()
                print('\n----跨境专区----')
                self.border_draw()
                print('\n----商户专区----')
                self.shoplist()
                print('\n----消保专区----\n---抓龙珠----')
                self.xb_zlz()
                print('\n---开始消保知识大考验----')
                self.xb_knowl()
                print('\n---开始翻斗乐----')
                self.xb_fdl()
                print('\n---抓娃娃游戏----')
                self.get_doll()
                print('\n---投篮球游戏----')
                self.do_basket()
                print('\n---开盲盒----')
                self.open_box()
            else:
                print('CSRF token or Authorization not found.')

    def extract_csrf_and_auth(self, url):
        res = requests.get(url)
        csrf_token = re.findall('csrf-token content="(.*?)"', res.text)
        auth = re.findall('name=Authorization content="(.*?)"', res.text)
        cookie = "; ".join([f"{key}={value}" for key, value in res.cookies.items()])
        return csrf_token[0], auth[0], cookie

    # 养老专区新
    def turn(self):
        activity_id = 'QmD9jpZr'
        index_url = f'https://fission-events.ccbft.com/a/224/{activity_id}?CCB_Chnl=2030023&__dmsp_st={self.dmsp_st}'
        remain_url = f'https://fission-events.ccbft.com/Component/draw/getUserExtInfo/224/{activity_id}'
        draw_url = f'https://fission-events.ccbft.com/Component/draw/commonDrawPrize/224/{activity_id}'
        requests.get(index_url, headers = self.zq_headers)
        remain_res = self.send_request(remain_url, headers = self.zq_headers)
        if remain_res.get('status') != 'success':
            return remain_res.get('messagee')
        remain_num = int(remain_res.get('data').get('remain_num'))
        print(f'用户剩余抽签次数: {remain_num}')
        try:
            for _ in range(remain_num):
                draw_res = self.send_request(draw_url, headers = self.zq_headers, method = "POST")
                print(f'抽签获得: {draw_res.get("data").get("prizename")}')
                time.sleep(3)
        except Exception as e:
            print(e)

    # 跨境专区活动新
    def border_draw(self):
        try:
            activity_id = 'vmKOvKm1'
            query_url = f'https://fission-events.ccbft.com/activity/dmspzfjkjzq/index/224/{activity_id}'
            draw_url = f'https://fission-events.ccbft.com/activity/dmspzfjkjzq/draw/224/{activity_id}'
            tasks_url = f'https://fission-events.ccbft.com/Component/task/lists/224/{activity_id}'

            query_data = self.send_request(query_url, headers = self.zq_headers)
            if query_data['status'] != 'success':
                print(query_data['message'])
            else:
                tasks_res = self.send_request(tasks_url, headers = self.zq_headers)
                task = tasks_res.get('data').get('task')
                userTask = tasks_res.get('data').get('userTask')
                for val in userTask:
                    id = val.get('id')
                    finish = val.get('finish')
                    if id == 'JvmKA31V':
                        continue
                    for val2 in task:
                        id2 = val2.get('id')
                        name = val2.get('name')
                        if id2 == id:
                            if finish == 1:
                                print(f'已完成:{name}')
                            elif finish == 0:
                                print(f'去完成：{name}')
                                do_url = f'https://fission-events.ccbft.com/Component/task/do/224/{activity_id}'
                                do_payload = {"id": id2}
                                do_res = self.send_request(do_url, headers = self.zq_headers, data = do_payload,
                                                           method = "POST")
                                if do_res.get('status') != 'success':
                                    print(do_res.get('message'))
                                time.sleep(3)

                num_data = self.send_request(query_url, headers = self.zq_headers)
                remain = num_data.get('data').get('draw_times')
                if remain == 0:
                    return print('--当前剩余宝箱为0')
                self.sleep()

                print(f'开始开宝箱,次数:{remain}')
                for _ in range(remain):
                    draw_data = self.send_request(draw_url, headers = self.zq_headers, method = 'POST')
                    if draw_data['status'] != 'success':
                        print(draw_data['message'])
                    else:
                        print(f"--{draw_data['message']}---{draw_data['data'].get('prizename')}")
                    time.sleep(3)
        except Exception as e:
            print(f'跨境专区错误信息:{e}')

    # 商户专区新
    def shoplist(self):
        activity_id = 'aZkjwem1'
        index_url = f'https://fission-events.ccbft.com/a/224/{activity_id}?CCB_Chnl=6000115&__dmsp_st={self.dmsp_st}'
        requests.get(index_url, headers = self.zq_headers)
        task_url = f'https://fission-events.ccbft.com/Component/task/lists/224/{activity_id}'
        tasks_data = self.send_request(task_url, headers = self.zq_headers)
        self.sleep()
        if tasks_data['status'] != 'success':
            print(tasks_data['message'])
        else:
            task_list = tasks_data['data'].get('userTask')
            for value in task_list:
                complete_status = value['finish']
                if complete_status == 1:
                    print('--已完成该任务，继续浏览下一个任务')
                    continue
                task_id = value['id']
                do_url = f'https://fission-events.ccbft.com/Component/task/do/224/{activity_id}'
                payload = {"id": task_id}
                do_data = self.send_request(do_url, headers = self.zq_headers, data = payload, method = 'POST')
                if do_data['status'] != 'success':
                    print(do_data['message'])
                    continue
                print('--浏览完成')
                time.sleep(3)
            print('--已完成全部任务，去掷骰子')
            time.sleep(3)
            self.throw()

    def throw(self):
        try:
            activity_id = 'aZkjwem1'
            query_url = f'https://fission-events.ccbft.com/activity/dmspshzq/getIndex/224/{activity_id}'
            query_data = self.send_request(query_url, headers = self.zq_headers)
            if query_data['status'] != 'success':
                print(query_data['message'])
            else:
                remain_num = query_data['data'].get('remain_num')
                if remain_num == '0':
                    return print('当前没有骰子了')
                self.sleep()
                num = int(remain_num)
                draw_url = f'https://fission-events.ccbft.com/activity/dmspshzq/drawPrize/224/{activity_id}'
                payload = {}
                prizes = []
                for _ in range(num):
                    draw_data = self.send_request(draw_url, headers = self.zq_headers, data = payload, method = 'POST')
                    if draw_data['status'] != 'success':
                        print(draw_data['message'])
                        continue
                    add_step = draw_data['data'].get('add_step')
                    current_step = draw_data['data'].get('current_step')
                    prize_name = draw_data['data'].get('prize_name')
                    prizes.append(f"前进步数:{add_step},当前步数:{current_step}\n获得奖励:{prize_name}")
                    time.sleep(3)

                if prizes:
                    print('\n'.join(prizes))
        except Exception as e:
            print(f'商户专区错误信息:{e}')

    # 消保专区-欢乐抓龙珠
    def xb_zlz(self):
        try:
            activity_id = 'omv15EPr'
            num_url = f'https://fission-events.ccbft.com/activity/dmspxbzlz/getUserInfo/224/{activity_id}'
            num_data = self.send_request(num_url, headers = self.zq_headers)
            self.sleep()
            if num_data.get('status') != 'success':
                print(num_data.get('message'))
            else:
                remain_num = num_data['data'].get('remain_num', 0)
                num = int(remain_num)
                if num == 0:
                    print('当前剩余游戏次数为0')
                else:
                    id_url = f'https://fission-events.ccbft.com/activity/dmspxbzlz/startChallenge/224/{activity_id}'
                    game_url = f'https://fission-events.ccbft.com/activity/dmspxbzlz/doChallenge/224/{activity_id}'

                    for _ in range(num):
                        id_data = self.send_request(id_url, headers = self.zq_headers, data = {}, method = 'POST')
                        if id_data.get('status') != 'success':
                            print(id_data.get('message'))
                            continue
                        game_id = id_data.get('data').get('log_id')
                        print('获取成功，开始抓龙珠')
                        time.sleep(15)

                        payload_game = {"score": random.randint(100, 120), "l_id": game_id}
                        game_res = self.send_request(game_url, headers = self.zq_headers, data = payload_game,
                                                     method = 'POST')
                        print(game_res.get('message'))

                draw_num_url = f'https://fission-events.ccbft.com/Component/draw/getUserExtInfo/224/{activity_id}'
                do_draw_url = f'https://fission-events.ccbft.com/Component/draw/commonDrawPrize/224/{activity_id}'

                draw_num_res = self.send_request(draw_num_url, headers = self.zq_headers)
                draw_num = int(draw_num_res.get("data").get("remain_num"))
                print(f'当前抽奖次数:{draw_num}')
                for _ in range(draw_num):
                    do_draw_res = self.send_request(do_draw_url, headers = self.zq_headers, data = {},
                                                    method = 'POST')
                    if do_draw_res.get("status") != 'success':
                        print(do_draw_res.get("message"))
                    else:
                        print(f'抽奖获得: {do_draw_res.get("data").get("prizename")}')
                    time.sleep(3)
        except Exception as e:
            print(e)

    # 消保翻斗乐
    def xb_fdl(self):
        activity_id = '631LWXZ2'
        turn_num_url = f'https://fission-events.ccbft.com/activity/dmspfdl/getUserInfo/224/{activity_id}'
        turn_num_res = self.send_request(turn_num_url, headers = self.zq_headers)
        remain_num = int(turn_num_res.get("data").get("remain_num"))
        point_list = turn_num_res.get("data").get("point_list")

        print(f'今日剩余翻牌次数: {remain_num}')
        time.sleep(1)
        if remain_num <= 0:
            return
        try:
            for _ in range(remain_num):
                random_number = random.choice([str(n) for n in range(1, 10) if str(n) not in point_list])
                point_list.append(random_number)
                start_turn_num = f'https://fission-events.ccbft.com/activity/dmspfdl/startChallenge/224/{activity_id}'
                start_turn_payload = {"point": random_number}
                start_turn_res = self.send_request(start_turn_num, data = start_turn_payload, headers = self.zq_headers,
                                                   method = "POST")
                if start_turn_res.get('data').get('game_type') == 'answer':
                    print('翻牌成功，开始答题')
                    levle_url = f'https://fission-events.ccbft.com/Component/answer/getLevels/224/{activity_id}'
                    level_res = self.send_request(levle_url, headers = self.zq_headers)
                    level = level_res.get('data').get('list')[0].get('level')  # 获取题库
                    question_num = level_res.get('data').get('list')[0].get('question_num')  # 答题次数

                    start_url = f'https://fission-events.ccbft.com/Component/answer/getQuestions/224/{activity_id}'
                    start_payload = {"id": level}
                    start_res = self.send_request(start_url, data = start_payload, headers = self.zq_headers,
                                                  method = "POST")
                    if start_res.get('status') != 'success':
                        continue
                    question = start_res.get('data')[0]

                    for _ in range(question_num):  # 假设每轮答题有三个问题
                        question_id = question.get('questionId')
                        question_name = question.get('title')
                        answer_list = question.get('options')

                        # 获取 AI 答案
                        ai_text = ai_answer(question_name, answer_list)

                        # 选择答案
                        chosen_option = next((answer.get('id') for answer in answer_list if
                                              answer.get('id') in ai_text or answer.get('option') in ai_text),
                                             random.choice(answer_list).get('id'))

                        # 提交答案并获取下一个问题
                        answ_json = {'id': question_id,
                                     'levelId': level,
                                     'options': chosen_option}
                        answ_url = f"https://fission-events.ccbft.com/Component/answer/do/224/{activity_id}"
                        answ_data = self.send_request(answ_url, headers = self.zq_headers, data = answ_json,
                                                      method = "POST")

                        if i < 2:  # 如果不是最后一个问题，获取下一个问题
                            question = answ_data.get('data').get('next')
                        time.sleep(5)

                    # 获取答题结果
                    res_url = f"https://fission-events.ccbft.com/Component/answer/getResult/224/{activity_id}"
                    res_json = {'id': level}
                    res_data = self.send_request(res_url, headers = self.zq_headers, data = res_json, method = 'POST')
                    rights = res_data.get('data').get('rights')
                    print(f'答对次数: {rights}')
        except Exception as e:
            print(f'翻牌错误:{e}')
        num_url = f"https://fission-events.ccbft.com/Component/draw/getUserExtInfo/224/{activity_id}"

        num_data = self.send_request(num_url, headers = self.zq_headers)

        remain_num = int(num_data.get('data').get('remain_num'))
        print(f'剩余抽奖次数：{remain_num}')
        if remain_num == 0:
            return
        print('开始抽奖')
        draw_url = f"https://fission-events.ccbft.com/Component/draw/commonDrawPrize/224/{activity_id}"
        for _ in range(int(remain_num)):
            draw_data = self.send_request(draw_url, headers = self.zq_headers, method = 'POST')
            if draw_data.get('status') == 'success':
                print(f'获得奖品：{draw_data.get("data").get("prizename")}')
            else:
                print(draw_data.get('message'))
            time.sleep(3)

    # 消保知识大考验
    def xb_knowl(self):
        try:
            activity_id = 'WZjQwQmx'
            num_url = f"https://fission-events.ccbft.com/Component/answer/getLevels/224/{activity_id}"
            num_data = self.send_request(num_url, headers = self.zq_headers)
            answer_num = int(num_data.get('data').get('answer_num'))
            print(f'答题机会次数：{answer_num}')
            if answer_num <= 0:
                return
            type_url = f'https://fission-events.ccbft.com/Component/answer/getLevels/224/{activity_id}'
            type_res = self.send_request(type_url, headers = self.zq_headers)
            list = type_res.get('data').get('list')
            xb_level_id = list[3].get('level')
            for _ in range(answer_num):
                # 获取第一个问题
                ques_url = f"https://fission-events.ccbft.com/Component/answer/getQuestions/224/{activity_id}"
                ques_json = {'id': xb_level_id}
                ques_data = self.send_request(ques_url, headers = self.zq_headers, data = ques_json, method = 'POST')
                if ques_data.get('status') != 'success':
                    continue
                question_data = ques_data.get('data')[0]

                for i in range(3):  # 假设每轮答题有三个问题
                    question_id = question_data.get('questionId')
                    question_name = question_data.get('title')
                    answer_list = question_data.get('options')

                    # 获取 AI 答案
                    ai_text = ai_answer(question_name, answer_list, knowledge_points = '消费者权益保护知识考验')

                    # 选择答案
                    chosen_option = next((answer.get('id') for answer in answer_list if
                                          answer.get('id') in ai_text or answer.get('option') in ai_text),
                                         random.choice(answer_list).get('id'))

                    # 提交答案并获取下一个问题
                    answ_json = {'id': question_id,
                                 'levelId': xb_level_id,
                                 'options': chosen_option}
                    answ_url = f"https://fission-events.ccbft.com/Component/answer/do/224/{activity_id}"
                    answ_data = self.send_request(answ_url, headers = self.zq_headers, data = answ_json,
                                                  method = "POST")

                    if i < 2:  # 如果不是最后一个问题，获取下一个问题
                        question_data = answ_data.get('data').get('next')
                    time.sleep(5)

                # 获取答题结果
                res_url = f"https://fission-events.ccbft.com/Component/answer/getResult/224/{activity_id}"
                res_json = {'id': xb_level_id}
                res_data = self.send_request(res_url, headers = self.zq_headers, data = res_json, method = 'POST')
                rights = res_data.get('data').get('rights')
                print(f'答对次数: {rights}')

            num_url = f"https://fission-events.ccbft.com/Component/draw/getUserExtInfo/224/{activity_id}"

            num_data = self.send_request(num_url, headers = self.zq_headers)

            remain_num = int(num_data.get('data').get('remain_num'))
            print(f'剩余抽奖次数：{remain_num}')
            if remain_num == 0:
                return
            print('开始抽奖')
            draw_url = f"https://fission-events.ccbft.com/Component/draw/commonDrawPrize/224/{activity_id}"
            for _ in range(int(remain_num)):
                draw_data = self.send_request(draw_url, headers = self.zq_headers, method = 'POST')
                if draw_data.get('status') == 'success':
                    print(f'获得奖品：{draw_data.get("data").get("prizename")}')
                else:
                    print(draw_data.get('message'))
                time.sleep(3)
        except Exception as e:
            print(e)

    # 抓娃娃
    def get_doll(self):
        if doll_flag == 0:
            print('已关闭抓娃娃游戏')
            return
        activity_id = 'WZjQwQmx'
        query_url = f'https://fission-events.ccbft.com/Component/draw/getUserCCB/224/{activity_id}'
        draw_url = f'https://fission-events.ccbft.com/Component/draw/dmspCommonCcbDrawPrize/224/{activity_id}'

        # 查询用户当前可用次数
        query_data = self.send_request(query_url, headers = self.zq_headers)
        user_draw_num = query_data.get('data', {}).get('user_day_draw_num', 0)
        remaining_draws = 10 - int(user_draw_num)
        target_draws = 10 - doll_draw
        print(f'--当前剩余游戏次数: {remaining_draws}')

        # 进行游戏
        while remaining_draws > target_draws:
            draw_data = self.send_request(draw_url, headers = self.zq_headers, method = 'POST')
            if draw_data.get('status') != 'success':
                print(draw_data.get('message', '抓娃娃游戏出错'))
                remaining_draws -= 1
                continue

            prizename = draw_data.get('data', {}).get('prizename', '未知奖品')
            print(f'{draw_data.get("message", "操作结果")}  获得奖品: {prizename}')
            time.sleep(3)
            remaining_draws -= 1

    # 投篮球
    def do_basket(self):
        try:
            if basket_flag == 0:
                print('已关闭投篮球游戏')
                return
            activity_id = 'vmKOLkm1'
            index_url = f'https://fission-events.ccbft.com/a/224/{activity_id}/index?CCB_Chnl=1000181'
            query_url = f'https://fission-events.ccbft.com/activity/dmspdunk/user/224/{activity_id}'
            requests.get(url = index_url, headers = self.zq_headers)
            query_data = self.send_request(query_url, headers = self.zq_headers)
            remain_daily = query_data.get('data', {}).get('remain_daily_times', 0)
            print(f'--当前剩余游戏次数: {remain_daily}')
            self.sleep()

            while remain_daily:
                id_url = f'https://fission-events.ccbft.com/activity/dmspdunk/start/224/{activity_id}'
                id_data = self.send_request(id_url, headers = self.zq_headers, method = 'POST')

                if id_data.get('status') != 'success':
                    print(id_data.get('message'))
                    continue
                game_id = id_data.get('data', {}).get('id')
                time.sleep(5)
                activity_url = f'https://fission-events.ccbft.com/activity/dmspdunk/scene/224/{activity_id}?id={game_id}'
                activity_data = self.send_request(activity_url, headers = self.zq_headers)
                remain_times = activity_data.get('data', {}).get('remain_times')
                basket_num = int(remain_times)  # 篮球数量
                while basket_num:
                    dogame_url = f'https://fission-events.ccbft.com/activity/dmspdunk/shot/224/{activity_id}'
                    payload = {'id': game_id}
                    dogeme_data = self.send_request(dogame_url, headers = self.zq_headers, data = payload,
                                                    method = 'POST')
                    if dogeme_data.get('status') != 'success':
                        print(dogeme_data.get('message'))
                        continue
                    win_times = dogeme_data.get('data', {}).get('win_times')  # 投中数量
                    got_ccb = dogeme_data.get('data', {}).get('got_ccb')  # 获得cc豆
                    print(f'当前投中篮球数量: {win_times}')

                    if basket_num == 1:
                        print(f'游戏结束,获得cc豆数量: {got_ccb}')
                    time.sleep(2.5)
                    basket_num -= 1
                remain_daily -= 1
        except Exception as e:
            print(f"错误：{e}")

    # 开盲盒
    def open_box(self):
        if box_flag == 0:
            print('已关闭开盲盒')
            return
        # 获取盲盒类型信息
        type_url = 'https://fission-events.ccbft.com/activity/dmspblindbox/index/224/xZ4JKaPl'
        type_data = self.send_request(type_url, headers = self.zq_headers)
        self.sleep()

        # 解析盲盒类型数据
        types = type_data.get('data', [])
        selected_box = next((item for item in types if item['pot_id'] == box_id), None)

        if not selected_box:
            print("未找到对应盲盒种类")
            return

        print(f'当前盲盒种类: [{selected_box["pot_name"]}], 需消耗: {selected_box["draw_one_ccb"]}cc豆')
        self.process_opening(selected_box['pot_id'])

    def process_opening(self, pot_id):
        # 获取用户当前可用次数
        num_url = 'https://fission-events.ccbft.com/Component/draw/getUserCCB/224/xZ4JKaPl'
        num_data = self.send_request(num_url, headers = self.zq_headers)
        self.sleep()

        # 解析可用次数
        draw_num = int(num_data.get('data', {}).get('draw_day_max_num', 0))
        user_num = int(num_data.get('data', {}).get('user_day_draw_num', 0))
        surplus_num = draw_num - user_num

        print(f'--当前可用开盲盒次数: {surplus_num}')

        # 开始开盲盒
        while surplus_num > (draw_num - box_draw):
            open_url = 'https://fission-events.ccbft.com/activity/dmspblindbox/draw/224/xZ4JKaPl'
            open_data = self.send_request(open_url, headers = self.zq_headers, data = {"pot_id": pot_id},
                                          method = 'POST')

            if open_data.get('status') != 'success':
                print(open_data.get('message', '开盲盒失败'))
                surplus_num -= 1
                continue

            prizename = open_data.get('data', {}).get('prizename', '未知物品')
            print(f'开盲盒获得: {prizename}')
            time.sleep(3)
            surplus_num -= 1

    # 竞猜专区
    def guess_info(self):
        activity_id = '8ZWXw53w'
        # 获取用户信息
        info_url = f'https://fission-events.ccbft.com/activity/dmspguesszd/userinfo/224/{activity_id}'
        remain_url = f'https://fission-events.ccbft.com/Component/draw/getUserCCB/224/{activity_id}'

        try:
            info_data = self.send_request(info_url, headers = self.zq_headers)
            remain_data = self.send_request(remain_url, headers = self.zq_headers)

            user_info = info_data.get('data', {})
            scene_ccb = user_info.get('scene_ccb')
            win_ratio = user_info.get('win_ratio')
            guess_data = user_info.get('guess_data')
            guess_times = user_info.get('guess_times')
            guess_right_times = user_info.get('guess_right_times')

            # 打印用户信息
            print(f'本赛季已得: {scene_ccb}CC豆, 胜率: {win_ratio}')
            print(f'已预测次数: {guess_times}, 猜对次数: {guess_right_times}')
            remain_money = remain_data.get('data', {}).get('remain_money')

            return guess_data, remain_money

        except Exception as e:
            print(f"发生异常: {e}")
            return None, None

    def guess(self):

        if guess_flag == 0:
            print('已关闭猜涨跌')
            return
        activity_id = '8ZWXw53w'
        guess_data, remain_money = self.guess_info()

        list_url = f'https://fission-events.ccbft.com/activity/dmspguesszd/index/224/{activity_id}'
        list_data = self.send_request(list_url, headers = self.zq_headers)
        src_list = list_data.get('data', {}).get('src_list', [])

        n = remain_money
        guess_url = f'https://fission-events.ccbft.com/activity/dmspguesszd/guess/224/{activity_id}'

        try:
            for value in src_list:
                src = value.get('src')
                src_value = str(src)
                src_name = value.get('src_name')

                if src_value not in guess_data or guess_data[src_value] != {}:
                    print(f'已竞猜: {src_name}')
                    continue

                guess_rise_ratio = float(value.get('guess_rise_ratio').replace('%', ''))
                guess_fall_ratio = float(value.get('guess_fall_ratio').replace('%', ''))

                print(f'开始竞猜: {src_name}')
                guess_step = None

                # 确定竞猜方向
                payload_type = 1 if guess_rise_ratio > guess_fall_ratio else 2
                direction = "涨" if payload_type == 1 else "跌"
                selected_ratio = guess_rise_ratio if payload_type == 1 else guess_fall_ratio

                # 检查所选比率是否小于63.0，并据此调整步骤
                if selected_ratio > 78.0:
                    print(f'当前选{direction}占比{selected_ratio},为你投第五档500豆')
                    if n >= 500:
                        guess_step = 5
                        n = n - 500
                    else:
                        print('当前CC豆余额不足，选最低档竞猜')
                        guess_step = 1
                        n = n - 20
                elif selected_ratio > 68:
                    print(f'当前选{direction}占比{selected_ratio},为你投第四档200豆')
                    if n >= 200:
                        guess_step = 4
                        n = n - 200
                    else:
                        print('当前CC豆余额不足，选最低档竞猜')
                        guess_step = 1
                        n = n - 20
                elif selected_ratio > 60:
                    print(f'当前选{direction}占比{selected_ratio},为你投第三档100豆')
                    if n >= 100:
                        guess_step = 3
                        n = n - 100
                    else:
                        print('当前CC豆余额不足，选最低档竞猜')
                        guess_step = 1
                        n = n - 20
                elif selected_ratio > 50:
                    print(f'当前选{direction}占比{selected_ratio},为你投第一档20豆')
                    guess_step = 1

                payload = {"type": payload_type, "step": guess_step, "src": src}

                response = self.send_request(guess_url, headers = self.zq_headers, data = payload, method = "POST")
                print(response.get('message'))
                time.sleep(5)
        except Exception as e:
            print(e)

    # 查询cc豆及过期cc豆时间
    def get_user_ccd(self):
        urls = {
            'current_ccd': f'https://event.ccbft.com/api/businessCenter/user/getUserCCD?zhc_token={self.zhc_token}',
            'expired_ccd': f'https://event.ccbft.com/api/businessCenter/user/getUserCCDExpired?zhc_token={self.zhc_token}'
        }
        ccd_data = {}

        for key, url in urls.items():
            try:
                response = self.send_request(url, headers = self.base_header, data = {}, method = 'POST')
                self.sleep()  # Assuming this is a custom method to delay between requests
                if response['code'] != 200:
                    raise Exception(f"Error fetching {key}: {response['message']}")
                ccd_data[key] = response['data']
            except Exception as e:
                print(f"An exception occurred: {e}")
                return  # Early return on failure

        current_count = ccd_data['current_ccd'].get('userCCBeanInfo', {}).get('count', 'unknown')
        expired_count = ccd_data['expired_ccd'].get('userCCBeanExpiredInfo', {}).get('count', 'unknown')
        expire_date_str = ccd_data['expired_ccd'].get('userCCBeanExpiredInfo', {}).get('expireDate', '')

        if expire_date_str:
            global send_msg
            expire_date = datetime.fromisoformat(expire_date_str)
            formatted_date = expire_date.strftime('%Y-%m-%d %H:%M:%S')
            msg = f'\n当前cc豆: {current_count}，有 {expired_count} cc豆将于 {formatted_date} 过期。'
            send_msg += f'用户【{self.phone}】: {msg}\n'
            print(msg)


if __name__ == "__main__":
    env_name = 'ccdck'
    token = os.getenv(env_name)
    if not token:
        print(f'⛔️未获取到ck变量：请检查变量 {env_name}是否填写')
        exit(0)
    cookies = re.split(r'[@\n]', token)
    msg = f"建行cc豆共获取到{len(cookies)}个账号"
    print(msg)

    for i, cookie in enumerate(cookies, start = 1):
        print(f"\n======== ▷ 第 {i} 个账号 ◁ ========")
        CCD(cookie).auth_login()
        print("\n随机等待5-10s进行下一个账号")
        time.sleep(random.randint(5, 10))
    # 在load_send中获取导入的send函数
    send = load_send()

    # 判断send是否可用再进行调用
    if send:
        send('建行生活CC豆', send_msg)
    else:
        print('通知服务不可用')
