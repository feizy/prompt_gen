#!/bin/bash

# AI Agent Prompt Generator - 快速部署脚本
# Quick Deployment Script for AI Agent Prompt Generator

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# 检查系统要求
check_requirements() {
    print_header "🔍 检查系统要求..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装。请先安装Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_message "✓ Docker已安装: $(docker --version)"

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装。请先安装Docker Compose"
        exit 1
    fi
    print_message "✓ Docker Compose已安装: $(docker-compose --version)"

    # 检查Git
    if ! command -v git &> /dev/null; then
        print_error "Git未安装。请先安装Git"
        exit 1
    fi
    print_message "✓ Git已安装: $(git --version)"

    # 检查端口占用
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口8000已被占用，请确保端口可用"
    fi

    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口3000已被占用，请确保端口可用"
    fi

    print_message "✓ 系统要求检查完成"
}

# 创建环境配置
setup_environment() {
    print_header "⚙️ 配置环境变量..."

    # 检查.env文件是否存在
    if [ ! -f ".env" ]; then
        print_message "创建.env文件..."

        # 生成随机密钥
        SECRET_KEY=$(openssl rand -hex 32)

        # 创建.env文件
        cat > .env << EOF
# 数据库配置
DATABASE_URL=postgresql://prompt_gen_user:$(openssl rand -base64 32)@postgres:5432/prompt_gen
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=prompt_gen
DATABASE_USER=prompt_gen_user
DATABASE_PASSWORD=$(openssl rand -base64 32)

# GLM API配置 (请替换为您的实际API密钥)
GLM_API_KEY=your_glm_api_key_here
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
GLM_MODEL=glm-4

# 应用配置
SECRET_KEY=$SECRET_KEY
DEBUG=True
CORS_ORIGINS=["http://localhost:3000"]

# Redis配置
REDIS_URL=redis://redis:6379/0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
EOF

        print_warning "⚠️  请编辑.env文件，设置您的GLM_API_KEY"
        print_message "✓ .env文件已创建"
    else
        print_message "✓ .env文件已存在"
    fi
}

# 选择部署模式
choose_deployment_mode() {
    print_header "🚀 选择部署模式..."

    echo "请选择部署模式:"
    echo "1) 开发环境 (Development)"
    echo "2) 生产环境 (Production)"
    echo "3) 仅后端 (Backend Only)"
    echo "4) 仅前端 (Frontend Only)"

    read -p "请输入选择 (1-4): " mode

    case $mode in
        1)
            DEPLOYMENT_MODE="development"
            print_message "选择: 开发环境"
            ;;
        2)
            DEPLOYMENT_MODE="production"
            print_message "选择: 生产环境"
            ;;
        3)
            DEPLOYMENT_MODE="backend-only"
            print_message "选择: 仅后端"
            ;;
        4)
            DEPLOYMENT_MODE="frontend-only"
            print_message "选择: 仅前端"
            ;;
        *)
            print_error "无效选择，使用默认开发环境"
            DEPLOYMENT_MODE="development"
            ;;
    esac
}

# 开发环境部署
deploy_development() {
    print_header "🛠️ 部署开发环境..."

    # 检查Python环境
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3未安装"
        exit 1
    fi

    # 检查Node.js环境
    if ! command -v node &> /dev/null; then
        print_error "Node.js未安装"
        exit 1
    fi

    # 后端设置
    print_message "设置后端..."
    cd backend

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_message "✓ Python虚拟环境已创建"
    fi

    source venv/bin/activate
    pip install -r requirements.txt

    # 前端设置
    print_message "设置前端..."
    cd ../frontend
    npm install

    # 启动服务
    print_message "启动开发服务器..."
    cd ..

    print_header "🎉 开发环境部署完成!"
    echo ""
    echo "启动服务:"
    echo "终端1 - 启动后端:"
    echo "  cd backend && source venv/bin/activate && uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    echo "终端2 - 启动前端:"
    echo "  cd frontend && npm start"
    echo ""
    echo "访问地址:"
    echo "  前端: http://localhost:3000"
    echo "  后端API: http://localhost:8000"
    echo "  API文档: http://localhost:8000/docs"
}

