

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册下载链接：https://pengo.pro/register?invite_code=QJEWR

Pengo (app.pengo.pro) 青龙面板脚本 —— 登录 / 激活 / 矿机领取 / 下级收益领取 / 升级

cron 建议（每日两次领取，收益按秒累积，自动入账周期 24h）：
    15 8,20 * * *
    15 8 * * *      # 只要升级和领取一次的话

============================ 环境变量 ============================
PENGO_ACCOUNTS      必填(二选一)。多账号，每行一个，格式：邮箱#密码
                    也支持 邮箱,密码 / 邮箱:密码，或一行多账号用 & 分隔
PENGO_TOKENS        可选(二选一)。直接给 Bearer token，每行一个（不想存密码时用）
PENGO_AUTO_UPGRADE  可选，true/false，默认 true：余额够就自动逐级升级
PENGO_CLAIM_TEAM    可选，true/false，默认 true：领取下级收益（直推 direct + 间推 indirect）

====================== 青龙依赖安装 ======================
面板 → 依赖管理 → Python3 → 添加并安装：curl_cffi
（app.pengo.pro 有 Cloudflare 托管挑战，普通 requests 会 403「Just a moment...」，
  必须用 curl_cffi 的浏览器 TLS 指纹。装不上则回退 tls_client / requests，成功率下降）
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BASE = "https://app.pengo.pro"
UNIT = 1_000_000  # 服务端 units / 1e6 == formatted

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.environ.get("PENGO_CACHE_DIR") or os.path.join(HERE, ".pengo_cache")

# ---------------------------------------------------------------- 依赖选择
IMPL = ""
IMPERSONATE = ""


DEF_UA = ("Mozilla/5.0 (Linux; Android 16; 2410DPN6CC Build/BP2A.250605.031.A3; wv) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.7871.181 Mobile Safari/537.36")


def _new_http_session(proxy: str | None = None):
    """建会话，优先带浏览器 TLS 指纹的实现（Cloudflare 校验 JA3）。"""
    global IMPL, IMPERSONATE
    try:
        from curl_cffi import requests as _r

        for target in ("chrome131", "chrome124", "chrome120", "chrome116"):
            try:
                s = _r.Session(impersonate=target)
                if proxy:
                    s.proxies = {"http": proxy, "https": proxy}
                IMPL, IMPERSONATE = "curl_cffi", target
                return s
            except Exception:
                continue
    except ImportError:
        pass
    try:
        import tls_client  # type: ignore

        for kwargs in ({"client_identifier": "chrome_120", "random_tls_extension_order": True, "proxy": proxy},
                       {"client_identifier": "chrome_120", "random_tls_extension_order": True,
                        "proxies": {"http": proxy, "https": proxy}}):
            if not proxy:
                kwargs.pop("proxy", None)
                kwargs.pop("proxies", None)
            try:
                s = tls_client.Session(**kwargs)
                IMPL, IMPERSONATE = "tls_client", "chrome_120"
                return s
            except Exception:
                continue
    except ImportError:
        pass
    import requests as _rq

    s = _rq.Session()
    s.headers.update({"User-Agent": DEF_UA, "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": '"Android"'})
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    IMPL, IMPERSONATE = "requests", ""
    return s


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    raw = env(name)
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes", "y", "on", "是", "开")


def env_int(name: str, default: int) -> int:
    try:
        return int(env(name) or default)
    except ValueError:
        return default


def log(msg: str, tag: str = "") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} [{tag}] {msg}" if tag else f"{ts} {msg}", flush=True)


def jwt_exp(token: str):
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part)).get("exp")
    except Exception:
        return None


def token_alive(token: str, skew: int = 300) -> bool:
    exp = jwt_exp(token or "")
    return bool(exp) and exp - int(time.time()) > skew


def mask(s: str) -> str:
    if not s:
        return ""
    if "@" in s:
        name, _, dom = s.partition("@")
        return f"{name[:2]}***@{dom}"
    return s[:6] + "***"


def is_empty_reward(e: "ApiError") -> bool:
    """400 +『暂无可领取』= 当前没有收益，属正常状态而非错误。"""
    return getattr(e, "status", None) == 400 and ("暂无可领取" in (getattr(e, "message", "") or ""))


def fmt_units(units: int | float) -> str:
    return f"{units / UNIT:.8f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- 异常
class ApiError(Exception):
    def __init__(self, code: str, message: str, status=None):
        super().__init__(f"[{code}] {message}")
        self.code, self.message, self.status = code, message, status


class AuthExpired(ApiError):
    pass


