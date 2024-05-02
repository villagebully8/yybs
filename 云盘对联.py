# 脚本名称: 中国移动云盘
# 功能描述: 答对联，获得立减金或云朵
# 使用说明:
#   - 抓包 Cookie：任意Authorization
# 环境变量设置:
#   - 名称：ydypCk   值：Authorization值#手机号#authToken的值
#   - 多账号处理方式：换行或者@分割
# 定时设置: 0 0 0 * * *
# 更新日志:
# 注: 本脚本仅用于个人学习和交流，请勿用于非法用途。作者不承担由于滥用此脚本所引起的任何责任，请在下载后24小时内删除。
# 作者: 洋洋不瘦
import hashlib
import os
import random
import re
import time
import requests
from urllib.parse import quote

ua = 'Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/90.0.4430.210 Mobile Safari/537.36 MCloudApp/10.3.1'

err_accounts = []  # 异常账号
GLOBAL_DEBUG = False


def ai_answer(question_name, tip):
    try:
        question_str = (
            f'对联大全，搜索以下对联，回答空缺部分，不需要包含额外文字，空格及符号！\n{question_name},{tip}')
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


class YP:
    def __init__(self, cookie):
        self.jwtToken = None
        self.Authorization = cookie.split("#")[0]
        self.account = cookie.split("#")[1]
        self.auth_token = cookie.split("#")[2]
        self.encrypt_account = self.account[:3] + "*" * 4 + self.account[7:]

        self.jwtHeaders = {
            'User-Agent': ua,
            'Accept': '*/*',
            'Host': 'caiyun.feixin.10086.cn:7071',
            'content-type': 'application/json; charset=UTF-8',
        }

    def send_request(self, url, headers=None, params=None, data=None, cookies=None, method='GET', debug=None):
        try:
            debug = debug if debug is not None else GLOBAL_DEBUG

            with requests.Session() as session:
                session.headers.update(headers or {})
                if cookies is not None:
                    session.cookies.update(cookies)

                if isinstance(data, dict):
                    response = session.request(method, url, params = params, json = data)
                else:
                    response = session.request(method, url, params = params, data = data)

                response.raise_for_status()

                if debug:
                    print(response.text)

                return response

        except requests.RequestException as e:
            print("请求错误:", str(e))

        return None

    # 随机延迟默认1-1.5s
    def sleep(self, min_delay=1, max_delay=1.5):
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    # 刷新令牌
    def sso(self):
        sso_url = 'https://orches.yun.139.com/orchestration/auth-rebuild/token/v1.0/querySpecToken'
        sso_headers = {
            'Authorization': self.Authorization,
            'User-Agent': ua,
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Host': 'orches.yun.139.com'
        }
        sso_payload = {"account": self.account, "toSourceId": "001005"}
        sso_data = self.send_request(sso_url, headers = sso_headers, data = sso_payload, method = 'POST').json()

        if sso_data['success']:
            refresh_token = sso_data['data']['token']
            return refresh_token
        else:
            print(sso_data['message'])
            return None

    # jwt
    def jwt(self):
        # 获取jwttoken
        token = self.sso()
        if token is not None:

            jwt_url = f"https://caiyun.feixin.10086.cn:7071/portal/auth/tyrzLogin.action?ssoToken={token}"
            jwt_data = self.send_request(jwt_url, headers = self.jwtHeaders, method = 'POST').json()
            if jwt_data['code'] != 0:
                print(jwt_data['msg'])
                return False
            self.jwtToken = jwt_data['result']['token']
            self.jwtHeaders['jwtToken'] = self.jwtToken
            return True
        else:
            print('-ck可能失效了')
            return False

    # 获得题目
    def get_title(self):
        try:
            if self.jwt():
                title_url = 'https://caiyun.feixin.10086.cn/market/lanternriddles/answeredPuzzles/getIndexPuzzleCard'
                title_res = self.send_request(title_url, headers = self.jwtHeaders).json()
                result = title_res.get('result')
                req_num = 1
                while req_num > 0:
                    flag = 0
                    for value in result:
                        id = value.get('id')
                        puzzleTitleContext = value.get('puzzleTitleContext')  # 题目
                        puzzleTipContext = value.get('puzzleTipContext')  # 提示

                        # AI  答题
                        ai_text = quote(ai_answer(puzzleTitleContext, puzzleTipContext))

                        # 答题
                        ans_url = f'https://caiyun.feixin.10086.cn/market/lanternriddles/answeredPuzzles/submitAnswered?puzzleId={id}&answered={ai_text}'

                        ans_res = self.send_request(ans_url, headers = self.jwtHeaders).json()
                        print(ans_res.get('msg'))
                        if ans_res.get('code') == 201:
                            print('--今日抽奖次数已上限')
                            flag = 201
                            break
                        elif ans_res.get('code') == 0:
                            self.do_draw(id)
                            time.sleep(1)
                            for _ in range(4):
                                ans_res = self.send_request(ans_url, headers = self.jwtHeaders).json()
                                print(ans_res.get('msg'))
                                if ans_res.get('code') == 201:
                                    print('--今日抽奖次数已上限')
                                    flag = 201
                                    break
                                self.do_draw(id)
                        time.sleep(2)

                    # 如果已经答完了所有题目，则退出循环
                    if flag == 201:
                        break
                    req_num -= 1

            else:
                # 失效账号
                err_accounts.append(self.encrypt_account)
        except Exception as e:
            print(f"发生错误：{e}")

    # 抽奖
    def do_draw(self, id):
        draw_url = 'https://caiyun.feixin.10086.cn/market/lanternriddles/answeredPuzzles/awarding'
        draw_payload = {
            "puzzleId": id
        }
        draw_res = self.send_request(draw_url, headers = self.jwtHeaders, data = draw_payload, method = "POST").json()
        print(f'--抽奖获得: {draw_res.get("result").get("prizeName")}')


if __name__ == "__main__":
    env_name = 'ydypCK'
    py_name = '移动云盘'
    token = os.getenv(env_name)
    if not token:
        print(f'⛔️未获取到ck变量：请检查变量 {env_name}是否填写')
        exit(0)

    cookies = re.split(r'[@\n]', token)
    print(f"{py_name}共获取到{len(cookies)}个账号")
    for i, account_info in enumerate(cookies, start = 1):
        print(f"\n======== ▷ 第 {i} 个账号 ◁ ========")
        YP(account_info).get_title()
        print("\n随机等待5-10s进行下一个账号")
        time.sleep(random.randint(5, 10))

    # 输出异常账号信息
    if err_accounts:
        print("\n异常账号:")
        for account in err_accounts:
            print(account)
    else:
        print('当前所有账号正常')
