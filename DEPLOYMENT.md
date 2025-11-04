# 部署指南 (Deployment Guide)

本文档提供了AI Agent Prompt Generator系统的完整部署指南，包括开发环境、生产环境和多种云部署选项。

## 目录

1. [系统要求](#系统要求)
2. [开发环境部署](#开发环境部署)
3. [Docker部署](#docker部署)
4. [生产环境部署](#生产环境部署)
5. [云服务部署](#云服务部署)
6. [环境配置](#环境配置)
7. [监控和维护](#监控和维护)
8. [故障排除](#故障排除)

## 系统要求

### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 20GB可用空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **CPU**: 4核心或更多
- **内存**: 8GB RAM或更多
- **存储**: 50GB SSD
- **网络**: 高速互联网连接

### 软件要求
- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 13+
- **Redis**: 6+ (可选，用于缓存)
- **Docker**: 20+ (可选)
- **Git**: 2.30+

## 开发环境部署

### 1. 克隆代码库

```bash
git clone https://github.com/feizy/prompt_gen.git
cd prompt_gen
```

### 2. 后端设置

```bash
# 进入后端目录
cd backend

# 创建Python虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt

# 配置环境变量
cp .env.example .env
```

### 3. 前端设置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 或使用yarn
yarn install
```

### 4. 数据库设置

```bash
# 安装PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS (使用Homebrew)
brew install postgresql
brew services start postgresql

# 创建数据库
sudo -u postgres createdb prompt_gen

# 创建用户
sudo -u postgres createuser --interactive prompt_gen_user
```

### 5. 环境变量配置

创建 `backend/.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:password@localhost/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=your_secure_password

# GLM API配置
GLM_API_KEY=your_glm_api_key_here
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 应用配置
SECRET_KEY=your_secret_key_here_change_in_production
DEBUG=True
CORS_ORIGINS=["http://localhost:3000"]

# Redis配置 (可选)
REDIS_URL=redis://localhost:6379/0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 6. 数据库迁移

```bash
cd backend

# 运行数据库迁移
python -m alembic upgrade head

# 或使用迁移脚本
python scripts/migrate_database.py
```

### 7. 启动开发服务器

```bash
# 启动后端 (终端1)
cd backend
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# 启动前端 (终端2)
cd frontend
npm start

# 应用将在以下地址可用：
# 前端: http://localhost:3000
# 后端API: http://localhost:8000
# API文档: http://localhost:8000/docs
```

## Docker部署

### 1. 创建Docker Compose文件

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  # PostgreSQL数据库
  postgres:
    image: postgres:15
    container_name: prompt_gen_db
    environment:
      POSTGRES_DB: prompt_gen
      POSTGRES_USER: prompt_gen_user
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - prompt_gen_network
    restart: unless-stopped

  # Redis缓存 (可选)
  redis:
    image: redis:7-alpine
    container_name: prompt_gen_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - prompt_gen_network
    restart: unless-stopped

  # 后端API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: prompt_gen_backend
    environment:
      - DATABASE_URL=postgresql://prompt_gen_user:your_secure_password@postgres:5432/prompt_gen
      - REDIS_URL=redis://redis:6379/0
      - GLM_API_KEY=${GLM_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - prompt_gen_network
    volumes:
      - ./backend/logs:/app/logs
    restart: unless-stopped

  # 前端
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - REACT_APP_API_URL=http://localhost:8000
    container_name: prompt_gen_frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - prompt_gen_network
    restart: unless-stopped

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: prompt_gen_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    networks:
      - prompt_gen_network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  prompt_gen_network:
    driver: bridge
```

### 2. 创建Dockerfile

#### 后端Dockerfile (`backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 前端Dockerfile (`frontend/Dockerfile`)

```dockerfile
# 构建阶段
FROM node:18-alpine as build

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建应用
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制构建文件
COPY --from=build /app/build /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]
```

### 3. 创建Nginx配置

创建 `nginx/nginx.conf`：

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    # 前端应用
    server {
        listen 80;
        server_name localhost;

        # 前端静态文件
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API请求
        location /api/ {
            rewrite /api/(.*) /v1/$1 break;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket连接
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 4. 启动Docker环境

```bash
# 创建环境变量文件
echo "GLM_API_KEY=your_glm_api_key" > .env
echo "SECRET_KEY=your_secret_key" >> .env

# 构建并启动所有服务
docker-compose up --build -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

## 生产环境部署

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y curl wget git nginx postgresql postgresql-contrib redis-server

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 防火墙配置

```bash
# 配置UFW防火墙
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000  # 后端API (如果直接暴露)
```

### 3. SSL证书配置

```bash
# 使用Let's Encrypt获取免费SSL证书
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com

# 自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 4. 生产环境变量

创建 `backend/.env.production`：

```env
# 生产环境配置
DEBUG=False
SECRET_KEY=your_very_secure_secret_key_here
CORS_ORIGINS=["https://yourdomain.com"]

# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:secure_password@postgres:5432/prompt_gen
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=very_secure_password

# GLM API配置
GLM_API_KEY=your_production_glm_api_key
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# Redis配置
REDIS_URL=redis://redis:6379/0

# 日志配置
LOG_LEVEL=WARNING
LOG_FILE=logs/production.log

# 安全配置
ALLOWED_HOSTS=["yourdomain.com", "www.yourdomain.com"]
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

### 5. 生产Docker Compose

创建 `docker-compose.prod.yml`：

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: prompt_gen_db_prod
    environment:
      POSTGRES_DB: prompt_gen
      POSTGRES_USER: prompt_gen_user
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - prompt_gen_network
    restart: always
    # 不暴露端口到主机，仅内部访问

  redis:
    image: redis:7-alpine
    container_name: prompt_gen_redis_prod
    volumes:
      - redis_data:/data
    networks:
      - prompt_gen_network
    restart: always
    # 不暴露端口到主机

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: prompt_gen_backend_prod
    env_file:
      - backend/.env.production
    depends_on:
      - postgres
      - redis
    networks:
      - prompt_gen_network
    volumes:
      - ./backend/logs:/app/logs
      - ./backups:/backups
    restart: always
    # 不暴露端口，通过nginx访问

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        - REACT_APP_API_URL=https://yourdomain.com/api
    container_name: prompt_gen_frontend_prod
    networks:
      - prompt_gen_network
    restart: always

  nginx:
    image: nginx:alpine
    container_name: prompt_gen_nginx_prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - ./backend/logs:/var/log/nginx
    depends_on:
      - frontend
      - backend
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

### 6. 启动生产环境

```bash
# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up --build -d

# 运行数据库迁移
docker-compose -f docker-compose.prod.yml exec backend python -m alembic upgrade head

# 创建超级用户 (可选)
docker-compose -f docker-compose.prod.yml exec backend python scripts/create_superuser.py
```

## 云服务部署

### 1. AWS部署

#### EC2部署

```bash
# 1. 创建EC2实例
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d3164 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxxx \
  --user-data file://user-data.sh

# 2. 用户脚本 (user-data.sh)
#!/bin/bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose nginx
systemctl start docker
systemctl enable docker

# 拉取代码
git clone https://github.com/feizy/prompt_gen.git /opt/prompt_gen
cd /opt/prompt_gen

# 启动服务
docker-compose -f docker-compose.prod.yml up -d
```

#### ECS部署

创建 `ecs-task-definition.json`：

```json
{
  "family": "prompt-gen",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "your-ecr-repo/backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://..."
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/prompt-gen",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 2. Google Cloud Platform部署

#### Cloud Run部署

```bash
# 1. 构建并推送镜像
gcloud builds submit --tag gcr.io/PROJECT_ID/prompt-gen-backend

# 2. 部署到Cloud Run
gcloud run deploy prompt-gen-backend \
  --image gcr.io/PROJECT_ID/prompt-gen-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql://...

# 3. 部署前端到Firebase Hosting
firebase init hosting
firebase deploy
```

### 3. Azure部署

#### Container Instances

```bash
# 1. 创建资源组
az group create --name prompt-gen-rg --location eastus

# 2. 部署容器组
az container create \
  --resource-group prompt-gen-rg \
  --name prompt-gen-app \
  --image your-registry/prompt-gen:latest \
  --dns-name-label prompt-gen-unique \
  --ports 80 443 \
  --environment-variables \
    DATABASE_URL=postgresql://... \
    GLM_API_KEY=your-key
```

### 4. 阿里云部署

#### 容器服务ACK

```yaml
# kubernetes-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prompt-gen-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: prompt-gen-backend
  template:
    metadata:
      labels:
        app: prompt-gen-backend
    spec:
      containers:
      - name: backend
        image: registry.cn-hangzhou.aliyuncs.com/your-namespace/prompt-gen:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: prompt-gen-secrets
              key: database-url
---
apiVersion: v1
kind: Service
metadata:
  name: prompt-gen-backend-service
spec:
  selector:
    app: prompt-gen-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 环境配置

### 开发环境配置 (.env.development)

```env
DEBUG=True
LOG_LEVEL=DEBUG
CORS_ORIGINS=["http://localhost:3000"]
DATABASE_URL=postgresql://localhost/prompt_gen_dev
GLM_API_KEY=dev_api_key
```

### 测试环境配置 (.env.test)

```env
DEBUG=True
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://localhost/prompt_gen_test
GLM_API_KEY=test_api_key
SECRET_KEY=test_secret_key
```

### 生产环境配置 (.env.production)

```env
DEBUG=False
LOG_LEVEL=ERROR
CORS_ORIGINS=["https://yourdomain.com"]
DATABASE_URL=postgresql://prod_user:secure_pass@db-host/prompt_gen
GLM_API_KEY=prod_api_key
SECRET_KEY=very_secure_secret_key
SSL_REQUIRED=True
```

## 监控和维护

### 1. 日志管理

```bash
# 查看应用日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 日志轮转配置
sudo nano /etc/logrotate.d/prompt-gen
```

### 2. 健康检查

```bash
# API健康检查
curl http://localhost:8000/health

# 系统健康检查
python system_validation.py --base-url http://yourdomain.com
```

### 3. 备份策略

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# 数据库备份
docker-compose exec postgres pg_dump -U prompt_gen_user prompt_gen > $BACKUP_DIR/db_backup_$DATE.sql

# 文件备份
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz ./backend/logs ./frontend/build

# 清理旧备份 (保留7天)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### 4. 性能监控

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  grafana_data:
```

## 故障排除

### 常见问题

#### 1. 数据库连接失败

```bash
# 检查数据库状态
docker-compose exec postgres pg_isready

# 检查连接字符串
docker-compose exec backend python -c "from src.database.connection import get_database; print('Connection OK')"
```

#### 2. GLM API错误

```bash
# 检查API密钥
curl -H "Authorization: Bearer $GLM_API_KEY" \
     https://open.bigmodel.cn/api/paas/v4/models

# 查看API调用日志
docker-compose logs backend | grep GLM
```

#### 3. WebSocket连接问题

```bash
# 测试WebSocket连接
wscat -c ws://localhost:8000/ws/test-session

# 检查防火墙设置
sudo ufw status
```

#### 4. 前端构建失败

```bash
# 清除缓存
cd frontend
rm -rf node_modules package-lock.json
npm install

# 检查环境变量
npm run build
```

### 性能优化

#### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM sessions WHERE status = 'active';
```

#### 2. 缓存配置

```python
# Redis缓存配置
REDIS_CACHE_TTL = 3600  # 1小时
CACHE_KEYS = {
    'session_list': 'sessions:list',
    'user_sessions': 'sessions:user:{user_id}',
    'agent_status': 'agents:status'
}
```

#### 3. 负载均衡

```nginx
upstream backend_pool {
    least_conn;
    server backend1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server backend2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server backend3:8000 weight=1 max_fails=3 fail_timeout=30s;
}
```

### 安全加固

#### 1. 应用安全

```python
# 安全中间件
SECURE_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
}
```

#### 2. 网络安全

```bash
# 防火墙规则
sudo ufw allow from trusted.ip.to.here port 22
sudo ufw allow from trusted.ip.to.here port 5432
sudo ufw deny 5432  # 禁止外部访问数据库
```

#### 3. 定期更新

```bash
#!/bin/bash
# update_system.sh
apt update && apt upgrade -y
docker-compose pull
docker-compose up -d
docker system prune -f
```

---

## 总结

本部署指南涵盖了从开发环境到生产环境的完整部署流程。根据您的具体需求选择合适的部署方式：

- **开发环境**: 直接运行或使用Docker Compose
- **生产环境**: 使用Docker Compose或Kubernetes
- **云部署**: 根据偏好选择AWS、GCP、Azure或阿里云

如有任何部署问题，请参考故障排除部分或提交Issue。