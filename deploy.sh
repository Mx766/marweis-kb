#!/bin/bash
# deploy.sh — 一键部署脚本
# 用法: 本地执行 ./deploy.sh，自动 push 到服务器并重启服务

set -e

SERVER="mx766@192.168.60.175"
PROJECT_DIR="/home/mx766/marweis-kb"
SERVICE_NAME="marweis-kb"

echo "=== 推送代码 ==="
git push origin master
git push server master

echo ""
echo "=== 服务器拉取 + 重启服务 ==="
ssh -o PasswordAuthentication=no "$SERVER" << 'REMOTE'
  set -e
  cd /home/mx766/marweis-kb
  echo "[1/3] git pull..."
  git pull origin master

  echo "[2/3] 重启后端..."
  # 如果用了 systemd:
  # sudo systemctl restart marweis-kb
  # 如果用了 nohup/screen/tmux，以下方式：
  pkill -f "uvicorn app.main:app" 2>/dev/null || true
  sleep 1
  cd backend
  source .venv/bin/activate 2>/dev/null || true
  nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > /home/mx766/logs/backend.log 2>&1 &
  echo "    后端已启动 (PID $!)"

  echo "[3/3] 完成!"
  echo "    后端: http://192.168.60.175:8000"
  echo "    前端已构建在 dist/"
REMOTE

echo ""
echo "=== 部署完成 ==="
