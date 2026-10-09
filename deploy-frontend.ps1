# AIFriends 前端部署脚本
# 功能：本地构建前端并上传到云服务器

# ==================== 配置区域 ====================
# 请根据实际情况修改以下配置，或创建 deploy-config.ps1 文件

# 本地路径配置
$PROJECT_ROOT = $PSScriptRoot            # 脚本所在目录（项目根目录）
$FRONTEND_DIR = Join-Path $PROJECT_ROOT "frontend"
$BUILD_OUTPUT = Join-Path $PROJECT_ROOT "backend\static\frontend"

# 服务器配置（如果存在 deploy-config.ps1，会从那里读取）
$SERVER_USER = "acs"                    # 服务器用户名
$SERVER_HOST = "tcserver"                # 服务器地址（可以是 IP 或域名）
$SERVER_PORT = "22"                      # SSH 端口（默认 22）
$SERVER_PATH = "~/AIFriends/backend/static/frontend"  # 服务器上的目标路径

# 尝试从配置文件读取（如果存在）
$CONFIG_FILE = Join-Path $PROJECT_ROOT "deploy-config.ps1"
if (Test-Path $CONFIG_FILE) {
    Write-Host "  从配置文件读取设置: deploy-config.ps1" -ForegroundColor Gray
    . $CONFIG_FILE
}

# ==================== 脚本开始 ====================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AIFriends 前端部署脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Node.js 和 npm
Write-Host "[1/4] 检查 Node.js 环境..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    $npmVersion = npm --version
    Write-Host "  ✓ Node.js: $nodeVersion" -ForegroundColor Green
    Write-Host "  ✓ npm: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 未找到 Node.js 或 npm，请先安装 Node.js" -ForegroundColor Red
    exit 1
}

# 2. 进入前端目录并构建
Write-Host ""
Write-Host "[2/4] 构建前端项目..." -ForegroundColor Yellow
Set-Location $FRONTEND_DIR

# 检查 node_modules 是否存在
if (-not (Test-Path "node_modules")) {
    Write-Host "  检测到未安装依赖，正在安装..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ 依赖安装失败" -ForegroundColor Red
        exit 1
    }
}

# 执行构建
Write-Host "  正在构建..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ 构建失败" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ 构建成功" -ForegroundColor Green

# 3. 检查构建产物
Write-Host ""
Write-Host "[3/4] 检查构建产物..." -ForegroundColor Yellow
if (-not (Test-Path $BUILD_OUTPUT)) {
    Write-Host "  ✗ 构建产物不存在: $BUILD_OUTPUT" -ForegroundColor Red
    exit 1
}

$fileCount = (Get-ChildItem -Path $BUILD_OUTPUT -Recurse -File).Count
Write-Host "  ✓ 找到 $fileCount 个文件" -ForegroundColor Green

# 4. 上传到服务器
Write-Host ""
Write-Host "[4/4] 上传到服务器..." -ForegroundColor Yellow
$serverInfo = "${SERVER_USER}@${SERVER_HOST}"
Write-Host "  服务器: $serverInfo" -ForegroundColor Gray
Write-Host "  目标路径: $SERVER_PATH" -ForegroundColor Gray
Write-Host ""

# 使用 scp 上传（需要配置 SSH 密钥或密码）
$scpCommand = "scp -r -P $SERVER_PORT `"$BUILD_OUTPUT\*`" ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"

Write-Host "  执行命令: $scpCommand" -ForegroundColor Gray
Write-Host "  提示: 如果使用密码，请输入服务器密码" -ForegroundColor Yellow
Write-Host ""

# 执行 scp 命令
try {
    Invoke-Expression $scpCommand
    $scpSuccess = $?
} catch {
    $scpSuccess = $false
}

if ($scpSuccess) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  ✓ 部署成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  文件已上传到: ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  ✗ 部署失败" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  可能的原因：" -ForegroundColor Yellow
    Write-Host "  1. SSH 连接失败（检查服务器地址和端口）" -ForegroundColor Yellow
    Write-Host "  2. 未配置 SSH 密钥（需要输入密码或配置密钥）" -ForegroundColor Yellow
    Write-Host "  3. 服务器路径不存在(需要在服务器上创建目录)" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# 返回项目根目录
Set-Location $PROJECT_ROOT
