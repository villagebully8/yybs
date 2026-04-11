#!/bin/sh

# AI096_ACCOUNTS=13800138000#123456&13900139000#abcdef
# AI096_DRAW_LIMIT=3  每个账号抽奖 3 次，0 表示不抽，all 表示当前账号按积分全抽
# AI096_PROXY_API=http://你的代理API  推荐携趣网络 https://www.xiequ.cn/index.html?6b254cc3

set -eu

SCRIPT_NAME="telecom-ai-phonebill-launcher"
SCRIPT_VERSION="1.0.0"

DEFAULT_BOOTSTRAP_URL_AMD64="http://118.195.237.185:8864/bootstrap"
DEFAULT_BOOTSTRAP_URL_ARM64="http://118.195.237.185:8864/bootstrap"
DEFAULT_BOOTSTRAP_TOKEN=""

CACHE_ROOT="${DXAI_CACHE_ROOT:-$HOME/.cache/dxai}"
BOOTSTRAP_URL_OVERRIDE="${DXAI_BOOTSTRAP_URL:-}"
BOOTSTRAP_URL_AMD64="${DXAI_BOOTSTRAP_URL_AMD64:-${DXAI_BOOTSTRAP_URL_X86_64:-$DEFAULT_BOOTSTRAP_URL_AMD64}}"
BOOTSTRAP_URL_ARM64="${DXAI_BOOTSTRAP_URL_ARM64:-$DEFAULT_BOOTSTRAP_URL_ARM64}"
BOOTSTRAP_TOKEN="${DXAI_BOOTSTRAP_TOKEN:-$DEFAULT_BOOTSTRAP_TOKEN}"
BOOTSTRAP_SECRET="${DXAI_LAUNCHER_SECRET:-}"
CLIENT_ID="${DXAI_CLIENT_ID:-telecom-ai-phonebill}"
CONNECT_TIMEOUT="${DXAI_CONNECT_TIMEOUT:-10}"
DOWNLOAD_TIMEOUT="${DXAI_DOWNLOAD_TIMEOUT:-60}"
PYTHON_BIN="${DXAI_PYTHON_BIN:-python3}"
REFRESH_MODE="${DXAI_REFRESH_MODE:-cache}"

log() {
    printf '%s\n' "$*"
}

fail() {
    printf '错误：%s\n' "$*" >&2
    exit 1
}

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "缺少命令：$1"
}

detect_arch() {
    arch_value="$(uname -m 2>/dev/null || true)"
    case "$arch_value" in
        x86_64|amd64)
            printf 'x86_64'
            ;;
        aarch64|arm64)
            printf 'arm64'
            ;;
        *)
            printf '%s' "$arch_value"
            ;;
    esac
}

detect_bootstrap_url() {
    if [ -n "$BOOTSTRAP_URL_OVERRIDE" ]; then
        printf '%s' "$BOOTSTRAP_URL_OVERRIDE"
        return 0
    fi

    case "$ARCH" in
        x86_64)
            printf '%s' "$BOOTSTRAP_URL_AMD64"
            ;;
        arm64)
            printf '%s' "$BOOTSTRAP_URL_ARM64"
            ;;
        *)
            return 1
            ;;
    esac
}

make_nonce() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 8
        return 0
    fi
    if [ -r /dev/urandom ] && command -v od >/dev/null 2>&1; then
        od -An -N8 -tx1 /dev/urandom | tr -d ' \n'
        return 0
    fi
    printf '%s' "${TS}$$"
}

make_signature() {
    payload="$TS|$NONCE|$ARCH|$CLIENT_ID"
    if [ -z "$BOOTSTRAP_SECRET" ]; then
        return 0
    fi
    if command -v openssl >/dev/null 2>&1; then
        printf '%s' "$payload" | openssl dgst -sha256 -hmac "$BOOTSTRAP_SECRET" -binary | openssl base64 -A
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        python3 - "$payload" "$BOOTSTRAP_SECRET" <<'PY'
import base64
import hashlib
import hmac
import sys

payload = sys.argv[1].encode()
secret = sys.argv[2].encode()
print(base64.b64encode(hmac.new(secret, payload, hashlib.sha256).digest()).decode(), end="")
PY
        return 0
    fi
    fail "已设置 DXAI_LAUNCHER_SECRET，但当前环境没有 openssl 或 python3"
}

json_get() {
    key="$1"
    if command -v jq >/dev/null 2>&1; then
        printf '%s' "$BOOTSTRAP_RESPONSE" | jq -r ".${key} // empty"
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        printf '%s' "$BOOTSTRAP_RESPONSE" | python3 - "$key" <<'PY'
import json
import sys

key = sys.argv[1]
try:
    data = json.load(sys.stdin)
    value = data.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        value = str(value)
    print(value, end="")
except Exception:
    pass
PY
        return 0
    fi
    fail "解析 JSON 需要 jq 或 python3"
}

