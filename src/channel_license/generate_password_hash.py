#!/usr/bin/env python3
"""
生成密码哈希值的工具脚本
"""

import hashlib
import sys

def hash_password(password: str) -> str:
    """计算密码的SHA256哈希值"""
    return hashlib.sha256(password.encode()).hexdigest()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python generate_password_hash.py <password>")
        sys.exit(1)
    
    password = sys.argv[1]
    hashed = hash_password(password)
    print(f"密码 '{password}' 的哈希值:")
    print(hashed)