# Windows AI Agent Prompt Generator 部署脚本
# 作者: Claude Code
# 版本: 1.0.0

param(
    [string]$Environment = "development",
    [string]$GLM_API_KEY = "",
    [string]$DOMAIN = "localhost",
    [switch]$UseDocker = $false,
    [switch]$SkipDatabase = $false,
    [switch]$Help = $false
)

# 显示帮助信息
if ($Help) {
    Write-Host "🪟 Windows AI Agent Prompt Generator 部署脚本" -ForegroundColor Green
    Write-Host "=================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "用法:" -ForegroundColor White
    Write-Host "  .\windows_deploy.ps1 [参数]" -ForegroundColor Gray
    Write-Host ""
    Write-Host "参数:" -ForegroundColor White
    Write-Host "  -Environment <string>    部署环境 (development|production) [默认: development]" -ForegroundColor Gray
    Write-Host "  -GLM_API_KEY <string>    GLM API 密钥" -ForegroundColor Gray
    Write-Host "  -DOMAIN <string>         域名 [默认: localhost]" -ForegroundColor Gray
    Write-Host "  -UseDocker              使用 Docker 部署数据库" -ForegroundColor Gray
    Write-Host "  -SkipDatabase           跳过数据库部署" -ForegroundColor Gray
    Write-Host "  -Help                   显示此帮助信息" -ForegroundColor Gray
    Write-Host ""
    Write-Host "示例:" -ForegroundColor White
    Write-Host "  .\windows_deploy.ps1 -Environment development -UseDocker" -ForegroundColor Gray
    Write-Host "  .\windows_deploy.ps1 -Environment production -GLM_API_KEY 'your_key' -DOMAIN 'example.com'" -ForegroundColor Gray
    Write-Host "  .\windows_deploy.ps1 -SkipDatabase -Environment development" -ForegroundColor Gray
    exit 0
}

# 颜色主题配置
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Blue"
    Title = "Cyan"
    White = "White"
}

# 辅助函数
function Write-ColorText {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Colors[$Color]
}

function Write-Section {
    param([string]$Title)
    Write-Host "`n📋 $Title" -ForegroundColor $Colors.Info
    Write-Host ("-" * 50) -ForegroundColor $Colors.Info
}

function Write-Step {
    param([string]$Step)
    Write-Host "🔧 $Step" -ForegroundColor $Colors.Title
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Colors.Success
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️ $Message" -ForegroundColor $Colors.Warning
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Colors.Error
}

function Test-Command {
    param([string]$Command)
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Read-SecureInput {
    param([string]$Prompt, [string]$DefaultValue = "")
    $input = Read-Host "$Prompt"
    if ([string]::IsNullOrEmpty($input)) {
        return $DefaultValue
    }
    return $input
}

# 主程序开始
Write-ColorText "🪟 Windows AI Agent Prompt Generator 部署脚本" "Success"
Write-ColorText "=================================================" "Success"
Write-Host ""

# 显示配置信息
Write-Host "📋 部署配置:" -ForegroundColor $Colors.Info
Write-Host "   环境: $Environment" -ForegroundColor $Colors.White
Write-Host "   域名: $DOMAIN" -ForegroundColor $Colors.White
Write-Host "   使用 Docker: $UseDocker" -ForegroundColor $Colors.White
Write-Host "   跳过数据库: $SkipDatabase" -ForegroundColor $Colors.White
Write-Host ""

# 检查管理员权限
Write-Section "检查权限和依赖"

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "请以管理员身份运行此脚本以获得最佳体验"
    $choice = Read-Host "是否继续? (y/n)"
    if ($choice -ne 'y') {
        Write-Error "部署已取消"
        exit 1
    }
} else {
    Write-Success "管理员权限检查通过"
}

# 检查系统依赖
$dependencies = @(
    @{ Name = "Python 3.11+"; Command = "python"; Version = "--version"; Pattern = "Python 3\.1[1-9]" },
    @{ Name = "Git"; Command = "git"; Version = "--version"; Pattern = "" },
    @{ Name = "Node.js 18+"; Command = "node"; Version = "--version"; Pattern = "v1[8-9]\.|v[2-9]\d\." },
    @{ Name = "PowerShell 7+"; Command = "pwsh"; Version = "--version"; Pattern = "PowerShell 7\." }
)

