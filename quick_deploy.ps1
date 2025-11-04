# AI Agent Prompt Generator - PowerShell快速部署脚本
# Quick Deployment Script for AI Agent Prompt Generator (PowerShell)

param(
    [string]$Mode = "",
    [switch]$Quick = $false,
    [switch]$CheckOnly = $false,
    [switch]$HealthOnly = $false,
    [switch]$Help = $false
)

# 颜色输出函数
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Info($message) {
    Write-ColorOutput Green "[INFO] $message"
}

function Write-Warning($message) {
    Write-ColorOutput Yellow "[WARNING] $message"
}

function Write-Error($message) {
    Write-ColorOutput Red "[ERROR] $message"
}

function Write-Header($message) {
    Write-ColorOutput Cyan $message
}

# 检查系统要求
function Test-Requirements {
    Write-Header "🔍 检查系统要求..."

    # 检查Docker
    try {
        $dockerVersion = docker --version
        Write-Info "✓ Docker已安装: $dockerVersion"
    }
    catch {
        Write-Error "Docker未安装。请先安装Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    }

    # 检查Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-Info "✓ Docker Compose已安装: $composeVersion"
    }
    catch {
        Write-Error "Docker Compose未安装。请先安装Docker Compose"
        exit 1
    }

    # 检查Git
    try {
        $gitVersion = git --version
        Write-Info "✓ Git已安装: $gitVersion"
    }
    catch {
        Write-Error "Git未安装。请先安装Git: https://git-scm.com/download/win"
        exit 1
    }

    # 检查端口占用
    $port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($port8000) {
        Write-Warning "端口8000已被占用，请确保端口可用"
    }

    $port3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
    if ($port3000) {
        Write-Warning "端口3000已被占用，请确保端口可用"
    }

    Write-Info "✓ 系统要求检查完成"
}

# 创建环境配置
function Initialize-Environment {
    Write-Header "⚙️ 配置环境变量..."

    # 检查.env文件是否存在
    if (-not (Test-Path ".env")) {
        Write-Info "创建.env文件..."

        # 生成随机密钥
        $secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
        $dbPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})

        # 创建.env文件
        @"
# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:$dbPassword@postgres:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=$dbPassword

# GLM API配置 (请替换为您的实际API密钥)
GLM_API_KEY=your_glm_api_key_here
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 应用配置
SECRET_KEY=$secretKey
DEBUG=True
CORS_ORIGINS=["http://localhost:3000"]

# Redis配置
REDIS_URL=redis://redis:6379/0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
"@ | Out-File -FilePath ".env" -Encoding UTF8

        Write-Warning "⚠️  请编辑.env文件，设置您的GLM_API_KEY"
        Write-Info "✓ .env文件已创建"
    }
    else {
        Write-Info "✓ .env文件已存在"
    }
}

# 选择部署模式
function Select-DeploymentMode {
    if ([string]::IsNullOrEmpty($Mode)) {
        Write-Header "🚀 选择部署模式..."

        Write-Host "请选择部署模式:"
        Write-Host "1) 开发环境 (Development)"
        Write-Host "2) 生产环境 (Production)"
        Write-Host "3) 仅后端 (Backend Only)"
        Write-Host "4) 仅前端 (Frontend Only)"

        $choice = Read-Host "请输入选择 (1-4)"

        switch ($choice) {
            "1" { $script:Mode = "development" }
            "2" { $script:Mode = "production" }
            "3" { $script:Mode = "backend-only" }
            "4" { $script:Mode = "frontend-only" }
            default {
                Write-Error "无效选择，使用默认开发环境"
                $script:Mode = "development"
            }
        }
    }

    Write-Info "选择: $Mode"
}

