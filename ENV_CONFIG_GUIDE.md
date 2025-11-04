# 环境变量配置指南

## 📋 问题说明

目前项目中有两个环境变量模板文件：
- 根目录：`.env.template` (完整版)
- backend目录：`.env.example` (简化版)

这会导致配置混乱。以下是统一的配置方案。

## 🎯 推荐方案

### 方案1：使用根目录的完整模板（推荐）

```bash
# 使用根目录的完整模板
cp .env.template .env
```

### 方案2：为不同环境创建专门配置

```bash
# 开发环境
cp .env.template .env.development

# 生产环境
cp .env.template .env.production

# 测试环境
cp .env.template .env.test
```

## ⚙️ 必须配置项（快速开始）

以下是必须修改的关键配置项：

### 1. 数据库配置
```env
# 选择其中一种方式

# 方式A：完整数据库URL（推荐）
DATABASE_URL=postgresql://prompt_gen_user:your_password@localhost:5432/prompt_gen

# 方式B：分别配置（如果不使用DATABASE_URL）
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=your_password
```

### 2. GLM API配置
```env
GLM_API_KEY=your_actual_glm_api_key_here
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4
```

### 3. 应用安全配置
```env
SECRET_KEY=your_very_secure_secret_key_here
DEBUG=False  # 生产环境必须设为False
```

### 4. 域名配置（生产环境）
```env
DOMAIN=your-domain.com
ALLOWED_HOSTS=["your-domain.com", "www.your-domain.com"]
CORS_ORIGINS=["https://your-domain.com", "https://www.your-domain.com"]
```

## 🛠️ 不同环境的配置示例

### 开发环境 (.env.development)
```env
# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:dev_password@localhost:5432/prompt_gen_dev
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen_dev
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=dev_password

# GLM API配置
GLM_API_KEY=your_glm_api_key
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 应用配置
SECRET_KEY=dev_secret_key_for_development_only
DEBUG=True
ENVIRONMENT=development

# CORS配置（开发环境允许本地访问）
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]

# 日志配置
LOG_LEVEL=DEBUG
LOG_FILE=logs/dev.log

# Redis配置（可选）
REDIS_URL=redis://localhost:6379/0

# WebSocket配置
WS_HEARTBEAT_INTERVAL=30
WS_CONNECTION_TIMEOUT=300
WS_MAX_CONNECTIONS=100

# 性能配置
WORKERS=1
MAX_CONCURRENT_SESSIONS=10
```

### 生产环境 (.env.production)
```env
# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:VERY_SECURE_PASSWORD@postgres:5432/prompt_gen
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=VERY_SECURE_PASSWORD

# GLM API配置
GLM_API_KEY=your_production_glm_api_key
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 应用配置
SECRET_KEY=$(openssl rand -hex 32)  # 生成随机密钥
DEBUG=False
ENVIRONMENT=production

# 安全配置
ALLOWED_HOSTS=["your-domain.com", "www.your-domain.com"]
CORS_ORIGINS=["https://your-domain.com", "https://www.your-domain.com"]
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000

# 域名配置
DOMAIN=your-domain.com
PROTOCOL=https
API_BASE_URL=https://your-domain.com/api
WS_BASE_URL=wss://your-domain.com/ws

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/production.log

# Redis配置
REDIS_URL=redis://:REDIS_PASSWORD@redis:6379/0
REDIS_PASSWORD=REDIS_PASSWORD

# 性能配置
WORKERS=4
MAX_CONCURRENT_SESSIONS=100

# 监控配置
PROMETHEUS_ENABLED=True
GRAFANA_ENABLED=True
GRAFANA_PASSWORD=GRAFANA_ADMIN_PASSWORD
```

### 测试环境 (.env.test)
```env
# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:test_password@localhost:5432/prompt_gen_test
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen_test
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=test_password

# GLM API配置（测试用）
GLM_API_KEY=test_glm_api_key
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 应用配置
SECRET_KEY=test_secret_key_only_for_testing
DEBUG=False
ENVIRONMENT=testing

# CORS配置
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
CORS_ORIGINS=["http://localhost:3000"]

# 日志配置
LOG_LEVEL=WARNING
LOG_FILE=logs/test.log

# 性能配置（测试环境优化）
WORKERS=1
MAX_CONCURRENT_SESSIONS=5
```

## 🔧 快速配置脚本