$missingDeps = @()
foreach ($dep in $dependencies) {
    if (Test-Command $dep.Command) {
        try {
            $version = & $dep.Command $dep.Version 2>&1
            if ([string]::IsNullOrEmpty($dep.Pattern) -or $version -match $dep.Pattern) {
                Write-Success "$($dep.Name): $version"
            } else {
                Write-Warning "$($dep.Name): 版本不符合要求 ($version)"
                $missingDeps += $dep.Name
            }
        } catch {
            Write-Error "$($dep.Name): 检查失败"
            $missingDeps += $dep.Name
        }
    } else {
        Write-Error "$($dep.Name): 未安装"
        $missingDeps += $dep.Name
    }
}

if ($missingDeps.Count -gt 0) {
    Write-Host "`n❌ 缺少以下依赖:" -ForegroundColor $Colors.Error
    $missingDeps | ForEach-Object { Write-Host "   - $_" -ForegroundColor $Colors.White }
    Write-Host "`n请安装缺少的依赖后重试:" -ForegroundColor $Colors.Warning
    Write-Host "   Python: https://www.python.org/downloads/" -ForegroundColor $Colors.White
    Write-Host "   Git: https://git-scm.com/download/win" -ForegroundColor $Colors.White
    Write-Host "   Node.js: https://nodejs.org/" -ForegroundColor $Colors.White
    Write-Host "   PowerShell: https://github.com/PowerShell/PowerShell" -ForegroundColor $Colors.White
    exit 1
}

# 检查 Docker (如果需要)
if ($UseDocker) {
    if (Test-Command "docker") {
        try {
            $docker_version = docker --version 2>&1
            $docker_running = docker info 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Docker: $docker_version (运行中)"
            } else {
                Write-Warning "Docker: 已安装但未运行"
                Write-Host "   请启动 Docker Desktop" -ForegroundColor $Colors.White
                exit 1
            }
        } catch {
            Write-Error "Docker 检查失败"
            exit 1
        }
    } else {
        Write-Error "Docker 未安装，请安装 Docker Desktop"
        Write-Host "   下载地址: https://www.docker.com/products/docker-desktop/" -ForegroundColor $Colors.White
        exit 1
    }
}

# 获取用户配置
Write-Section "配置应用参数"

if (-not $GLM_API_KEY) {
    $GLM_API_KEY = Read-SecureInput "请输入 GLM API Key"
}

if ([string]::IsNullOrEmpty($GLM_API_KEY)) {
    Write-Error "GLM API Key 不能为空"
    exit 1
}

Write-Success "GLM API Key 已配置"

# 生成安全密钥和密码
Write-Step "生成安全配置"

$db_password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$redis_password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$secret_key = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})

Write-Success "安全密钥已生成"

# 创建环境变量文件
Write-Step "创建环境配置文件"

$env_content = @"
# AI Agent Prompt Generator - Windows 部署配置
# 生成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# 环境: $Environment

# =============================================================================
# GLM API 配置
# =============================================================================
GLM_API_KEY=$GLM_API_KEY
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4
GLM_TIMEOUT=60
GLM_MAX_RETRIES=3

# =============================================================================
# 数据库配置
# =============================================================================
DATABASE_URL=postgresql://prompt_gen_user:$db_password@localhost:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=$db_password

# =============================================================================
# Redis 配置
# =============================================================================
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# =============================================================================
# 应用配置
# =============================================================================
SECRET_KEY=$secret_key
DEBUG=$($Environment -eq "development")
ENVIRONMENT=$Environment
DOMAIN=$DOMAIN

# =============================================================================
# CORS 配置
# =============================================================================
CORS_ORIGINS=$(
    if ($Environment -eq "development") {
        '["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]'
    } else {
        "['https://$DOMAIN', 'https://www.$DOMAIN']"
    }
)

# =============================================================================
# 性能配置
# =============================================================================
WORKERS=$(
    if ($Environment -eq "development") { "1" } else { "4" }
)
MAX_CONCURRENT_SESSIONS=$(
    if ($Environment -eq "development") { "10" } else { "100" }
)

# =============================================================================
# 日志配置
# =============================================================================
LOG_LEVEL=$(
    if ($Environment -eq "development") { "DEBUG" } else { "INFO" }
)
LOG_FILE=logs/$Environment.log
LOG_FORMAT=json