# 开发环境部署
function Deploy-Development {
    Write-Header "🛠️ 部署开发环境..."

    # 检查Python环境
    try {
        $pythonVersion = python --version
        Write-Info "✓ Python已安装: $pythonVersion"
    }
    catch {
        Write-Error "Python未安装。请先安装Python 3.11+: https://www.python.org/downloads/"
        exit 1
    }

    # 检查Node.js环境
    try {
        $nodeVersion = node --version
        Write-Info "✓ Node.js已安装: $nodeVersion"
    }
    catch {
        Write-Error "Node.js未安装。请先安装Node.js: https://nodejs.org/"
        exit 1
    }

    # 后端设置
    Write-Info "设置后端..."
    Set-Location backend

    if (-not (Test-Path "venv")) {
        python -m venv venv
        Write-Info "✓ Python虚拟环境已创建"
    }

    # 激活虚拟环境并安装依赖
    & venv\Scripts\Activate.ps1
    pip install -r requirements.txt

    # 前端设置
    Write-Info "设置前端..."
    Set-Location ..\frontend
    npm install

    # 返回根目录
    Set-Location ..

    Write-Header "🎉 开发环境部署完成!"
    Write-Host ""
    Write-Host "启动服务:"
    Write-Host "终端1 - 启动后端:"
    Write-Host "  cd backend"
    Write-Host "  venv\Scripts\Activate.ps1"
    Write-Host "  uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000"
    Write-Host ""
    Write-Host "终端2 - 启动前端:"
    Write-Host "  cd frontend"
    Write-Host "  npm start"
    Write-Host ""
    Write-Host "访问地址:"
    Write-Host "  前端: http://localhost:3000"
    Write-Host "  后端API: http://localhost:8000"
    Write-Host "  API文档: http://localhost:8000/docs"
}

# Docker部署
function Deploy-Docker {
    Write-Header "🐳 部署Docker环境..."

    # 选择Compose文件
    if ($Mode -eq "production") {
        $composeFile = "docker-compose.prod.yml"
        Write-Info "使用生产环境配置"
    }
    else {
        $composeFile = "docker-compose.yml"
        Write-Info "使用开发环境配置"
    }

    # 检查compose文件是否存在
    if (-not (Test-Path $composeFile)) {
        Write-Error "$composeFile 文件不存在"
        exit 1
    }

    # 停止现有服务
    Write-Info "停止现有服务..."
    docker-compose -f $composeFile down

    # 构建并启动服务
    Write-Info "构建并启动服务..."
    docker-compose -f $composeFile up --build -d

    # 等待服务启动
    Write-Info "等待服务启动..."
    Start-Sleep -Seconds 10

    # 运行数据库迁移
    if ($Mode -ne "frontend-only") {
        Write-Info "运行数据库迁移..."
        try {
            docker-compose -f $composeFile exec -T backend python -m alembic upgrade head
            Write-Info "✓ 数据库迁移完成"
        }
        catch {
            Write-Warning "数据库迁移失败，请手动检查"
        }
    }

    # 检查服务状态
    Write-Info "检查服务状态..."
    docker-compose -f $composeFile ps

    Write-Header "🎉 Docker部署完成!"
    Write-Host ""
    Write-Host "服务访问地址:"

    if ($Mode -ne "backend-only") {
        Write-Host "  前端: http://localhost:3000"
    }

    if ($Mode -ne "frontend-only") {
        Write-Host "  后端API: http://localhost:8000"
        Write-Host "  API文档: http://localhost:8000/docs"
    }

    Write-Host ""
    Write-Host "查看日志: docker-compose -f $composeFile logs -f"
    Write-Host "停止服务: docker-compose -f $composeFile down"
}

# 仅后端部署
function Deploy-BackendOnly {
    Write-Header "🔧 仅部署后端..."

    Set-Location backend

    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        Write-Info "使用Docker部署后端..."
        docker-compose up --build -d postgres redis backend

        # 等待服务启动
        Start-Sleep -Seconds 5

        # 运行数据库迁移
        try {
            docker-compose exec backend python -m alembic upgrade head
            Write-Info "✓ 数据库迁移完成"
        }
        catch {
            Write-Warning "数据库迁移失败"
        }

        Write-Header "🎉 后端部署完成!"
        Write-Host "后端API: http://localhost:8000"
        Write-Host "API文档: http://localhost:8000/docs"
        Write-Host "查看日志: docker-compose logs -f backend"
    }
    else {
        Write-Error "需要Docker Compose来部署后端服务"
        exit 1
    }
}

