#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中航 (xdww/gsftsm) 每日签到
==========================================

⚠️ 风险提示（请认真阅读）
------------------------------------------
1. 本平台用裸 IP + 自签证书，域名 xdww.cast.mn.gsftsm.com 与中国航天科技集团无任何关联。
2. 业务话术为"原价 10 万 / 补贴价 0 / 每日固定收益 / 拉人头阶梯返佣 / 锁定 180 天 50 元每天"，
   符合典型资金盘 / 庞氏 / 拉人头特征。
3. 平台明文存储手机号 + 密码到 localStorage，且要求实名身份证 + 银行卡，存在严重个人信息泄露风险。
4. 本脚本仅作为接口逆向技术演示，不构成任何投资建议；产生的所谓"收益"在此类平台一般无法真实提现，
   后续大概率诱导充值或拉人头。**强烈建议立刻注销账号、删除身份证 / 银行卡绑定，并停止使用该平台。**

#注册链接yq.mdophb.com/#/register?inviteCode=515838
##邀请码515838

==========================================
接口梳理
------------------------------------------
BASE: https://api.xdww.cast.mn.gsftsm.com

1) 登录
   POST /api/v1/login
   body: {"phone": "...", "password": "...", "version": 1}
   200  -> data.token = "<uid>|<random>"  (Laravel Sanctum 风格)

2) 免费产品状态（判断今天是否还能签）
   GET /api/v1/products/free
   header: Authorization: Bearer <token>
   200  -> data.available_request: int  (>0 表示可签到)

3) 签到 / 领每日收益
   POST /api/v1/operation/request
   header: Authorization: Bearer <token>
   body: {"order_quantity": 50}
   200  -> data.operation_service.profit: int  (本次收益)

无签名 / 无设备 id / 无时间戳 / 无 nonce，纯 Bearer Token。
==========================================
青龙 / 多账号
------------------------------------------
#注册链接yq.mdophb.com/#/register?inviteCode=612051
##邀请码612051
环境变量 CAST_ACCOUNTS 多账号用换行或 & 分隔，每条 "手机号#密码[#备注]"
示例：
    CAST_ACCOUNTS = "18300000001#密码#小号A&18350000002#密码#小号B"
可选环境变量：
    CAST_DELAY_MIN / CAST_DELAY_MAX  账号间随机延迟（默认 8-20 秒）
    CAST_TIMEOUT                     单请求超时秒数（默认 20）