# Docker部署
deploy_docker() {
    print_header "🐳 部署Docker环境..."

    # 选择Compose文件
    if [ "$DEPLOYMENT_MODE" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
        print_message "使用生产环境配置"
    else
        COMPOSE_FILE="docker-compose.yml"
        print_message "使用开发环境配置"
    fi

    # 检查compose文件是否存在
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "$COMPOSE_FILE 文件不存在"
        exit 1
    fi

    # 停止现有服务
    print_message "停止现有服务..."
    docker-compose -f $COMPOSE_FILE down

    # 构建并启动服务
    print_message "构建并启动服务..."
    docker-compose -f $COMPOSE_FILE up --build -d

    # 等待服务启动
    print_message "等待服务启动..."
    sleep 10

    # 运行数据库迁移
    if [ "$DEPLOYMENT_MODE" != "frontend-only" ]; then
        print_message "运行数据库迁移..."
        docker-compose -f $COMPOSE_FILE exec -T backend python -m alembic upgrade head || print_warning "数据库迁移失败，请手动检查"
    fi

    # 检查服务状态
    print_message "检查服务状态..."
    docker-compose -f $COMPOSE_FILE ps

    print_header "🎉 Docker部署完成!"
    echo ""
    echo "服务访问地址:"

    if [ "$DEPLOYMENT_MODE" != "backend-only" ]; then
        echo "  前端: http://localhost:3000"
    fi

    if [ "$DEPLOYMENT_MODE" != "frontend-only" ]; then
        echo "  后端API: http://localhost:8000"
        echo "  API文档: http://localhost:8000/docs"
    fi

    echo ""
    echo "查看日志: docker-compose -f $COMPOSE_FILE logs -f"
    echo "停止服务: docker-compose -f $COMPOSE_FILE down"
}

# 仅后端部署
deploy_backend_only() {
    print_header "🔧 仅部署后端..."

    cd backend

    # 使用Docker部署后端
    if command -v docker-compose &> /dev/null; then
        print_message "使用Docker部署后端..."
        docker-compose up --build -d postgres redis backend

        # 等待服务启动
        sleep 5

        # 运行数据库迁移
        docker-compose exec backend python -m alembic upgrade head

        print_header "🎉 后端部署完成!"
        echo "后端API: http://localhost:8000"
        echo "API文档: http://localhost:8000/docs"
        echo "查看日志: docker-compose logs -f backend"
    else
        print_error "需要Docker Compose来部署后端服务"
        exit 1
    fi
}

# 仅前端部署
deploy_frontend_only() {
    print_header "🎨 仅部署前端..."

    cd frontend

    if command -v docker-compose &> /dev/null; then
        print_message "使用Docker部署前端..."
        docker-compose up --build -d frontend

        print_header "🎉 前端部署完成!"
        echo "前端: http://localhost:3000"
        echo "查看日志: docker-compose logs -f frontend"
    else
        print_message "使用本地环境部署前端..."
        npm install
        npm run build

        print_header "🎉 前端构建完成!"
        echo "构建文件位于: build/"
        echo "您可以使用任何Web服务器托管这些文件"
    fi
}

# 健康检查
health_check() {
    print_header "🏥 执行健康检查..."

    # 等待服务完全启动
    sleep 5

    # 检查后端健康
    if [ "$DEPLOYMENT_MODE" != "frontend-only" ]; then
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_message "✓ 后端服务健康"
        else
            print_warning "⚠️ 后端服务可能未正常启动"
        fi
    fi

    # 检查前端
    if [ "$DEPLOYMENT_MODE" != "backend-only" ]; then
        if curl -f http://localhost:3000 &> /dev/null; then
            print_message "✓ 前端服务健康"
        else
            print_warning "⚠️ 前端服务可能未正常启动"
        fi
    fi

    # 运行系统验证
    if command -v python3 &> /dev/null && [ -f "system_validation.py" ]; then
        print_message "运行系统验证..."
        python3 system_validation.py --base-url http://localhost:8000 || print_warning "系统验证发现问题，请检查日志"
    fi
}

# 显示帮助信息
show_help() {
    echo "AI Agent Prompt Generator - 快速部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  -m, --mode MODE         部署模式 (development|production|backend-only|frontend-only)"
    echo "  -q, --quick            快速部署 (跳过部分检查)"
    echo "  --check-only           仅执行环境检查"
    echo "  --health-only          仅执行健康检查"
    echo ""
    echo "示例:"
    echo "  $0                     # 交互式部署"
    echo "  $0 -m development      # 开发环境部署"
    echo "  $0 -m production       # 生产环境部署"
    echo "  $0 --check-only        # 仅检查环境"
    echo ""
}

# 主函数
main() {
    print_header "🚀 AI Agent Prompt Generator - 快速部署脚本"
    echo ""

    # 解析命令行参数
    QUICK_DEPLOY=false
    CHECK_ONLY=false
    HEALTH_ONLY=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -m|--mode)
                DEPLOYMENT_MODE="$2"
                shift 2
                ;;
            -q|--quick)
                QUICK_DEPLOY=true
                shift
                ;;
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --health-only)
                HEALTH_ONLY=true
                shift
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 仅执行健康检查
    if [ "$HEALTH_ONLY" = true ]; then
        health_check
        exit 0
    fi

    # 仅执行环境检查
    if [ "$CHECK_ONLY" = true ]; then
        check_requirements
        print_header "✅ 环境检查完成"
        exit 0
    fi

    # 检查要求
    if [ "$QUICK_DEPLOY" = false ]; then
        check_requirements
    fi

    # 设置环境
    setup_environment

    # 选择部署模式
    if [ -z "$DEPLOYMENT_MODE" ]; then
        choose_deployment_mode
    fi

    # 根据模式执行部署
    case $DEPLOYMENT_MODE in
        development)
            deploy_development
            ;;
        production)
            deploy_docker
            ;;
        backend-only)
            deploy_backend_only
            ;;
        frontend-only)
            deploy_frontend_only
            ;;
        *)
            print_error "无效的部署模式: $DEPLOYMENT_MODE"
            exit 1
            ;;
    esac

    # 健康检查
    if [ "$QUICK_DEPLOY" = false ]; then
        health_check
    fi

    print_header "🎉 部署完成!"
    echo ""
    echo "📚 更多信息:"
    echo "  - 部署文档: DEPLOYMENT.md"
    echo "  - 测试文档: TESTING.md"
    echo "  - 系统验证: python system_validation.py"
    echo ""
    echo "🐛 如遇问题，请查看:"
    echo "  - 日志文件: docker-compose logs -f"
    echo "  - 故障排除: DEPLOYMENT.md#故障排除"
    echo ""
}

# 执行主函数
main "$@"