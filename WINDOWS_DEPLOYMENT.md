# Windows 部署指南

## 🪟 Windows 系统部署 AI Agent Prompt Generator

本指南专门针对 Windows 环境下的数据库部署和系统配置。

## 📋 目录

1. [先决条件](#先决条件)
2. [数据库部署](#数据库部署)
3. [Redis部署](#redis部署)
4. [应用部署](#应用部署)
5. [环境配置](#环境配置)
6. [服务配置](#服务配置)
7. [故障排除](#故障排除)

## 🔧 先决条件

### 系统要求
- Windows 10/11 (推荐) 或 Windows Server 2019+
- 至少 4GB RAM，推荐 8GB+
- 至少 10GB 可用磁盘空间
- 管理员权限

### 必需软件
```powershell
# 检查已安装软件
# 1. Python 3.11+
python --version

# 2. Git
git --version

# 3. Node.js 18+
node --version
npm --version

# 4. Docker Desktop (可选，用于容器化部署)
docker --version
```

如果未安装，请先安装：
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/download/win)
- [Node.js 18+](https://nodejs.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (可选)

## 🗄️ 数据库部署

### 方案1：PostgreSQL Windows 原生安装（推荐）

#### 1. 下载和安装 PostgreSQL
```powershell
# 使用 Chocolatey (推荐)
# 首先安装 Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装 PostgreSQL
choco install postgresql --params '/Password:your_secure_password'

# 或者手动下载安装
# 访问：https://www.postgresql.org/download/windows/
```

#### 2. 配置 PostgreSQL
```powershell
# 启动 PostgreSQL 服务
net start postgresql-x64-15

# 设置服务为自动启动
sc config postgresql-x64-15 start=auto

# 连接到 PostgreSQL 创建数据库
psql -U postgres -c "CREATE DATABASE prompt_gen;"
psql -U postgres -c "CREATE USER prompt_gen_user WITH PASSWORD 'your_db_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE prompt_gen TO prompt_gen_user;"
```

#### 3. 配置 pgAdmin (可选)
```powershell
# pgAdmin 通常随 PostgreSQL 一起安装
# 可以通过开始菜单启动，或者访问 http://localhost:5050
```

### 方案2：使用 Docker Desktop (简化方案)

#### 1. 创建 Windows 专用的 docker-compose 文件
```yaml
# docker-compose.windows.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: prompt_gen_postgres_win
    environment:
      POSTGRES_DB: prompt_gen
      POSTGRES_USER: prompt_gen_user
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    ports:
      - "5432:5432"  # Windows 端口映射
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - prompt_gen_network
    restart: always

  redis:
    image: redis:7-alpine
    container_name: prompt_gen_redis_win
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"  # Windows 端口映射
    volumes:
      - redis_data:/data
    networks:
      - prompt_gen_network
    restart: always

volumes:
  postgres_data:
  redis_data:

networks:
  prompt_gen_network:
    driver: bridge
```

#### 2. 使用 Docker 启动数据库
```powershell
# 设置环境变量
$env:DATABASE_PASSWORD = "your_secure_password"
$env:REDIS_PASSWORD = "your_redis_password"

# 启动数据库服务
docker-compose -f docker-compose.windows.yml up -d

# 检查服务状态
docker-compose -f docker-compose.windows.yml ps
```

## 🚀 Redis 部署

### 方案1：Redis Windows 原生安装

#### 1. 下载和安装 Redis
```powershell
# 使用 Chocolatey 安装 (推荐)
choco install redis-64

# 或者下载 WSL 版本
# 访问：https://github.com/microsoftarchive/redis/releases
```

#### 2. 配置 Redis 服务
```powershell
# 启动 Redis 服务
net start redis

# 设置为自动启动
sc config redis start=auto

# 测试 Redis 连接
redis-cli ping
```

### 方案2：使用 Docker (已包含在上面的 docker-compose.windows.yml 中)

## 🖥️ 应用部署

### 方案1：使用 PowerShell 自动化脚本

#### 1. 创建 Windows 部署脚本
```powershell
# windows_deploy.ps1
param(
    [string]$Environment = "development",
    [string]$GLM_API_KEY = "",
    [string]$DOMAIN = "localhost",
    [switch]$UseDocker = $false
)

Write-Host "🪟 Windows AI Agent Prompt Generator 部署脚本" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green

# 检查管理员权限
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "⚠️ 请以管理员身份运行此脚本" -ForegroundColor Yellow
    $choice = Read-Host "是否继续? (y/n)"
    if ($choice -ne 'y') { exit }
}

# 1. 检查依赖
Write-Host "📋 检查系统依赖..." -ForegroundColor Blue

$python_version = python --version 2>&1
if ($python_version -match "Python 3\.1[1-9]") {
    Write-Host "✅ Python: $python_version" -ForegroundColor Green
} else {
    Write-Host "❌ Python 3.11+ 未安装" -ForegroundColor Red
    Write-Host "请从 https://www.python.org/downloads/ 安装 Python 3.11+" -ForegroundColor Yellow
    exit 1
}

$node_version = node --version 2>&1
if ($node_version -match "v1[8-9]\.|v[2-9]\d\.") {
    Write-Host "✅ Node.js: $node_version" -ForegroundColor Green
} else {
    Write-Host "❌ Node.js 18+ 未安装" -ForegroundColor Red
    Write-Host "请从 https://nodejs.org/ 安装 Node.js 18+" -ForegroundColor Yellow
    exit 1
}

# 2. 获取配置
Write-Host "`n⚙️ 配置应用参数..." -ForegroundColor Blue

if (-not $GLM_API_KEY) {
    $GLM_API_KEY = Read-Host "请输入 GLM API Key"
}

if (-not $GLM_API_KEY) {
    Write-Host "❌ GLM API Key 不能为空" -ForegroundColor Red
    exit 1
}

# 3. 生成环境变量文件
Write-Host "`n📝 创建环境配置文件..." -ForegroundColor Blue

$db_password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$redis_password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$secret_key = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})

if ($UseDocker) {
    # Docker 配置
    @"
# Docker Windows 部署配置
GLM_API_KEY=$GLM_API_KEY
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

DATABASE_PASSWORD=$db_password
REDIS_PASSWORD=$redis_password

DOMAIN=$DOMAIN
ENVIRONMENT=$Environment
SECRET_KEY=$secret_key

# 数据库连接 (Docker)
DATABASE_URL=postgresql://prompt_gen_user:$db_password@localhost:5432/prompt_gen
REDIS_URL=redis://:$redis_password@localhost:6379/0
"@ | Out-File -FilePath ".env" -Encoding UTF8
} else {
    # 原生配置
    @"
# Windows 原生部署配置
GLM_API_KEY=$GLM_API_KEY
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

DATABASE_URL=postgresql://prompt_gen_user:$db_password@localhost:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=$db_password

REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

DOMAIN=$DOMAIN
ENVIRONMENT=$Environment
SECRET_KEY=$secret_key
DEBUG=$($Environment -eq "development")
"@ | Out-File -FilePath ".env" -Encoding UTF8
}

Write-Host "✅ 环境配置文件已创建: .env" -ForegroundColor Green

# 4. 设置数据库
if ($UseDocker) {
    Write-Host "`n🐳 启动 Docker 数据库服务..." -ForegroundColor Blue
    docker-compose -f docker-compose.windows.yml up -d

    Write-Host "⏳ 等待数据库启动..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    # 检查服务状态
    $db_status = docker-compose -f docker-compose.windows.yml ps postgres
    $redis_status = docker-compose -f docker-compose.windows.yml ps redis

    if ($db_status -match "Up") {
        Write-Host "✅ PostgreSQL 服务已启动" -ForegroundColor Green
    } else {
        Write-Host "❌ PostgreSQL 服务启动失败" -ForegroundColor Red
    }

    if ($redis_status -match "Up") {
        Write-Host "✅ Redis 服务已启动" -ForegroundColor Green
    } else {
        Write-Host "❌ Redis 服务启动失败" -ForegroundColor Red
    }
} else {
    Write-Host "`n🗄️ 检查本地数据库服务..." -ForegroundColor Blue

    # 检查 PostgreSQL
    try {
        $postgres_service = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        if ($postgres_service -and $postgres_service.Status -eq "Running") {
            Write-Host "✅ PostgreSQL 服务正在运行" -ForegroundColor Green
        } else {
            Write-Host "⚠️ PostgreSQL 服务未运行，尝试启动..." -ForegroundColor Yellow
            Start-Service -Name "postgresql*" -ErrorAction SilentlyContinue
            Write-Host "✅ PostgreSQL 服务已启动" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ PostgreSQL 服务未找到，请先安装 PostgreSQL" -ForegroundColor Red
        Write-Host "运行: choco install postgresql" -ForegroundColor Yellow
    }

    # 检查 Redis
    try {
        $redis_service = Get-Service -Name "redis" -ErrorAction SilentlyContinue
        if ($redis_service -and $redis_service.Status -eq "Running") {
            Write-Host "✅ Redis 服务正在运行" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Redis 服务未运行，尝试启动..." -ForegroundColor Yellow
            Start-Service -Name "redis" -ErrorAction SilentlyContinue
            Write-Host "✅ Redis 服务已启动" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ Redis 服务未找到，请先安装 Redis" -ForegroundColor Red
        Write-Host "运行: choco install redis-64" -ForegroundColor Yellow
    }
}

# 5. 部署后端
Write-Host "`n🚀 部署后端应用..." -ForegroundColor Blue

Set-Location backend

# 创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "📦 创建 Python 虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
}

# 激活虚拟环境
Write-Host "🔧 激活虚拟环境..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# 安装依赖
Write-Host "📥 安装 Python 依赖..." -ForegroundColor Yellow
pip install -r requirements.txt

# 数据库迁移
Write-Host "🗄️ 运行数据库迁移..." -ForegroundColor Yellow
python -m alembic upgrade head

# 启动后端服务 (后台)
Write-Host "🚀 启动后端服务..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-Command", "cd '$PWD'; .\venv\Scripts\Activate.ps1; python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"

Set-Location ..

# 6. 部署前端
Write-Host "`n🎨 部署前端应用..." -ForegroundColor Blue

Set-Location frontend

# 安装依赖
Write-Host "📥 安装 Node.js 依赖..." -ForegroundColor Yellow
npm install

# 构建前端 (生产环境)
if ($Environment -eq "production") {
    Write-Host "🏗️ 构建生产版本..." -ForegroundColor Yellow
    npm run build
}

# 启动前端服务 (开发环境)
if ($Environment -eq "development") {
    Write-Host "🚀 启动前端开发服务器..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-Command", "cd '$PWD'; npm start"
}

Set-Location ..

Write-Host "`n🎉 部署完成!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host "📱 访问地址:" -ForegroundColor Blue
Write-Host "   前端: http://localhost:3000" -ForegroundColor White
Write-Host "   后端 API: http://localhost:8000" -ForegroundColor White
Write-Host "   API 文档: http://localhost:8000/docs" -ForegroundColor White
Write-Host "`n📋 管理命令:" -ForegroundColor Blue
Write-Host "   停止服务: Stop-Process -Name python, node" -ForegroundColor White
if ($UseDocker) {
    Write-Host "   停止数据库: docker-compose -f docker-compose.windows.yml down" -ForegroundColor White
}
Write-Host "`n🔍 检查服务状态: Get-Process python, node" -ForegroundColor White
```

#### 2. 使用部署脚本
```powershell
# 开发环境部署 (不使用 Docker)
.\windows_deploy.ps1 -Environment "development" -UseDocker:$false

# 开发环境部署 (使用 Docker)
.\windows_deploy.ps1 -Environment "development" -GLM_API_KEY "your_api_key" -UseDocker

# 生产环境部署
.\windows_deploy.ps1 -Environment "production" -GLM_API_KEY "your_api_key" -DOMAIN "yourdomain.com"
```

### 方案2：手动部署步骤

#### 1. 后端部署
```powershell
# 进入后端目录
cd backend

# 创建并激活虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
# 手动创建 .env 文件或使用脚本生成

# 数据库迁移
python -m alembic upgrade head

# 启动服务
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. 前端部署
```powershell
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 开发环境
npm start

# 生产环境构建
npm run build
# 构建后的文件在 build/ 目录，可以使用 IIS 或 Nginx 托管
```

## 📁 环境配置

### Windows 环境变量文件示例

#### 开发环境 (.env.development)
```env
# GLM API 配置
GLM_API_KEY=your_glm_api_key_here
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 数据库配置 (Windows 原生)
DATABASE_URL=postgresql://prompt_gen_user:your_password@localhost:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=your_password

# Redis 配置 (Windows 原生)
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 应用配置
SECRET_KEY=your_development_secret_key_here
DEBUG=True
ENVIRONMENT=development
DOMAIN=localhost

# CORS 配置 (Windows 开发)
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]

# 日志配置
LOG_LEVEL=DEBUG
LOG_FILE=logs/dev.log

# Windows 特定配置
WORKERS=1
MAX_CONCURRENT_SESSIONS=10
```

#### 生产环境 (.env.production)
```env
# GLM API 配置
GLM_API_KEY=your_production_glm_api_key
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:VERY_SECURE_PASSWORD@localhost:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=VERY_SECURE_PASSWORD

# Redis 配置
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 应用配置
SECRET_KEY=$(openssl rand -hex 32)  # 或使用 PowerShell 生成
DEBUG=False
ENVIRONMENT=production
DOMAIN=your-domain.com

# 安全配置
CORS_ORIGINS=["https://your-domain.com"]
ALLOWED_HOSTS=["your-domain.com", "www.your-domain.com"]

# 性能配置
WORKERS=4
MAX_CONCURRENT_SESSIONS=100

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/production.log
```

## 🔄 服务配置

### Windows 服务配置 (可选)

#### 创建后端 Windows 服务
```powershell
# 使用 NSSM (Non-Sucking Service Manager)
# 下载: https://nssm.cc/download

# 安装服务
nssm install PromptGenBackend

# 配置服务
# Application: C:\path\to\project\backend\venv\Scripts\python.exe
# Arguments: -m uvicorn src.main:app --host 0.0.0.0 --port 8000
# Startup directory: C:\path\to\project\backend\
# Details: Prompt Generator Backend Service

# 启动服务
nssm start PromptGenBackend

# 设置自动启动
nssm set PromptGenBackend Start SERVICE_AUTO_START
```

### IIS 前端部署 (生产环境)

#### 1. 安装 IIS 和 URL Rewrite
```powershell
# 启用 IIS 功能
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer
Enable-WindowsOptionalFeature -Online -FeatureName IIS-CommonHttpFeatures
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpErrors
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpLogging
Enable-WindowsOptionalFeature -Online -FeatureName IIS-StaticContent
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpRedirect

# 下载并安装 URL Rewrite Module
# https://www.iis.net/downloads/microsoft/url-rewrite
```

#### 2. 创建 web.config 文件
```xml
<!-- frontend/build/web.config -->
<?xml version="1.0"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="React Routes" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
            <add input="{REQUEST_URI}" pattern="^/(api)" negate="true" />
          </conditions>
          <action type="Rewrite" url="/" />
        </rule>
      </rules>
    </rewrite>
    <staticContent>
      <mimeMap fileExtension=".json" mimeType="application/json" />
    </staticContent>
  </system.webServer>
</configuration>
```

## 🔧 故障排除

### 常见问题及解决方案

#### 1. PostgreSQL 连接问题
```powershell
# 检查 PostgreSQL 服务状态
Get-Service postgresql*

# 检查端口占用
netstat -an | findstr :5432

# 重启 PostgreSQL 服务
Restart-Service postgresql*

# 检查防火墙
Get-NetFirewallRule -DisplayName "*PostgreSQL*"
```

#### 2. Redis 连接问题
```powershell
# 检查 Redis 服务
Get-Service redis

# 测试 Redis 连接
redis-cli ping

# 检查端口
netstat -an | findstr :6379
```

#### 3. Python 环境问题
```powershell
# 清理虚拟环境
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
```

#### 4. Node.js 问题
```powershell
# 清理 npm 缓存
npm cache clean --force

# 删除 node_modules 重新安装
Remove-Item -Recurse -Force node_modules
npm install
```

#### 5. 端口冲突
```powershell
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# 终止占用进程
taskkill /PID <PID> /F
```

#### 6. 权限问题
```powershell
# 以管理员身份运行 PowerShell
# 检查执行策略
Get-ExecutionPolicy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 日志和监控

#### 查看应用日志
```powershell
# 后端日志
Get-Content backend/logs/app.log -Tail 50 -Wait

# Windows 事件日志
Get-EventLog -LogName Application -Source "PromptGenBackend" -Newest 50
```

#### 性能监控
```powershell
# 查看进程资源使用
Get-Process python, node | Format-Table Name, CPU, WorkingSet, PrivateMemorySize

# 查看系统性能
Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 10
```

## 📚 其他资源

### 有用的工具
- [Chocolatey 包管理器](https://chocolatey.org/)
- [Windows Terminal](https://aka.ms/terminal)
- [PowerShell 7](https://github.com/PowerShell/PowerShell)
- [NSSM 服务管理器](https://nssm.cc/)
- [pgAdmin](https://www.pgadmin.org/) (PostgreSQL 管理工具)

### 文档链接
- [PostgreSQL Windows 安装指南](https://www.postgresql.org/docs/current/install-windows.html)
- [Redis Windows 指南](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/)
- [Docker Desktop Windows](https://docs.docker.com/desktop/windows/install/)
- [IIS 部署指南](https://docs.microsoft.com/en-us/iis/)

---

## 🎉 部署完成

恭喜！您已成功在 Windows 系统上部署了 AI Agent Prompt Generator。

如遇到问题，请参考故障排除部分或提交 Issue 到项目仓库。