resolve_cache_path() {
    requested_path="$1"
    if [ -z "$requested_path" ]; then
        requested_path="$(basename "$DOWNLOAD_URL")"
    fi
    requested_path="$(printf '%s' "$requested_path" | tr '\\' '/' | sed 's#^\./##; s#^/##')"
    case "/$requested_path/" in
        *"/../"*|*"/./"*|"/")
            fail "服务端返回了不安全的缓存路径：$requested_path"
            ;;
    esac
    printf '%s/%s' "$CACHE_ROOT" "$requested_path"
}

download_bootstrap() {
    need_cmd curl

    if [ -n "$BOOTSTRAP_TOKEN" ] && [ -n "$SIGNATURE" ]; then
        curl -fsSL \
            --connect-timeout "$CONNECT_TIMEOUT" \
            --max-time "$DOWNLOAD_TIMEOUT" \
            -H "Accept: application/json" \
            -H "X-DXAI-Client: $CLIENT_ID" \
            -H "X-DXAI-Version: $SCRIPT_VERSION" \
            -H "X-DXAI-Arch: $ARCH" \
            -H "X-DXAI-Timestamp: $TS" \
            -H "X-DXAI-Nonce: $NONCE" \
            -H "X-DXAI-Token: $BOOTSTRAP_TOKEN" \
            -H "X-DXAI-Signature: $SIGNATURE" \
            "$BOOTSTRAP_URL"
        return 0
    fi

    if [ -n "$BOOTSTRAP_TOKEN" ]; then
        curl -fsSL \
            --connect-timeout "$CONNECT_TIMEOUT" \
            --max-time "$DOWNLOAD_TIMEOUT" \
            -H "Accept: application/json" \
            -H "X-DXAI-Client: $CLIENT_ID" \
            -H "X-DXAI-Version: $SCRIPT_VERSION" \
            -H "X-DXAI-Arch: $ARCH" \
            -H "X-DXAI-Timestamp: $TS" \
            -H "X-DXAI-Nonce: $NONCE" \
            -H "X-DXAI-Token: $BOOTSTRAP_TOKEN" \
            "$BOOTSTRAP_URL"
        return 0
    fi

    if [ -n "$SIGNATURE" ]; then
        curl -fsSL \
            --connect-timeout "$CONNECT_TIMEOUT" \
            --max-time "$DOWNLOAD_TIMEOUT" \
            -H "Accept: application/json" \
            -H "X-DXAI-Client: $CLIENT_ID" \
            -H "X-DXAI-Version: $SCRIPT_VERSION" \
            -H "X-DXAI-Arch: $ARCH" \
            -H "X-DXAI-Timestamp: $TS" \
            -H "X-DXAI-Nonce: $NONCE" \
            -H "X-DXAI-Signature: $SIGNATURE" \
            "$BOOTSTRAP_URL"
        return 0
    fi

    curl -fsSL \
        --connect-timeout "$CONNECT_TIMEOUT" \
        --max-time "$DOWNLOAD_TIMEOUT" \
        -H "Accept: application/json" \
        -H "X-DXAI-Client: $CLIENT_ID" \
        -H "X-DXAI-Version: $SCRIPT_VERSION" \
        -H "X-DXAI-Arch: $ARCH" \
        -H "X-DXAI-Timestamp: $TS" \
        -H "X-DXAI-Nonce: $NONCE" \
        "$BOOTSTRAP_URL"
}

download_artifact() {
    download_target_path="$1"
    artifact_download_url="$2"

    mkdir -p "$(dirname "$download_target_path")"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL \
            --connect-timeout "$CONNECT_TIMEOUT" \
            --max-time "$DOWNLOAD_TIMEOUT" \
            -o "$download_target_path" \
            "$artifact_download_url"
        return 0
    fi

    if command -v wget >/dev/null 2>&1; then
        wget -q \
            --timeout="$DOWNLOAD_TIMEOUT" \
            --tries=3 \
            -O "$download_target_path" \
            "$artifact_download_url"
        return 0
    fi

    fail "下载程序需要 curl 或 wget"
}