==========================================
"""

import os
import sys
import time
import json
import random
import hashlib
import logging
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ===================== 配置区 =====================
# 本地直跑可在这里写死，青龙优先读 CAST_ACCOUNTS 环境变量
ACCOUNTS = [
    # {"phone": "18300000001", "password": "密码", "name": "账号1"},
]

BASE_URL = "https://api.xdww.cast.mn.gsftsm.com"

# 提交的 order_quantity 服务端会按用户实际产品上限纠正，固定写 50 即可
ORDER_QUANTITY = 50

DEFAULT_TIMEOUT = int(os.environ.get("CAST_TIMEOUT", 20))
DEFAULT_DELAY_MIN = int(os.environ.get("CAST_DELAY_MIN", 8))
DEFAULT_DELAY_MAX = int(os.environ.get("CAST_DELAY_MAX", 20))

# UA 池：按账号手机号哈希固化，避免泄露本机指纹，且同一账号每天 UA 稳定（防 UA 突变风控）
# 每条都是 (label, user-agent, sec-ch-ua-platform, sec-ch-ua-mobile, sec-ch-ua)
# Safari 不发 sec-ch-ua，置 None
UA_POOL = [
    (
        "win-chrome-131",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        '"Windows"',
        "?0",
        '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    ),
    (
        "win-chrome-130",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        '"Windows"',
        "?0",
        '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    ),
    (
        "win-chrome-128",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        '"Windows"',
        "?0",
        '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    ),
    (
        "android-chrome-131",
        "Mozilla/5.0 (Linux; Android 14; SM-S921U) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        '"Android"',
        "?1",
        '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    ),
    (
        "android-chrome-130",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        '"Android"',
        "?1",
        '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    ),
    (
        "android-chrome-mi",
        "Mozilla/5.0 (Linux; Android 13; 23049RAD8C Build/TKQ1.221114.001) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
        '"Android"',
        "?1",
        '"Chromium";v="129", "Not=A?Brand";v="8", "Google Chrome";v="129"',
    ),
    (
        "iphone-safari-17",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        '"iOS"',
        "?1",
        None,
    ),
    (
        "iphone-safari-18",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        '"iOS"',
        "?1",
        None,
    ),
]


def pick_ua_for(seed: str):
    """同一 seed (一般是手机号) 永远返回同一条 UA，防 UA 突变。"""
    digest = hashlib.md5(seed.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "big") % len(UA_POOL)
    return UA_POOL[idx]


def build_headers(seed: str):
    label, ua, platform, mobile, ch_ua = pick_ua_for(seed)
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "referer": "https://8.159.152.71:32939/",
        "user-agent": ua,
        "sec-ch-ua-mobile": mobile,
        "sec-ch-ua-platform": platform,
    }
    if ch_ua:
        headers["sec-ch-ua"] = ch_ua
    return label, headers


# ==================================================


# --------- 日志 ---------
def _setup_logger():
    logger = logging.getLogger("cast")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%H:%M:%S"))
        logger.addHandler(h)
    return logger


log = _setup_logger()


def mask_phone(phone: str) -> str:
    if not phone or len(phone) < 7:
        return phone or ""
    return phone[:3] + "****" + phone[-4:]


def mask_token(token: str) -> str:
    if not token:
        return ""
    if "|" in token:
        head, tail = token.split("|", 1)
        return f"{head}|{tail[:4]}***{tail[-4:]}"
    return token[:4] + "***" + token[-4:]


# --------- 账号读取 ---------
def load_accounts():
    env = os.environ.get("CAST_ACCOUNTS", "").strip()
    if env:
        accounts = []
        # 支持 & 或换行分隔
        for raw in env.replace("\n", "&").split("&"):
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split("#")
            if len(parts) < 2:
                log.warning("跳过格式错误的账号: %s", raw)
                continue
            phone, password = parts[0].strip(), parts[1].strip()
            name = (
                parts[2].strip()
                if len(parts) >= 3 and parts[2].strip()
                else mask_phone(phone)
            )
            accounts.append({"phone": phone, "password": password, "name": name})
        return accounts
    return list(ACCOUNTS)


# --------- HTTP 客户端 ---------
class CastClient:
    def __init__(self, account, timeout=DEFAULT_TIMEOUT):
        self.phone = account["phone"]
        self.password = account["password"]
        self.name = account.get("name") or mask_phone(self.phone)
        self.timeout = timeout
        self.token = None
        self.session = requests.Session()
        # UA 按手机号哈希固化：同账号每次跑都是同一条 UA + 配套 sec-ch-ua / platform / mobile
        ua_label, headers = build_headers(self.phone)
        self.ua_label = ua_label
        self.session.headers.update(headers)
        log.info("[%s] 使用 UA=%s", self.name, ua_label)
        # 平台用自签证书，必须关 verify
        self.session.verify = False

    # 出错后简单重试
    def _request(self, method, path, **kwargs):
        url = BASE_URL + path
        kwargs.setdefault("timeout", self.timeout)
        last_err = None
        for attempt in range(3):
            try:
                resp = self.session.request(method, url, **kwargs)
                # Laravel 业务码都走 200，非 200 直接抛
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as e:
                last_err = e
                wait = 2 * (attempt + 1)
                log.warning(
                    "[%s] %s %s 失败(%s)，%ss 后重试", self.name, method, path, e, wait
                )
                time.sleep(wait)
        raise RuntimeError(f"请求 {method} {path} 多次失败: {last_err}")

    def login(self):
        data = self._request(
            "POST",
            "/api/v1/login",
            json={"phone": self.phone, "password": self.password, "version": 1},
        )
        if not data.get("status"):
            raise RuntimeError(f"登录失败: {data.get('message')}")
        token = data["data"]["token"]
        user = data["data"].get("user") or {}
        self.token = token
        self.session.headers["authorization"] = f"Bearer {token}"
        log.info(
            "[%s] 登录成功 uid=%s token=%s",
            self.name,
            user.get("id"),
            mask_token(token),
        )
        return user

    def get_free_product(self):
        data = self._request("GET", "/api/v1/products/free")
        if not data.get("status"):
            raise RuntimeError(f"查询免费产品失败: {data.get('message')}")
        return data["data"]

    def do_sign(self):
        data = self._request(
            "POST",
            "/api/v1/operation/request",
            json={"order_quantity": ORDER_QUANTITY},
        )
        return data


# --------- 单账号流程 ---------
def run_account(account):
    name = account.get("name") or mask_phone(account["phone"])
    log.info("===== 处理账号: %s (%s) =====", name, mask_phone(account["phone"]))
    summary = {"name": name, "ok": False, "msg": "", "profit": 0, "total": "-"}

    try:
        client = CastClient(account)
        client.login()

        free = client.get_free_product()
        available = int(free.get("available_request") or 0)
        today_profit = free.get("today_profit")
        total_profit = free.get("total_profit")
        log.info(
            "[%s] 状态：今日剩余=%s 今日收益=%s 累计=%s 项目=%s",
            name,
            available,
            today_profit,
            total_profit,
            free.get("name"),
        )

        summary["total"] = total_profit

        if available <= 0:
            summary["ok"] = True
            summary["msg"] = f"今日已签到（剩余次数 0），累计 {total_profit}"
            log.info("[%s] 今日已签到，跳过", name)
            return summary

        # 签到
        result = client.do_sign()
        if not result.get("status"):
            summary["msg"] = f"签到失败: {result.get('message')}"
            log.warning("[%s] %s", name, summary["msg"])
            return summary

        profit = result["data"]["operation_service"].get("profit", 0)
        summary["ok"] = True
        summary["profit"] = profit
        summary["msg"] = f"签到成功 +{profit} 元"

        # 复查累计
        try:
            free2 = client.get_free_product()
            summary["total"] = free2.get("total_profit")
        except Exception:
            pass

        log.info(
            "[%s] %s（累计=%s）",
            name,
            summary["msg"],
            summary["total"],
        )
        return summary

    except Exception as e:
        summary["msg"] = f"异常: {e}"
        log.error("[%s] %s", name, summary["msg"])
        return summary


# --------- 青龙通知 ---------
def push_notify(title, body):
    """兼容青龙 notify.py：若不可用就只打印到 stdout。"""
    try:
        import notify  # type: ignore

        notify.send(title, body)
    except Exception:
        print("\n========== 推送 ==========")
        print(title)
        print(body)
        print("==========================")


# --------- 入口 ---------
def main():
    accounts = load_accounts()
    if not accounts:
        log.error(
            "未配置任何账号。请设置环境变量 CAST_ACCOUNTS 或在 ACCOUNTS 列表里填入账号。"
        )
        sys.exit(1)

    log.info("共 %d 个账号待处理", len(accounts))
    results = []
    for idx, acc in enumerate(accounts):
        results.append(run_account(acc))
        if idx != len(accounts) - 1:
            delay = random.randint(DEFAULT_DELAY_MIN, DEFAULT_DELAY_MAX)
            log.info("等待 %ss 处理下一个账号 ...", delay)
            time.sleep(delay)

    # 汇总通知
    lines = []
    ok_cnt = sum(1 for r in results if r["ok"])
    for r in results:
        flag = "✅" if r["ok"] else "❌"
        lines.append(f"{flag} {r['name']}: {r['msg']} | 累计 {r['total']}")
    body = "\n".join(lines)
    title = f"中航签到 {ok_cnt}/{len(results)} 成功"
    log.info("\n%s\n%s", title, body)
    push_notify(title, body)


if __name__ == "__main__":
    main()