# =============================================================================
# WebSocket 配置
# =============================================================================
WS_HEARTBEAT_INTERVAL=30
WS_CONNECTION_TIMEOUT=300
WS_MAX_CONNECTIONS=$(
    if ($Environment -eq "development") { "100" } else { "1000" }
)

# =============================================================================
# 安全配置
# =============================================================================
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# =============================================================================
# 文件配置
# =============================================================================
UPLOAD_PATH=uploads/
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=[".txt", ".pdf", ".doc", ".docx", ".md"]
"@

# 创建 Docker Compose 文件 (如果使用 Docker)
if ($UseDocker) {
    $docker_compose_content = @"
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: prompt_gen_postgres_win
    environment:
      POSTGRES_DB: prompt_gen
      POSTGRES_USER: prompt_gen_user
      POSTGRES_PASSWORD: $db_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - prompt_gen_network
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U prompt_gen_user -d prompt_gen"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: prompt_gen_redis_win
    command: redis-server --appendonly yes --requirepass $redis_password
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - prompt_gen_network
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:

networks:
  prompt_gen_network:
    driver: bridge
"@

    $docker_compose_content | Out-File -FilePath "docker-compose.windows.yml" -Encoding UTF8
    Write-Success "Docker Compose 文件已创建: docker-compose.windows.yml"

    # 更新环境变量文件中的数据库连接信息
    $env_content = $env_content -replace "DATABASE_URL=postgresql://prompt_gen_user:.*@localhost:5432/prompt_gen", "DATABASE_URL=postgresql://prompt_gen_user:$db_password@localhost:5432/prompt_gen"
    $env_content = $env_content -replace "REDIS_URL=redis://localhost:6379/0", "REDIS_URL=redis://:$redis_password@localhost:6379/0"
}

$env_content | Out-File -FilePath ".env" -Encoding UTF8
Write-Success "环境配置文件已创建: .env"

# 设置数据库
if (-not $SkipDatabase) {
    Write-Section "配置数据库服务"

    if ($UseDocker) {
        Write-Step "启动 Docker 数据库服务"

        try {
            docker-compose -f docker-compose.windows.yml down 2>$null
            docker-compose -f docker-compose.windows.yml up -d

            Write-Host "⏳ 等待数据库服务启动..." -ForegroundColor $Colors.Warning
            Start-Sleep -Seconds 15

            # 检查服务状态
            $postgres_status = docker-compose -f docker-compose.windows.yml ps -q postgres | ForEach-Object { docker inspect $_ --format='{{.State.Status}}' }
            $redis_status = docker-compose -f docker-compose.windows.yml ps -q redis | ForEach-Object { docker inspect $_ --format='{{.State.Status}}' }

            if ($postgres_status -eq "running") {
                Write-Success "PostgreSQL 服务已启动"
            } else {
                Write-Error "PostgreSQL 服务启动失败"
                docker-compose -f docker-compose.windows.yml logs postgres
                exit 1
            }

            if ($redis_status -eq "running") {
                Write-Success "Redis 服务已启动"
            } else {
                Write-Error "Redis 服务启动失败"
                docker-compose -f docker-compose.windows.yml logs redis
                exit 1
            }

            Write-Success "Docker 数据库服务启动成功"
        } catch {
            Write-Error "Docker 服务启动失败: $($_.Exception.Message)"
            exit 1
        }
    } else {
        Write-Step "检查本地数据库服务"

        # 检查 PostgreSQL
        try {
            $postgres_services = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
            if ($postgres_services) {
                $postgres_service = $postgres_services | Where-Object { $_.Status -eq "Running" } | Select-Object -First 1
                if ($postgres_service) {
                    Write-Success "PostgreSQL 服务正在运行: $($postgres_service.Name)"
                } else {
                    Write-Warning "PostgreSQL 服务未运行，尝试启动..."
                    try {
                        Start-Service -Name $postgres_services[0].Name -ErrorAction Stop
                        Write-Success "PostgreSQL 服务已启动"
                    } catch {
                        Write-Error "无法启动 PostgreSQL 服务，请手动检查"
                        Write-Host "   可能需要安装 PostgreSQL: choco install postgresql" -ForegroundColor $Colors.White
                    }
                }
            } else {
                Write-Warning "PostgreSQL 服务未找到"
                Write-Host "   安装命令: choco install postgresql" -ForegroundColor $Colors.White
                Write-Host "   或访问: https://www.postgresql.org/download/windows/" -ForegroundColor $Colors.White
            }
        } catch {
            Write-Warning "检查 PostgreSQL 服务时出错"
        }

        # 检查 Redis
        try {
            $redis_service = Get-Service -Name "redis" -ErrorAction SilentlyContinue
            if ($redis_service) {
                if ($redis_service.Status -eq "Running") {
                    Write-Success "Redis 服务正在运行"
                } else {
                    Write-Warning "Redis 服务未运行，尝试启动..."
                    try {
                        Start-Service -Name "redis" -ErrorAction Stop
                        Write-Success "Redis 服务已启动"
                    } catch {
                        Write-Error "无法启动 Redis 服务，请手动检查"
                        Write-Host "   可能需要安装 Redis: choco install redis-64" -ForegroundColor $Colors.White
                    }
                }
            } else {
                Write-Warning "Redis 服务未找到"
                Write-Host "   安装命令: choco install redis-64" -ForegroundColor $Colors.White
            }
        } catch {
            Write-Warning "检查 Redis 服务时出错"
        }
    }
} else {
    Write-Warning "跳过数据库配置"
}