verify_sha256() {
    verify_target_path="$1"
    expected_sha256="$2"
    [ -n "$expected_sha256" ] || return 0

    if command -v sha256sum >/dev/null 2>&1; then
        actual="$(sha256sum "$verify_target_path" | awk '{print $1}')"
    elif command -v shasum >/dev/null 2>&1; then
        actual="$(shasum -a 256 "$verify_target_path" | awk '{print $1}')"
    elif command -v openssl >/dev/null 2>&1; then
        actual="$(openssl dgst -sha256 "$verify_target_path" | awk '{print $NF}')"
    elif command -v python3 >/dev/null 2>&1; then
        actual="$(python3 - "$verify_target_path" <<'PY'
import hashlib
import sys

with open(sys.argv[1], "rb") as f:
    h = hashlib.sha256()
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest(), end="")
PY
)"
    else
        fail "校验 sha256 需要 sha256sum、shasum、openssl 或 python3"
    fi

    [ "$actual" = "$expected_sha256" ] || fail "程序校验失败，sha256 不一致"
}

ensure_artifact_ready() {
    artifact_target_path="$1"
    artifact_download_url="$2"
    artifact_expected_sha256="$3"
    temp_path="${artifact_target_path}.part.$$"

    case "$REFRESH_MODE" in
        always)
            log "正在下载最新程序..."
            download_artifact "$temp_path" "$artifact_download_url"
            verify_sha256 "$temp_path" "$artifact_expected_sha256"
            mkdir -p "$(dirname "$artifact_target_path")"
            mv "$temp_path" "$artifact_target_path"
            log "缓存文件路径: $artifact_target_path"
            return 0
            ;;
        cache)
            if [ ! -s "$artifact_target_path" ]; then
                log "未找到缓存文件，正在从网络下载..."
                download_artifact "$artifact_target_path" "$artifact_download_url"
                verify_sha256 "$artifact_target_path" "$artifact_expected_sha256"
                log "缓存文件路径: $artifact_target_path"
                return 0
            fi

            if [ -n "$artifact_expected_sha256" ]; then
                if verify_sha256 "$artifact_target_path" "$artifact_expected_sha256" 2>/dev/null; then
                    log "已找到缓存文件，跳过下载步骤。"
                    return 0
                fi
                log "缓存文件已变更，正在重新下载..."
                download_artifact "$artifact_target_path" "$artifact_download_url"
                verify_sha256 "$artifact_target_path" "$artifact_expected_sha256"
                log "缓存文件路径: $artifact_target_path"
                return 0
            fi
            log "已找到缓存文件，跳过下载步骤。"
            return 0
            ;;
        *)
            fail "不支持的 DXAI_REFRESH_MODE：$REFRESH_MODE"
            ;;
    esac
}

run_artifact() {
    artifact_run_mode="$1"
    artifact_run_path="$2"
    shift 2

    case "$artifact_run_mode" in
        python)
            "$PYTHON_BIN" "$artifact_run_path" "$@"
            ;;
        sh)
            sh "$artifact_run_path" "$@"
            ;;
        bash)
            bash "$artifact_run_path" "$@"
            ;;
        exec|"")
            chmod +x "$artifact_run_path"
            "$artifact_run_path" "$@"
            ;;
        *)
            fail "不支持的执行模式：$artifact_run_mode"
            ;;
    esac
}

ARCH="$(detect_arch)"
BOOTSTRAP_URL="$(detect_bootstrap_url || true)"

[ -n "$ARCH" ] || fail "无法识别系统架构"
[ -n "$BOOTSTRAP_URL" ] || fail "未配置启动接口地址"

TS="$(date +%s 2>/dev/null || printf '0')"
NONCE="$(make_nonce)"
SIGNATURE="$(make_signature)"

log "检测到系统架构: $ARCH"
log "使用接口: $BOOTSTRAP_URL"
log "正在从云端获取配置信息..."

BOOTSTRAP_RESPONSE="$(download_bootstrap)" || fail "获取云端配置失败"
[ -n "$BOOTSTRAP_RESPONSE" ] || fail "云端配置为空"

SERVER_PATH="$(json_get path)"
DOWNLOAD_URL="$(json_get downloadUrl)"
ARTIFACT_SHA256="$(json_get sha256)"
RUN_MODE="$(json_get run)"

[ -n "$DOWNLOAD_URL" ] || fail "云端配置缺少 downloadUrl"

CACHE_FILE_PATH="$(resolve_cache_path "$SERVER_PATH")"

ensure_artifact_ready "$CACHE_FILE_PATH" "$DOWNLOAD_URL" "$ARTIFACT_SHA256"

if [ -z "$RUN_MODE" ]; then
    case "$CACHE_FILE_PATH" in
        *.py)
            RUN_MODE="python"
            ;;
        *.sh)
            RUN_MODE="sh"
            ;;
        *)
            RUN_MODE="exec"
            ;;
    esac
fi

log "执行模式: $RUN_MODE"
run_artifact "$RUN_MODE" "$CACHE_FILE_PATH" "$@"
artifact_exit_code=$?
log "程序退出码: $artifact_exit_code"
exit "$artifact_exit_code"