# 仅前端部署
function Deploy-FrontendOnly {
    Write-Header "🎨 仅部署前端..."

    Set-Location frontend

    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        Write-Info "使用Docker部署前端..."
        docker-compose up --build -d frontend

        Write-Header "🎉 前端部署完成!"
        Write-Host "前端: http://localhost:3000"
        Write-Host "查看日志: docker-compose logs -f frontend"
    }
    else {
        Write-Info "使用本地环境部署前端..."
        npm install
        npm run build

        Write-Header "🎉 前端构建完成!"
        Write-Host "构建文件位于: build\"
        Write-Host "您可以使用任何Web服务器托管这些文件"
    }
}

# 健康检查
function Test-Health {
    Write-Header "🏥 执行健康检查..."

    # 等待服务完全启动
    Start-Sleep -Seconds 5

    # 检查后端健康
    if ($Mode -ne "frontend-only") {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
            Write-Info "✓ 后端服务健康"
        }
        catch {
            Write-Warning "⚠️ 后端服务可能未正常启动"
        }
    }

    # 检查前端
    if ($Mode -ne "backend-only") {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 10
            Write-Info "✓ 前端服务健康"
        }
        catch {
            Write-Warning "⚠️ 前端服务可能未正常启动"
        }
    }

    # 运行系统验证
    if (Get-Command python -ErrorAction SilentlyContinue -and (Test-Path "system_validation.py")) {
        Write-Info "运行系统验证..."
        try {
            python system_validation.py --base-url http://localhost:8000
            Write-Info "✓ 系统验证通过"
        }
        catch {
            Write-Warning "系统验证发现问题，请检查日志"
        }
    }
}

# 显示帮助信息
function Show-Help {
    Write-Host "AI Agent Prompt Generator - PowerShell快速部署脚本"
    Write-Host ""
    Write-Host "用法: .\quick_deploy.ps1 [参数]"
    Write-Host ""
    Write-Host "参数:"
    Write-Host "  -Mode <String>          部署模式 (development|production|backend-only|frontend-only)"
    Write-Host "  -Quick                  快速部署 (跳过部分检查)"
    Write-Host "  -CheckOnly              仅执行环境检查"
    Write-Host "  -HealthOnly             仅执行健康检查"
    Write-Host "  -Help                   显示此帮助信息"
    Write-Host ""
    Write-Host "示例:"
    Write-Host "  .\quick_deploy.ps1                    # 交互式部署"
    Write-Host "  .\quick_deploy.ps1 -Mode development  # 开发环境部署"
    Write-Host "  .\quick_deploy.ps1 -Mode production   # 生产环境部署"
    Write-Host "  .\quick_deploy.ps1 -CheckOnly         # 仅检查环境"
    Write-Host ""
}

# 主函数
function Main {
    Write-Header "🚀 AI Agent Prompt Generator - PowerShell快速部署脚本"
    Write-Host ""

    # 显示帮助
    if ($Help) {
        Show-Help
        return
    }

    # 仅执行健康检查
    if ($HealthOnly) {
        Test-Health
        return
    }

    # 仅执行环境检查
    if ($CheckOnly) {
        Test-Requirements
        Write-Header "✅ 环境检查完成"
        return
    }

    # 检查要求
    if (-not $Quick) {
        Test-Requirements
    }

    # 设置环境
    Initialize-Environment

    # 选择部署模式
    if ([string]::IsNullOrEmpty($Mode)) {
        Select-DeploymentMode
    }

    # 根据模式执行部署
    switch ($Mode) {
        "development" {
            Deploy-Development
        }
        "production" {
            Deploy-Docker
        }
        "backend-only" {
            Deploy-BackendOnly
        }
        "frontend-only" {
            Deploy-FrontendOnly
        }
        default {
            Write-Error "无效的部署模式: $Mode"
            exit 1
        }
    }

    # 健康检查
    if (-not $Quick) {
        Test-Health
    }

    Write-Header "🎉 部署完成!"
    Write-Host ""
    Write-Host "📚 更多信息:"
    Write-Host "  - 部署文档: DEPLOYMENT.md"
    Write-Host "  - 测试文档: TESTING.md"
    Write-Host "  - 系统验证: python system_validation.py"
    Write-Host ""
    Write-Host "🐛 如遇问题，请查看:"
    Write-Host "  - 日志文件: docker-compose logs -f"
    Write-Host "  - 故障排除: DEPLOYMENT.md#故障排除"
    Write-Host ""
}

# 执行主函数
Main