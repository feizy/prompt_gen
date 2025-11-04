# Windows AI Agent Prompt Generator Deployment Script
# Author: Claude Code
# Version: 1.0.0

param(
    [string]$Environment = "development",
    [string]$GLM_API_KEY = "e212879c3a3043929c18892ebc5a9346.PEZl1iVbvHL3mVmS",
    [string]$DOMAIN = "localhost",
    [switch]$UseDocker = $false,
    [switch]$SkipDatabase = $false,
    [switch]$Help = $false
)

# Display help information
if ($Help) {
    Write-Host "🪟 Windows AI Agent Prompt Generator Deployment Script" -ForegroundColor Green
    Write-Host "=================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor White
    Write-Host "  .\windows_deploy.ps1 [parameters]" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor White
    Write-Host "  -Environment <string>    Deployment environment (development|production) [default: development]" -ForegroundColor Gray
    Write-Host "  -GLM_API_KEY <string>    GLM API Key" -ForegroundColor Gray
    Write-Host "  -DOMAIN <string>         Domain [default: localhost]" -ForegroundColor Gray
    Write-Host "  -UseDocker              Use Docker to deploy database" -ForegroundColor Gray
    Write-Host "  -SkipDatabase           Skip database deployment" -ForegroundColor Gray
    Write-Host "  -Help                   Show this help information" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor White
    Write-Host "  .\windows_deploy.ps1 -Environment development -UseDocker" -ForegroundColor Gray
    Write-Host "  .\windows_deploy.ps1 -Environment production -GLM_API_KEY 'your_key' -DOMAIN 'example.com'" -ForegroundColor Gray
    Write-Host "  .\windows_deploy.ps1 -SkipDatabase -Environment development" -ForegroundColor Gray
    exit 0
}

# Color theme configuration
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Blue"
    Title = "Cyan"
    White = "White"
}

# Helper functions
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

# Main program starts
Write-ColorText "🪟 Windows AI Agent Prompt Generator Deployment Script" "Success"
Write-ColorText "=================================================" "Success"
Write-Host ""

# Display configuration
Write-Host "📋 Deployment Configuration:" -ForegroundColor $Colors.Info
Write-Host "   Environment: $Environment" -ForegroundColor $Colors.White
Write-Host "   Domain: $DOMAIN" -ForegroundColor $Colors.White
Write-Host "   Use Docker: $UseDocker" -ForegroundColor $Colors.White
Write-Host "   Skip Database: $SkipDatabase" -ForegroundColor $Colors.White
Write-Host ""

# Check administrator permissions
Write-Section "Checking Permissions and Dependencies"

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Please run this script as Administrator for best experience"
    $choice = Read-Host "Continue? (y/n)"
    if ($choice -ne 'y') {
        Write-Error "Deployment cancelled"
        exit 1
    }
} else {
    Write-Success "Administrator permission check passed"
}

# Check system dependencies
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
                Write-Warning "$($dep.Name): Version does not meet requirements ($version)"
                $missingDeps += $dep.Name
            }
        } catch {
            Write-Error "$($dep.Name): Check failed"
            $missingDeps += $dep.Name
        }
    } else {
        Write-Error "$($dep.Name): Not installed"
        $missingDeps += $dep.Name
    }
}

if ($missingDeps.Count -gt 0) {
    Write-Host "`n❌ Missing dependencies:" -ForegroundColor $Colors.Error
    $missingDeps | ForEach-Object { Write-Host "   - $_" -ForegroundColor $Colors.White }
    Write-Host "`nPlease install missing dependencies:" -ForegroundColor $Colors.Warning
    Write-Host "   Python: https://www.python.org/downloads/" -ForegroundColor $Colors.White
    Write-Host "   Git: https://git-scm.com/download/win" -ForegroundColor $Colors.White
    Write-Host "   Node.js: https://nodejs.org/" -ForegroundColor $Colors.White
    Write-Host "   PowerShell: https://github.com/PowerShell/PowerShell" -ForegroundColor $Colors.White
    exit 1
}

# Check Docker (if needed)
if ($UseDocker) {
    if (Test-Command "docker") {
        try {
            $docker_version = docker --version 2>&1
            $docker_running = docker info 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Docker: $docker_version (running)"
            } else {
                Write-Warning "Docker: Installed but not running"
                Write-Host "   Please start Docker Desktop" -ForegroundColor $Colors.White
                exit 1
            }
        } catch {
            Write-Error "Docker check failed"
            exit 1
        }
    } else {
        Write-Error "Docker not installed, please install Docker Desktop"
        Write-Host "   Download: https://www.docker.com/products/docker-desktop/" -ForegroundColor $Colors.White
        exit 1
    }
}