# 部署后端应用
Write-Section "部署后端应用"

Set-Location backend

# 检查后端目录结构
if (-not (Test-Path "requirements.txt")) {
    Write-Error "后端目录缺少 requirements.txt 文件"
    Set-Location ..
    exit 1
}

Write-Step "配置 Python 虚拟环境"

# 创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "📦 创建 Python 虚拟环境..." -ForegroundColor $Colors.Warning
    try {
        python -m venv venv
        Write-Success "虚拟环境创建成功"
    } catch {
        Write-Error "虚拟环境创建失败: $($_.Exception.Message)"
        Set-Location ..
        exit 1
    }
}

# 激活虚拟环境
Write-Step "激活虚拟环境"
try {
    & ".\venv\Scripts\Activate.ps1"
    Write-Success "虚拟环境已激活"
} catch {
    Write-Error "虚拟环境激活失败，请检查 PowerShell 执行策略"
    Write-Host "   运行: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor $Colors.White
    Set-Location ..
    exit 1
}

# 安装依赖
Write-Step "安装 Python 依赖"
try {
    pip install -r requirements.txt --upgrade
    Write-Success "Python 依赖安装完成"
} catch {
    Write-Error "Python 依赖安装失败: $($_.Exception.Message)"
    Set-Location ..
    exit 1
}

# 数据库迁移
if (-not $SkipDatabase -and (Test-Path "alembic.ini")) {
    Write-Step "运行数据库迁移"
    try {
        python -m alembic upgrade head
        Write-Success "数据库迁移完成"
    } catch {
        Write-Warning "数据库迁移失败或不需要迁移: $($_.Exception.Message)"
    }
}

# 启动后端服务
Write-Step "启动后端服务"
try {
    $backend_log = "..\logs\backend.log"
    $logs_dir = "..\logs"
    if (-not (Test-Path $logs_dir)) {
        New-Item -ItemType Directory -Path $logs_dir -Force | Out-Null
    }

    # 启动后端服务 (后台)
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "powershell.exe"
    $startInfo.Arguments = "-Command cd '$PWD'; .\venv\Scripts\Activate.ps1; python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload *>&1 | Tee-Object -FilePath '$backend_log'"
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true

    $process = [System.Diagnostics.Process]::Start($startInfo)

    Write-Host "⏳ 等待后端服务启动..." -ForegroundColor $Colors.Warning
    Start-Sleep -Seconds 5

    # 检查服务是否启动成功
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Success "后端服务启动成功 (PID: $($process.Id))"
        } else {
            Write-Warning "后端服务可能启动失败，请检查日志"
        }
    } catch {
        Write-Warning "后端服务健康检查失败，请手动检查: $backend_log"
    }
} catch {
    Write-Error "后端服务启动失败: $($_.Exception.Message)"
}

Set-Location ..

# 部署前端应用
Write-Section "部署前端应用"

Set-Location frontend

