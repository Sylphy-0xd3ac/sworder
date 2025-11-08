#!/usr/bin/env python3
"""
测试脚本：验证服务器作为模块导入和后台运行的功能
"""

import time
import os
import sys

# 添加server目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

def test_server_import():
    """测试服务器导入和后台运行"""
    print("测试1: 导入服务器模块...")
    try:
        from main import start_server, stop_server
        print("✓ 服务器模块导入成功")
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False
    
    print("\n测试2: 启动后台服务器...")
    try:
        # 设置测试环境变量
        os.environ['WS_HOST'] = 'localhost'
        os.environ['WS_PORT'] = '8766'
        os.environ['WS_TOKEN'] = 'test-token'
        
        server = start_server()
        print("✓ 后台服务器启动成功")
        
        # 等待服务器完全启动
        time.sleep(2)
        
        print("\n测试3: 停止服务器...")
        stop_server()
        print("✓ 服务器停止成功")
        
    except Exception as e:
        print(f"✗ 服务器操作失败: {e}")
        return False
    
    print("\n测试4: 验证环境变量加载...")
    try:
        # 测试.env文件加载
        with open('.env', 'w') as f:
            f.write("WS_HOST=env-test\n")
            f.write("WS_PORT=9999\n")
            f.write("WS_TOKEN=env-token\n")
        
        # 重新导入以测试环境变量加载
        import importlib
        import main
        importlib.reload(main)
        
        main.load_env()
        
        assert os.environ.get('WS_HOST') == 'env-test'
        assert os.environ.get('WS_PORT') == '9999'
        assert os.environ.get('WS_TOKEN') == 'env-token'
        
        print("✓ 环境变量加载成功")
        
    except Exception as e:
        print(f"✗ 环境变量测试失败: {e}")
        return False
    finally:
        # 清理测试文件
        if os.path.exists('.env'):
            os.remove('.env')
    
    print("\n🎉 所有测试通过！")
    return True

if __name__ == '__main__':
    test_server_import()