# Get user configuration
Write-Section "Configure Application Parameters"

if (-not $GLM_API_KEY) {
    $GLM_API_KEY = Read-Host "Please enter GLM API Key"
}

if ([string]::IsNullOrEmpty($GLM_API_KEY)) {
    Write-Error "GLM API Key cannot be empty"
    exit 1
}

Write-Success "GLM API Key configured"

# Generate security keys and passwords
Write-Step "Generate Security Configuration"

$db_password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$redis_password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$secret_key = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})

Write-Success "Security keys generated"

# Create environment variable file
Write-Step "Create Environment Configuration File"

$env_content = @"
# AI Agent Prompt Generator - Windows Deployment Configuration
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# Environment: $Environment

# =============================================================================
# GLM API Configuration
# =============================================================================
GLM_API_KEY=$GLM_API_KEY
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4
GLM_TIMEOUT=60
GLM_MAX_RETRIES=3

# =============================================================================
# Database Configuration
# =============================================================================
DATABASE_URL=postgresql://prompt_gen_user:$db_password@localhost:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=$db_password

# =============================================================================
# Redis Configuration
# =============================================================================
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# =============================================================================
# Application Configuration
# =============================================================================
SECRET_KEY=$secret_key
DEBUG=$($Environment -eq "development")
ENVIRONMENT=$Environment
DOMAIN=$DOMAIN

# =============================================================================
# CORS Configuration
# =============================================================================
CORS_ORIGINS=$(
    if ($Environment -eq "development") {
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001"
    } else {
        "https://$DOMAIN,https://www.$DOMAIN"
    }
)

# =============================================================================
# Performance Configuration
# =============================================================================
WORKERS=$(
    if ($Environment -eq "development") { "1" } else { "4" }
)
MAX_CONCURRENT_SESSIONS=$(
    if ($Environment -eq "development") { "10" } else { "100" }
)

# =============================================================================
# Logging Configuration
# =============================================================================
LOG_LEVEL=$(
    if ($Environment -eq "development") { "DEBUG" } else { "INFO" }
)
LOG_FILE=logs/$Environment.log
LOG_FORMAT=json

# =============================================================================
# WebSocket Configuration
# =============================================================================
WS_HEARTBEAT_INTERVAL=30
WS_CONNECTION_TIMEOUT=300
WS_MAX_CONNECTIONS=$(
    if ($Environment -eq "development") { "100" } else { "1000" }
)

# =============================================================================
# Security Configuration
# =============================================================================
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# =============================================================================
# File Configuration
# =============================================================================
UPLOAD_PATH=uploads/
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS='.txt|.pdf|.doc|.docx|.md'
"@

# Create Docker Compose file (if using Docker)
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
      test: CMD-SHELL "pg_isready -U prompt_gen_user -d prompt_gen"
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
      test: CMD redis-cli ping
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
    Write-Success "Docker Compose file created: docker-compose.windows.yml"

    # Update database connection info in env file
    $env_content = $env_content -replace "DATABASE_URL=postgresql://prompt_gen_user:.*@localhost:5432/prompt_gen", "DATABASE_URL=postgresql://prompt_gen_user:$db_password@localhost:5432/prompt_gen"
    $env_content = $env_content -replace "REDIS_URL=redis://localhost:6379/0", "REDIS_URL=redis://:$redis_password@localhost:6379/0"
}

$env_content | Out-File -FilePath ".env" -Encoding UTF8
Write-Success "Environment configuration file created: .env"

