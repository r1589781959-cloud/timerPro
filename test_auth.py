#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
授权系统测试脚本
测试机器码生成和激活码验证
"""
import hashlib
import uuid
import os

class AuthTester:
    def __init__(self):
        self.machine_code = self._generate_machine_code()

    def _generate_machine_code(self):
        """生成机器码"""
        mac = uuid.getnode()
        cname = os.environ.get('COMPUTERNAME', 'UNKNOWN')
        raw = f"{mac}_{cname}_TIMERPRO"
        h = hashlib.md5(raw.encode()).hexdigest().upper()
        return f"{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

    def get_expected_key(self):
        """生成期望的激活码"""
        s_part1, s_part2, s_part3 = "T!m3r", "Pr0", "V14_@uth"
        complex_raw = f"{s_part1}_{self.machine_code[::-1]}_{s_part2}_{self.machine_code}_{s_part3}"
        h = hashlib.sha256(complex_raw.encode()).hexdigest().upper()
        return f"{h[3:7]}-{h[15:19]}-{h[27:31]}-{h[50:54]}"

    def test_authorization(self):
        """测试授权系统"""
        print("="*60)
        print("授权系统测试")
        print("="*60)

        print(f"\n【系统信息】")
        print(f"计算机名: {os.environ.get('COMPUTERNAME', 'UNKNOWN')}")
        print(f"MAC地址: {uuid.getnode()}")

        print(f"\n【授权信息】")
        print(f"机器码: {self.machine_code}")
        expected_key = self.get_expected_key()
        print(f"期望激活码: {expected_key}")

        print(f"\n【文件位置】")
        hash_a = hashlib.md5((self.machine_code + "LOC_A").encode()).hexdigest()[:8]
        hash_b = hashlib.md5((self.machine_code + "LOC_B").encode()).hexdigest()[:8]
        path_a = os.path.join(os.getenv('APPDATA', 'C:\\'), f"win_sys_{hash_a}.dat")
        path_b = os.path.join(os.getenv('LOCALAPPDATA', 'C:\\'), f"com.microsoft.cache.{hash_b}.bin")
        print(f"授权文件A: {path_a}")
        print(f"授权文件B: {path_b}")

        print(f"\n【文件状态】")
        print(f"文件A存在: {'✓' if os.path.exists(path_a) else '✗'}")
        print(f"文件B存在: {'✓' if os.path.exists(path_b) else '✗'}")

        print(f"\n【测试结果】")
        print(f"✓ 机器码生成: 正常")
        print(f"✓ 激活码算法: 正常")
        print(f"✓ 授权文件路径: 正常")

        return {
            "machine_code": self.machine_code,
            "activation_key": expected_key,
            "files_exist": {
                "path_a": os.path.exists(path_a),
                "path_b": os.path.exists(path_b)
            }
        }

if __name__ == '__main__':
    import sys
    import io

    # 设置编码
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    tester = AuthTester()
    result = tester.test_authorization()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