# 检查前端目录结构
if (-not (Test-Path "package.json")) {
    Write-Error "前端目录缺少 package.json 文件"
    Set-Location ..
    exit 1
}

Write-Step "安装 Node.js 依赖"
try {
    npm install
    Write-Success "Node.js 依赖安装完成"
} catch {
    Write-Error "Node.js 依赖安装失败: $($_.Exception.Message)"
    Set-Location ..
    exit 1
}

# 构建前端 (生产环境)
if ($Environment -eq "production") {
    Write-Step "构建生产版本"
    try {
        npm run build
        Write-Success "生产版本构建完成"
    } catch {
        Write-Error "前端构建失败: $($_.Exception.Message)"
        Set-Location ..
        exit 1
    }
}

# 启动前端服务 (开发环境)
if ($Environment -eq "development") {
    Write-Step "启动前端开发服务器"
    try {
        $frontend_log = "..\logs\frontend.log"

        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = "powershell.exe"
        $startInfo.Arguments = "-Command cd '$PWD'; npm start *>&1 | Tee-Object -FilePath '$frontend_log'"
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true

        $process = [System.Diagnostics.Process]::Start($startInfo)

        Write-Host "⏳ 等待前端服务启动..." -ForegroundColor $Colors.Warning
        Start-Sleep -Seconds 10

        Write-Success "前端开发服务器已启动 (PID: $($process.Id))"
    } catch {
        Write-Warning "前端服务启动可能失败，请手动检查"
    }
}

Set-Location ..

# 部署完成
Write-Section "部署完成"

Write-Success "🎉 部署完成!"
Write-Host ""

Write-Host "📱 访问地址:" -ForegroundColor $Colors.Info
Write-Host "   前端: http://localhost:3000" -ForegroundColor $Colors.White
if ($Environment -eq "production") {
    Write-Host "   生产构建: ./frontend/build/ 目录" -ForegroundColor $Colors.White
}
Write-Host "   后端 API: http://localhost:8000" -ForegroundColor $Colors.White
Write-Host "   API 文档: http://localhost:8000/docs" -ForegroundColor $Colors.White
Write-Host "   健康检查: http://localhost:8000/health" -ForegroundColor $Colors.White
Write-Host ""

Write-Host "📋 管理命令:" -ForegroundColor $Colors.Info
Write-Host "   查看进程: Get-Process python, node" -ForegroundColor $Colors.White
Write-Host "   终止进程: Stop-Process -Name python, node" -ForegroundColor $Colors.White
Write-Host "   查看端口: netstat -ano | findstr :8000" -ForegroundColor $Colors.White
if ($UseDocker) {
    Write-Host "   Docker 状态: docker-compose -f docker-compose.windows.yml ps" -ForegroundColor $Colors.White
    Write-Host "   Docker 日志: docker-compose -f docker-compose.windows.yml logs" -ForegroundColor $Colors.White
    Write-Host "   停止 Docker: docker-compose -f docker-compose.windows.yml down" -ForegroundColor $Colors.White
}
Write-Host ""

Write-Host "📝 日志文件:" -ForegroundColor $Colors.Info
Write-Host "   后端日志: ./logs/backend.log" -ForegroundColor $Colors.White
Write-Host "   前端日志: ./logs/frontend.log" -ForegroundColor $Colors.White
Write-Host "   应用日志: ./logs/$Environment.log" -ForegroundColor $Colors.White
Write-Host ""

Write-Host "🔧 环境配置:" -ForegroundColor $Colors.Info
Write-Host "   配置文件: ./.env" -ForegroundColor $Colors.White
if ($UseDocker) {
    Write-Host "   Docker 配置: ./docker-compose.windows.yml" -ForegroundColor $Colors.White
}
Write-Host ""

Write-Host "⚠️  注意事项:" -ForegroundColor $Colors.Warning
Write-Host "   1. 请确保防火墙允许端口 3000, 8000 的访问" -ForegroundColor $Colors.White
Write-Host "   2. 生产环境请配置真实的域名和 SSL 证书" -ForegroundColor $Colors.White
Write-Host "   3. 定期备份 .env 文件和数据库" -ForegroundColor $Colors.White
Write-Host "   4. 监控日志文件以了解应用状态" -ForegroundColor $Colors.White

Write-Host ""
Write-ColorText "感谢使用 AI Agent Prompt Generator! 🚀" "Success"