# Setup database
if (-not $SkipDatabase) {
    Write-Section "Configure Database Services"

    if ($UseDocker) {
        Write-Step "Starting Docker Database Services"

        try {
            docker-compose -f docker-compose.windows.yml down 2>$null
            docker-compose -f docker-compose.windows.yml up -d

            Write-Host "⏳ Waiting for database services to start..." -ForegroundColor $Colors.Warning
            Start-Sleep -Seconds 15

            # Check service status
            $postgres_status = docker-compose -f docker-compose.windows.yml ps -q postgres | ForEach-Object { docker inspect $_ --format='{{.State.Status}}' }
            $redis_status = docker-compose -f docker-compose.windows.yml ps -q redis | ForEach-Object { docker inspect $_ --format='{{.State.Status}}' }

            if ($postgres_status -eq "running") {
                Write-Success "PostgreSQL service started"
            } else {
                Write-Error "PostgreSQL service failed to start"
                docker-compose -f docker-compose.windows.yml logs postgres
                exit 1
            }

            if ($redis_status -eq "running") {
                Write-Success "Redis service started"
            } else {
                Write-Error "Redis service failed to start"
                docker-compose -f docker-compose.windows.yml logs redis
                exit 1
            }

            Write-Success "Docker database services started successfully"
        } catch {
            Write-Error "Docker service startup failed: $($_.Exception.Message)"
            exit 1
        }
    } else {
        Write-Step "Checking Local Database Services"

        # Check PostgreSQL
        try {
            $postgres_services = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
            if ($postgres_services) {
                $postgres_service = $postgres_services | Where-Object { $_.Status -eq "Running" } | Select-Object -First 1
                if ($postgres_service) {
                    Write-Success "PostgreSQL service running: $($postgres_service.Name)"
                } else {
                    Write-Warning "PostgreSQL service not running, attempting to start..."
                    try {
                        Start-Service -Name $postgres_services[0].Name -ErrorAction Stop
                        Write-Success "PostgreSQL service started"
                    } catch {
                        Write-Error "Cannot start PostgreSQL service, please check manually"
                        Write-Host "   May need to install PostgreSQL: choco install postgresql" -ForegroundColor $Colors.White
                    }
                }
            } else {
                Write-Warning "PostgreSQL service not found"
                Write-Host "   Install command: choco install postgresql" -ForegroundColor $Colors.White
                Write-Host "   Or visit: https://www.postgresql.org/download/windows/" -ForegroundColor $Colors.White
            }
        } catch {
            Write-Warning "Error checking PostgreSQL service"
        }

        # Check Redis
        try {
            $redis_service = Get-Service -Name "redis" -ErrorAction SilentlyContinue
            if ($redis_service) {
                if ($redis_service.Status -eq "Running") {
                    Write-Success "Redis service is running"
                } else {
                    Write-Warning "Redis service not running, attempting to start..."
                    try {
                        Start-Service -Name "redis" -ErrorAction Stop
                        Write-Success "Redis service started"
                    } catch {
                        Write-Error "Cannot start Redis service, please check manually"
                        Write-Host "   May need to install Redis: choco install redis-64" -ForegroundColor $Colors.White
                    }
                }
            } else {
                Write-Warning "Redis service not found"
                Write-Host "   Install command: choco install redis-64" -ForegroundColor $Colors.White
            }
        } catch {
            Write-Warning "Error checking Redis service"
        }
    }
} else {
    Write-Warning "Skipping database configuration"
}

# Deploy backend application
Write-Section "Deploy Backend Application"

Set-Location backend

# Check backend directory structure
if (-not (Test-Path "requirements.txt")) {
    Write-Error "Backend directory missing requirements.txt file"
    Set-Location ..
    exit 1
}

Write-Step "Configure Python Virtual Environment"

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating Python virtual environment..." -ForegroundColor $Colors.Warning
    try {
        python -m venv venv
        Write-Success "Virtual environment created successfully"
    } catch {
        Write-Error "Virtual environment creation failed: $($_.Exception.Message)"
        Set-Location ..
        exit 1
    }
}

# Activate virtual environment
Write-Step "Activate Virtual Environment"
try {
    & ".\venv\Scripts\Activate.ps1"
    Write-Success "Virtual environment activated"
} catch {
    Write-Error "Virtual environment activation failed, please check PowerShell execution policy"
    Write-Host "   Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor $Colors.White
    Set-Location ..
    exit 1
}

# Install dependencies
Write-Step "Install Python Dependencies"
try {
    pip install -r requirements.txt --upgrade
    Write-Success "Python dependencies installed"
} catch {
    Write-Error "Python dependencies installation failed: $($_.Exception.Message)"
    Set-Location ..
    exit 1
}

# Database migration
if (-not $SkipDatabase -and (Test-Path "alembic.ini")) {
    Write-Step "Run Database Migration"
    try {
        python -m alembic upgrade head
        Write-Success "Database migration completed"
    } catch {
        Write-Warning "Database migration failed or not needed: $($_.Exception.Message)"
    }
}

# Start backend service
Write-Step "Start Backend Service"
try {
    $backend_log = "..\logs\backend.log"
    $logs_dir = "..\logs"
    if (-not (Test-Path $logs_dir)) {
        New-Item -ItemType Directory -Path $logs_dir -Force | Out-Null
    }

    # Start backend service (background)
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "powershell.exe"
    $startInfo.Arguments = "-Command cd '$PWD'; .\venv\Scripts\Activate.ps1; python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload *>&1 | Tee-Object -FilePath '$backend_log'"
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true

    $process = [System.Diagnostics.Process]::Start($startInfo)

    Write-Host "⏳ Waiting for backend service to start..." -ForegroundColor $Colors.Warning
    Start-Sleep -Seconds 5

    # Check if service started successfully
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Success "Backend service started successfully (PID: $($process.Id))"
        } else {
            Write-Warning "Backend service may have failed to start, please check logs"
        }
    } catch {
        Write-Warning "Backend service health check failed, please check manually: $backend_log"
    }
} catch {
    Write-Error "Backend service startup failed: $($_.Exception.Message)"
}

