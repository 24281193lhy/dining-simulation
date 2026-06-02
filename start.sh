#!/bin/bash
#
# 北交大食堂仿真系统 - 一键启动脚本
# 支持从任意路径启动，不依赖当前工作目录
#

set -e

# 自动检测脚本所在目录（无论从哪里调用）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 项目根目录
PROJECT_DIR="${SCRIPT_DIR}"

# Python 路径（优先使用 venv，否则使用系统 python）
if [ -f "${PROJECT_DIR}/.venv/bin/python3" ]; then
    PYTHON="${PROJECT_DIR}/.venv/bin/python3"
elif [ -f "${PROJECT_DIR}/.venv/bin/python" ]; then
    PYTHON="${PROJECT_DIR}/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

# 日志目录
LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOG_DIR}"

PID_FILE="${LOG_DIR}/canteen_sim.pid"

# 切到项目目录运行（确保 Python 包导入正常）
cd "${PROJECT_DIR}"

echo "============================================="
echo "   北交大食堂仿真系统"
echo "   Starting..."
echo "============================================="

# 停止已运行的实例
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}" 2>/dev/null || true)
    if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "[INFO] 停止旧进程 PID=${OLD_PID}"
        kill "${OLD_PID}" 2>/dev/null || true
        sleep 1
    fi
fi

# 检查依赖
check_and_install() {
    if ! ${PYTHON} -c "import flask" 2>/dev/null; then
        echo "[INFO] 正在安装依赖..."
        ${PYTHON} -m pip install -r "${PROJECT_DIR}/requirements.txt" -q
    fi
}
check_and_install

# 启动
echo "[INFO] Python: ${PYTHON}"
echo "[INFO] 端口: 8082"
echo "[INFO] 访问: http://localhost:8082"

nohup ${PYTHON} -m canteen_sim > "${LOG_DIR}/app.log" 2>&1 &

echo $! > "${PID_FILE}"
echo "[OK] 仿真系统已启动，PID: $(cat ${PID_FILE})"
echo "[OK] 日志文件: ${LOG_DIR}/app.log"
echo "============================================="