### 自动配置脚本
```bash
#!/bin/bash
# auto_config.sh

echo "🚀 AI Agent Prompt Generator 环境配置"

# 生成随机密码和密钥
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# 读取用户输入
echo "请输入配置信息："
read -p "GLM API Key: " GLM_API_KEY
read -p "域名 (如 example.com): " DOMAIN
read -p "环境 (development/production): " ENVIRONMENT

# 创建.env文件
cat > .env << EOF
# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:$DB_PASSWORD@localhost:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=$DB_PASSWORD

# GLM API配置
GLM_API_KEY=$GLM_API_KEY
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 应用配置
SECRET_KEY=$SECRET_KEY
DEBUG=$([ "$ENVIRONMENT" = "development" ] && echo "True" || echo "False")
ENVIRONMENT=$ENVIRONMENT

# 域名配置
DOMAIN=$DOMAIN
ALLOWED_HOSTS=["$DOMAIN", "www.$DOMAIN"]
CORS_ORIGINS=["https://$DOMAIN", "https://www.$DOMAIN"]

# Redis配置
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD

# 日志配置
LOG_LEVEL=$([ "$ENVIRONMENT" = "development" ] && echo "DEBUG" || echo "INFO")
LOG_FILE=logs/$ENVIRONMENT.log
EOF

echo "✅ .env 文件已创建完成！"
```

### PowerShell自动配置脚本
```powershell
# auto_config.ps1

Write-Host "🚀 AI Agent Prompt Generator 环境配置"

# 生成随机密码和密钥
$DB_PASSWORD = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$SECRET_KEY = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$REDIS_PASSWORD = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})

# 读取用户输入
$GLM_API_KEY = Read-Host "GLM API Key"
$DOMAIN = Read-Host "域名 (如 example.com)"
$ENVIRONMENT = Read-Host "环境 (development/production)"

# 创建.env文件
$DEBUG_VALUE = if ($ENVIRONMENT -eq "development") { "True" } else { "False" }
$LOG_LEVEL_VALUE = if ($ENVIRONMENT -eq "development") { "DEBUG" } else { "INFO" }

@"
# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:$DB_PASSWORD@localhost:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=$DB_PASSWORD

# GLM API配置
GLM_API_KEY=$GLM_API_KEY
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 应用配置
SECRET_KEY=$SECRET_KEY
DEBUG=$DEBUG_VALUE
ENVIRONMENT=$ENVIRONMENT

# 域名配置
DOMAIN=$DOMAIN
ALLOWED_HOSTS=["$DOMAIN", "www.$DOMAIN"]
CORS_ORIGINS=["https://$DOMAIN", "https://www.$DOMAIN"]

# Redis配置
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
REDIS_PASSWORD=$REDIS_PASSWORD

# 日志配置
LOG_LEVEL=$LOG_LEVEL_VALUE
LOG_FILE=logs/$ENVIRONMENT.log
"@ | Out-File -FilePath ".env" -Encoding UTF8

Write-Host "✅ .env 文件已创建完成！"
```

## 📋 配置检查清单

### 必须配置项
- [ ] GLM_API_KEY（您的GLM API密钥）
- [ ] SECRET_KEY（应用密钥）
- [ ] DATABASE_PASSWORD（数据库密码）
- [ ] DOMAIN（您的域名，生产环境）

### 可选配置项
- [ ] REDIS_PASSWORD（Redis密码，如果使用Redis）
- [ ] GRAFANA_PASSWORD（监控面板密码，如果启用监控）
- [ ] 邮件配置（如果需要邮件功能）
- [ ] 第三方服务配置（如Sentry、Google Analytics等）

### 环境特定配置
- [ ] 开发环境：DEBUG=True，允许本地域名
- [ ] 生产环境：DEBUG=False，设置真实域名，启用安全配置
- [ ] 测试环境：使用测试数据库，最小化日志

## 🔍 配置验证

创建配置后，运行以下命令验证：

```bash
# 检查环境变量文件
cat .env

# 验证数据库连接
python -c "from src.database.connection import get_database; print('Database OK')"

# 验证GLM API连接
python -c "from src.services.glm_api import GLMClient; print('GLM API OK')"

# 运行系统验证
python system_validation.py
```

## ⚠️ 安全提醒

1. **永远不要将.env文件提交到Git仓库**
2. **生产环境必须使用强密码**
3. **定期更换API密钥和密码**
4. **使用不同的密钥用于不同环境**
5. **限制.env文件的访问权限**：
   ```bash
   chmod 600 .env
   ```

## 🐛 常见问题

### Q: 我应该使用哪个.env模板文件？
A: 推荐使用根目录的`.env.template`，它更完整。

### Q: 配置了.env但应用还是报错？
A: 检查以下几点：
   1. 确保.env文件在正确的目录
   2. 检查配置项是否正确（没有多余空格）
   3. 确保数据库和Redis服务正在运行

### Q: Docker部署时环境变量不生效？
A: 确保：
   1. .env文件在docker-compose.yml同级目录
   2. docker-compose.yml中正确引用了环境变量
   3. 重新构建并启动容器

### Q: 如何在不同环境间切换？
A: 使用不同的.env文件：
   ```bash
   cp .env.development .env  # 切换到开发环境
   cp .env.production .env   # 切换到生产环境
   ```