Set-Location ..

# Deploy frontend application
Write-Section "Deploy Frontend Application"

Set-Location frontend

# Check frontend directory structure
if (-not (Test-Path "package.json")) {
    Write-Error "Frontend directory missing package.json file"
    Set-Location ..
    exit 1
}

Write-Step "Install Node.js Dependencies"
try {
    npm install
    Write-Success "Node.js dependencies installed"
} catch {
    Write-Error "Node.js dependencies installation failed: $($_.Exception.Message)"
    Set-Location ..
    exit 1
}

# Build frontend (production environment)
if ($Environment -eq "production") {
    Write-Step "Build Production Version"
    try {
        npm run build
        Write-Success "Production version built successfully"
    } catch {
        Write-Error "Frontend build failed: $($_.Exception.Message)"
        Set-Location ..
        exit 1
    }
}

# Start frontend service (development environment)
if ($Environment -eq "development") {
    Write-Step "Start Frontend Development Server"
    try {
        $frontend_log = "..\logs\frontend.log"

        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = "powershell.exe"
        $startInfo.Arguments = "-Command cd '$PWD'; npm start *>&1 | Tee-Object -FilePath '$frontend_log'"
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true

        $process = [System.Diagnostics.Process]::Start($startInfo)

        Write-Host "⏳ Waiting for frontend service to start..." -ForegroundColor $Colors.Warning
        Start-Sleep -Seconds 10

        Write-Success "Frontend development server started (PID: $($process.Id))"
    } catch {
        Write-Warning "Frontend service startup may have failed, please check manually"
    }
}

Set-Location ..

# Deployment complete
Write-Section "Deployment Complete"

Write-Success "🎉 Deployment Complete!"
Write-Host ""

Write-Host "📱 Access URLs:" -ForegroundColor $Colors.Info
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor $Colors.White
if ($Environment -eq "production") {
    Write-Host "   Production Build: ./frontend/build/ directory" -ForegroundColor $Colors.White
}
Write-Host "   Backend API: http://localhost:8000" -ForegroundColor $Colors.White
Write-Host "   API Documentation: http://localhost:8000/docs" -ForegroundColor $Colors.White
Write-Host "   Health Check: http://localhost:8000/health" -ForegroundColor $Colors.White
Write-Host ""

Write-Host "📋 Management Commands:" -ForegroundColor $Colors.Info
Write-Host "   View processes: Get-Process python, node" -ForegroundColor $Colors.White
Write-Host "   Stop processes: Stop-Process -Name python, node" -ForegroundColor $Colors.White
Write-Host "   View ports: netstat -ano | findstr :8000" -ForegroundColor $Colors.White
if ($UseDocker) {
    Write-Host "   Docker status: docker-compose -f docker-compose.windows.yml ps" -ForegroundColor $Colors.White
    Write-Host "   Docker logs: docker-compose -f docker-compose.windows.yml logs" -ForegroundColor $Colors.White
    Write-Host "   Stop Docker: docker-compose -f docker-compose.windows.yml down" -ForegroundColor $Colors.White
}
Write-Host ""

Write-Host "📝 Log Files:" -ForegroundColor $Colors.Info
Write-Host "   Backend log: ./logs/backend.log" -ForegroundColor $Colors.White
Write-Host "   Frontend log: ./logs/frontend.log" -ForegroundColor $Colors.White
Write-Host "   Application log: ./logs/$Environment.log" -ForegroundColor $Colors.White
Write-Host ""

Write-Host "🔧 Environment Configuration:" -ForegroundColor $Colors.Info
Write-Host "   Configuration file: ./.env" -ForegroundColor $Colors.White
if ($UseDocker) {
    Write-Host "   Docker configuration: ./docker-compose.windows.yml" -ForegroundColor $Colors.White
}
Write-Host ""

Write-Host "⚠️  Important Notes:" -ForegroundColor $Colors.Warning
Write-Host "   1. Please ensure firewall allows ports 3000, 8000 access" -ForegroundColor $Colors.White
Write-Host "   2. Production environment please configure real domain and SSL certificates" -ForegroundColor $Colors.White
Write-Host "   3. Regular backup of .env file and database" -ForegroundColor $Colors.White
Write-Host "   4. Monitor log files to understand application status" -ForegroundColor $Colors.White

Write-Host ""
Write-ColorText "Thank you for using AI Agent Prompt Generator! 🚀" "Success"