# ---------------------------------------------------------------- 单账号
class PengoAccount:
    def __init__(self, email: str = "", password: str = "", token: str = ""):
        self.email = email
        self.password = password
        self.token = token
        self.tag = mask(email) if email else "token:" + (token[:6] if token else "?")
        self.proxy = env("PENGO_PROXY") or None
        self.notes: list[str] = []
        self._new_session()
        if not self.token:
            self._load_cache()

    # --- 会话
    def _new_session(self):
        self.s = _new_http_session(self.proxy)
        try:
            self.s.headers.update({
                "Accept": "*/*",
                "Accept-Language": "zh-CN",
                "Origin": "https://localhost",
                "Referer": "https://localhost/",
                "X-Requested-With": "pengo.pro",
            })
        except Exception:
            pass

    # --- token 缓存
    def _cache_path(self) -> str:
        key = base64.urlsafe_b64encode((self.email or "token").encode()).decode().rstrip("=")
        return os.path.join(CACHE_DIR, f"{key}.json")

    def _load_cache(self) -> None:
        try:
            with open(self._cache_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            if token_alive(data.get("token", "")):
                self.token = data["token"]
        except Exception:
            pass

    def _save_cache(self) -> None:
        if not self.token or not self.email:
            return
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(self._cache_path(), "w", encoding="utf-8") as f:
                json.dump({"token": self.token, "email": self.email, "savedAt": int(time.time())}, f)
            os.chmod(self._cache_path(), 0o600)
        except Exception:
            pass

    # --- 请求
    def request(self, method: str, path: str, body=None, auth: bool = True, retry_auth: bool = True):
        url = BASE + path
        payload = json.dumps(body if body is not None else {}, ensure_ascii=False).encode() if method == "POST" else None
        last = None
        for attempt in range(3):
            headers = {}
            if auth:
                if not self.token:
                    raise AuthExpired("no_token", "没有可用 token")
                headers["Authorization"] = f"Bearer {self.token}"
            if method == "POST":
                headers["Content-Type"] = "application/json"
            try:
                r = self.s.request(method, url, headers=headers, data=payload, timeout=25)
            except Exception as e:
                last = ApiError("network", f"{type(e).__name__}: {e}")
                time.sleep(1.5 * (attempt + 1))
                continue

            text = getattr(r, "text", "") or ""
            if r.status_code == 403 and "Just a moment" in text:
                last = ApiError("cloudflare", "Cloudflare 挑战拦截（换 IP / 确认 curl_cffi 已装）", 403)
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = ApiError(f"http_{r.status_code}", text[:150], r.status_code)
                time.sleep(1.5 * (attempt + 1))
                continue

            try:
                data = r.json()
            except Exception:
                raise ApiError(f"http_{r.status_code}", f"响应非 JSON: {text[:150]}", r.status_code)

            err = (data or {}).get("error") or {}
            code = err.get("code")
            if r.status_code == 401 or code == "unauthorized":
                if auth and retry_auth and self.email and self.password:
                    self.login()
                    return self.request(method, path, body, auth, retry_auth=False)
                raise AuthExpired(code or "unauthorized", err.get("message") or "登录失效")
            if not r.ok or "data" not in data:
                raise ApiError(code or f"http_{r.status_code}", err.get("message") or text[:150], r.status_code)
            return data["data"]
        raise last or ApiError("unknown", "请求失败")

    def login(self) -> dict:
        data = self.request("POST", "/api/v1/auth/login",
                            {"email": self.email, "password": self.password}, auth=False)
        self.token = data.get("token") or ""
        if not self.token:
            raise ApiError("login_failed", "登录未返回 token")
        self._save_cache()
        u = data.get("user") or {}
        self.notes.append(f"登录成功(user={u.get('id') or u.get('userId') or '?'})")
        return data

    def ensure_login(self) -> None:
        if token_alive(self.token):
            return
        if not (self.email and self.password):
            raise AuthExpired("token_expired", "token 已过期且未配置账号密码，无法续期")
        self.login()

    # --- 业务
    def miner(self):
        return self.request("GET", "/api/v1/miner")

    def summarize(self) -> str:
        m = self.miner()
        return (f"Lv{m.get('level')} 余额{m.get('balance', {}).get('formatted')} | "
                f"今日已领{m.get('todayClaimedPengu', {}).get('formatted')} | "
                f"待领{m.get('claimable', {}).get('formatted')}")

    def activate_if_needed(self, m: dict) -> dict:
        if m.get("activated"):
            return m
        log("矿机未激活，执行激活", self.tag)
        res = self.request("POST", "/api/v1/miner/activate", {})
        reward = res.get("reward", {})
        self.notes.append(f"激活成功+{reward.get('formatted')}{reward.get('symbol', '')}")
        return res.get("miner") or m

    def do_claim(self, force: bool = False) -> None:
        m = self.miner()
        m = self.activate_if_needed(m)
        claimable = m.get("claimable", {}).get("units", 0)
        energy = m.get("claimableEnergy", {}).get("units", 0)
        if claimable <= 0 and energy <= 0 and not force:
            log("无可领取额度，跳过", self.tag)
            return
        log(f"领取 {m.get('claimable', {}).get('formatted')} PENGU / "
            f"{m.get('claimableEnergy', {}).get('formatted')} ENERGY", self.tag)
        res = self.request("POST", "/api/v1/miner/claim", {})
        got = res.get("claimed", {})
        got_e = res.get("claimedEnergy", {})
        bal = (res.get("miner") or {}).get("balance", {})
        self.notes.append(f"领取{got.get('formatted')}{got.get('symbol', '')}/"
                          f"{got_e.get('formatted')}{got_e.get('symbol', '')}→余额{bal.get('formatted')}")
        log(f"领取成功，余额 {bal.get('formatted')}", self.tag)

    def team_summary(self) -> dict:
        return self.request("GET", "/api/v1/team/summary")

    def claim_team_type(self, kind: str) -> dict | None:
        """领取一种团队收益（direct=下级直推 / indirect=下级间推）。
        服务端在无可领取时返回 400 bad_request『暂无可领取团队奖励』——那是正常状态，不算失败。"""
        try:
            return self.request("POST", "/api/v1/team/claim", {"type": kind})
        except ApiError as e:
            if is_empty_reward(e):
                return None
            raise

    def do_team_claim(self) -> None:
        s = self.team_summary()
        d = (s.get("direct") or {}).get("claimable", {}).get("units", 0)
        i = (s.get("indirect") or {}).get("claimable", {}).get("units", 0)
        d_cnt = (s.get("direct") or {}).get("memberCount", 0)
        i_cnt = (s.get("indirect") or {}).get("memberCount", 0)
        log(f"下级收益：直推{d_cnt}人可领 {d / UNIT:.8f}，间推{i_cnt}人可领 {i / UNIT:.8f}", self.tag)

        if d <= 0 and i <= 0:
            log("下级收益无可领取额度", self.tag)
            return

        total = 0.0
        got_parts = []
        for kind, units, label in (("direct", d, "下级直推"), ("indirect", i, "下级间推")):
            if units <= 0:
                continue
            res = self.claim_team_type(kind)
            if res is None:
                log(f"{label} 领取时已无额度", self.tag)
                continue
            amt = (res.get("claimed") or {}).get("units", 0)
            avail = (res.get("wallet") or {}).get("available", {}).get("formatted")
            total += amt / UNIT
            got_parts.append(f"{label}{amt / UNIT:.8f}")
            log(f"{label}领取成功 +{amt / UNIT:.8f} PENGU，余额 {avail}", self.tag)
            self.notes.append(f"{label}+{amt / UNIT:.8f}PENGU")

        if got_parts:
            self.notes.append(f"下级收益合计+{total:.8f}PENGU")
            log(f"下级收益合计 +{total:.8f} PENGU", self.tag)

    def do_upgrade(self, to: int | None) -> None:
        info = self.request("GET", "/api/v1/miner/upgrade-info")
        cur = info.get("currentLevel", 1)
        bal_units = info.get("balance", {}).get("units", 0)
        bal_txt = info.get("balance", {}).get("formatted")
        levels = {lv["level"]: lv for lv in info.get("levels", [])}
        if not levels:
            log("未取到等级表，跳过升级", self.tag)
            return
        top = max(levels)
        if to:
            top = min(top, to)
        log(f"升级检查：当前 Lv{cur}，余额 {bal_txt} PENGU，目标上限 Lv{top}", self.tag)
        upgraded = []
        sim = bal_units
        for lv in range(cur + 1, top + 1):
            cost = (levels.get(lv) or {}).get("upgradeCost", {}).get("units")
            if cost is None:
                break
            if cost > sim:
                log(f"Lv{lv} 需要 {cost / UNIT:.2f} PENGU，余额不足，停止升级", self.tag)
                break
            try:
                res = self.request("POST", "/api/v1/miner/upgrade", {"targetLevel": lv})
            except ApiError as e:
                log(f"升级 Lv{lv} 失败：{e}", self.tag)
                self.notes.append(f"升级Lv{lv}失败({e.code})")
                break
            sim -= cost
            real = res.get("miner") or res
            upgraded.append(lv)
            log(f"升级成功 → Lv{real.get('level')}，余额 {real.get('balance', {}).get('formatted')}", self.tag)
        if upgraded:
            self.notes.append("升级至 Lv" + ",".join(map(str, upgraded)))
        else:
            log("无可升级等级", self.tag)

    # --- 主流程
    def run(self) -> dict:
        result = {"tag": self.tag, "ok": False, "summary": "", "error": "", "notes": self.notes}
        try:
            self.ensure_login()
            m = self.miner()
            m = self.activate_if_needed(m)
            self.do_claim(force=env_bool("PENGO_FORCE_CLAIM"))
            if env_bool("PENGO_CLAIM_TEAM", True):
                try:
                    self.do_team_claim()
                except ApiError as e:
                    if is_empty_reward(e):
                        log("下级收益无可领取", self.tag)
                    else:
                        log(f"下级收益领取忽略异常：{e}", self.tag)
            if env_bool("PENGO_AUTO_UPGRADE", True):
                self.do_upgrade(env_int("PENGO_UPGRADE_TO", 0) or None)
            result["summary"] = self.summarize()
            result["ok"] = True
            log(f"完成 | {result['summary']}", self.tag)
        except ApiError as e:
            result["error"] = str(e)
            log(f"失败：{e}", self.tag)
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            log(f"异常：{e}", self.tag)
            print(traceback.format_exc())
        result["notes"] = self.notes
        return result


# ---------------------------------------------------------------- 账号解析
def parse_targets() -> list[PengoAccount]:
    accounts: list[PengoAccount] = []
    raw = env("PENGO_ACCOUNTS")
    if raw:
        chunks = [c for line in raw.replace("&", "\n").replace("；", "\n").splitlines() for c in [line.strip()] if c]
        for item in chunks:
            for sep in ("#", ",", "，", ":"):
                if sep in item:
                    email, _, pwd = item.partition(sep)
                    email, pwd = email.strip(), pwd.strip()
                    if email and pwd:
                        accounts.append(PengoAccount(email=email, password=pwd))
                        break
            else:
                log(f"跳过无法解析的账号条目：{mask(item)}")

    tokens_raw = env("PENGO_TOKENS") or env("PENGO_TOKEN")
    if tokens_raw:
        for t in [x.strip() for x in tokens_raw.replace("&", "\n").splitlines() if x.strip()]:
            accounts.append(PengoAccount(token=t))

    if not accounts and env("PENGO_EMAIL") and env("PENGO_PASSWORD"):
        accounts.append(PengoAccount(email=env("PENGO_EMAIL"), password=env("PENGO_PASSWORD")))
    return accounts


def notify(title: str, content: str) -> None:
    if not env_bool("PENGO_NOTIFY", True):
        return
    try:
        import importlib

        for mod in ("notify", "sendNotify"):
            try:
                m = importlib.import_module(mod)
                fn = getattr(m, "send", None) or getattr(m, "sendNotify", None)
                if fn:
                    fn(title, content)
                    log("通知已发送")
                    return
            except ImportError:
                continue
        log("未找到青龙 notify 模块，跳过通知")
    except Exception as e:
        log(f"通知发送失败（忽略）：{e}")


def main() -> int:
    started = time.time()
    _new_http_session()  # 预热：确定 HTTP 实现后再打印，避免并发下取值竞态
    log(f"Pengo 青龙任务启动 | HTTP 实现={IMPL}"
        + (f"(impersonate={IMPERSONATE})" if IMPERSONATE else " ← 无 TLS 指纹，可能被 Cloudflare 拦"))
    if IMPL == "requests":
        log("提示：请在青龙『依赖管理 → Python3』安装 curl_cffi 以提高成功率")

    targets = parse_targets()
    if not targets:
        log("未配置账号：请设置 PENGO_ACCOUNTS（邮箱#密码，多行）或 PENGO_TOKENS")
        return 1

    log(f"共 {len(targets)} 个账号，并发 {env_int('PENGO_CONCURRENCY', 3)}")
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, env_int("PENGO_CONCURRENCY", 3))) as pool:
        for res in pool.map(lambda a: a.run(), targets):
            results.append(res)

    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    lines = [f"成功 {len(ok)} / 失败 {len(bad)} / 共 {len(results)}，耗时 {int(time.time() - started)}s", ""]
    for r in results:
        head = "✅" if r["ok"] else "❌"
        lines.append(f"{head} {r['tag']}")
        if r.get("notes"):
            lines.append("   " + "；".join(r["notes"]))
        if r.get("summary"):
            lines.append(f"   {r['summary']}")
        if r.get("error"):
            lines.append(f"   错误：{r['error']}")
    content = "\n".join(lines)
    print("\n" + content + "\n")
    notify("Pengo 每日任务", content)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())

