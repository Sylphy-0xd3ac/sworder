#!/bin/bash
# WebSocket控制系统启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}    WebSocket控制系统${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

# 检查Python是否安装
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_message $RED "错误: 未找到Python3，请先安装Python3"
        exit 1
    fi
    print_message $GREEN "✓ Python3 已安装"
}

# 检查环境变量文件
check_env() {
    if [ ! -f ".env" ]; then
        print_message $YELLOW "未找到.env文件，正在从.env.example创建..."
        cp .env.example .env
        print_message $GREEN "✓ 已创建.env文件，请根据需要修改配置"
    else
        print_message $GREEN "✓ 环境变量文件已存在"
    fi
}

# 启动服务器
start_server() {
    print_message $BLUE "正在启动WebSocket服务器..."
    cd server
    python3 main.py &
    SERVER_PID=$!
    cd ..
    
    # 等待服务器启动
    sleep 2
    
    if kill -0 $SERVER_PID 2>/dev/null; then
        print_message $GREEN "✓ 服务器已启动 (PID: $SERVER_PID)"
        echo $SERVER_PID > .server.pid
    else
        print_message $RED "✗ 服务器启动失败"
        exit 1
    fi
}

# 启动客户端
start_client() {
    print_message $BLUE "正在启动客户端..."
    
    # 检测系统类型
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open client/index.html
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open client/index.html
        elif command -v firefox &> /dev/null; then
            firefox client/index.html
        else
            print_message $YELLOW "无法自动打开浏览器，请手动打开 client/index.html"
        fi
    else
        print_message $YELLOW "请手动在浏览器中打开 client/index.html"
    fi
    
    print_message $GREEN "✓ 客户端已启动"
}

# 启动开发服务器（可选）
start_dev_server() {
    print_message $BLUE "正在启动HTTP开发服务器..."
    python3 -m http.server 8080 --directory client &
    HTTP_PID=$!
    echo $HTTP_PID > .http.pid
    print_message $GREEN "✓ HTTP开发服务器已启动 (PID: $HTTP_PID)"
    print_message $BLUE "访问地址: http://localhost:8080"
}

# 停止服务器
stop_servers() {
    print_message $BLUE "正在停止服务器..."
    
    if [ -f ".server.pid" ]; then
        SERVER_PID=$(cat .server.pid)
        if kill -0 $SERVER_PID 2>/dev/null; then
            kill $SERVER_PID
            print_message $GREEN "✓ WebSocket服务器已停止"
        fi
        rm -f .server.pid
    fi
    
    if [ -f ".http.pid" ]; then
        HTTP_PID=$(cat .http.pid)
        if kill -0 $HTTP_PID 2>/dev/null; then
            kill $HTTP_PID
            print_message $GREEN "✓ HTTP开发服务器已停止"
        fi
        rm -f .http.pid
    fi
}

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  start     启动服务器和客户端 (默认)"
    echo "  server    仅启动服务器"
    echo "  client    仅启动客户端"
    echo "  dev       启动服务器和HTTP开发服务器"
    echo "  stop      停止所有服务器"
    echo "  test      运行测试"
    echo "  help      显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0 start      # 启动完整系统"
    echo "  $0 dev        # 开发模式启动"
    echo "  $0 stop       # 停止所有服务"
}

# 运行测试
run_test() {
    print_message $BLUE "正在运行测试..."
    python3 test_server.py
}

# 清理函数
cleanup() {
    stop_servers
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 主程序
main() {
    print_header
    
    case "${1:-start}" in
        "start")
            check_python
            check_env
            start_server
            start_client
            print_message $GREEN "🎉 系统启动完成！"
            print_message $YELLOW "按 Ctrl+C 停止服务器"
            wait
            ;;
        "server")
            check_python
            check_env
            start_server
            print_message $GREEN "🎉 服务器启动完成！"
            print_message $YELLOW "按 Ctrl+C 停止服务器"
            wait
            ;;
        "client")
            start_client
            ;;
        "dev")
            check_python
            check_env
            start_server
            start_dev_server
            print_message $GREEN "🎉 开发环境启动完成！"
            print_message $YELLOW "按 Ctrl+C 停止服务器"
            wait
            ;;
        "stop")
            stop_servers
            ;;
        "test")
            check_python
            run_test
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_message $RED "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主程序
main "$@"