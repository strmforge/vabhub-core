#!/bin/bash

# VabHub-Core 版本标签创建脚本

set -e

VERSION="1.3.0"
TAG_NAME="v${VERSION}"
COMMIT_MESSAGE="Release VabHub-Core version ${VERSION}"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}创建 VabHub-Core ${VERSION} 版本标签${NC}"

# 检查当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "当前分支: ${CURRENT_BRANCH}"

# 检查是否有未提交的更改
if [[ -n $(git status --porcelain) ]]; then
    echo "检测到未提交的更改，请先提交更改"
    git status
    exit 1
fi

# 拉取最新更改
echo "拉取最新更改..."
git pull origin ${CURRENT_BRANCH}

# 检查标签是否已存在
if git rev-parse "${TAG_NAME}" >/dev/null 2>&1; then
    echo "标签 ${TAG_NAME} 已存在"
    read -p "是否删除并重新创建? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "${TAG_NAME}"
        git push --delete origin "${TAG_NAME}" 2>/dev/null || true
    else
        echo "操作取消"
        exit 0
    fi
fi

# 创建带注释的标签
echo "创建版本标签 ${TAG_NAME}..."
git tag -a "${TAG_NAME}" -m "${COMMIT_MESSAGE}"

# 推送标签到远程
echo "推送标签到远程仓库..."
git push origin "${TAG_NAME}"

echo -e "${GREEN}版本标签创建成功!${NC}"
echo ""
echo "下一步操作:"
echo "1. GitHub 会自动触发 Release 工作流"
echo "2. 等待构建和测试完成"
echo "3. 检查 Release 页面: https://github.com/vabhub/vabhub-core/releases"
echo "4. 验证发布包和 Docker 镜像"
echo ""
echo "标签信息:"
echo "- 版本: ${VERSION}"
echo "- 标签: ${TAG_NAME}"
echo "- 提交信息: ${COMMIT_MESSAGE}"