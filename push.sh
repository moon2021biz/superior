#!/bin/bash
# ============================================================
# html.ai — GitHub push + Cloudflare Pages 自動デプロイ
# 使い方: bash push.sh "更新内容のメモ"
# 例:     bash push.sh "SUPERIORスケジュール更新"
# ============================================================

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

MESSAGE="${1:-update: $(date '+%Y-%m-%d %H:%M')}"

echo ""
echo "📁 対象フォルダ: $REPO_DIR"
echo "📝 コミットメッセージ: $MESSAGE"
echo ""

# ===== STEP 1: GitHub push =====
CHANGED=$(git status --porcelain)
if [ -z "$CHANGED" ]; then
  echo "ℹ️  git変更なし — GitHub pushをスキップ"
else
  echo "📋 変更ファイル:"
  git status --short
  git add .
  git commit -m "$MESSAGE"
  git push origin main
  echo "✅ GitHub push 完了"
fi

echo ""
echo "🎉 完了！Cloudflare Pagesが自動でデプロイします"
echo "🌐 URL: https://superior-cud.pages.dev"
echo ""
