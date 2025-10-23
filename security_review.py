import ast
from typing import List, Dict, Any

# 简易安全代码审查器：针对用户提交的函数工具代码进行静态检测
# 目标：阻断可能对系统造成破坏的操作（高危），并提示潜在风险（中低危）

# 黑名单命令（包含常见 Linux/Windows 破坏性命令，以及会被禁止的系统管理命令）
BLACKLIST_COMMANDS = {
    # Linux 常见破坏性/系统命令
    'rm', 'rm -rf', 'reboot', 'shutdown', 'mount', 'umount', 'service', 'route', 'sysctl', 'systemctl',
    'useradd', 'userdel', 'usermod', 'groupadd', 'groupdel', 'groupmod', 'passwd', 'killall', 'pkill',
    'lvremove', 'pvremove', 'vgremove',
    # Windows 常见破坏性命令/操作
    'del', 'erase', 'format', 'shutdown', 'rmdir', 'rd', 'sc', 'net user', 'reg add', 'reg delete', 'reg import',
}

# 高危函数/调用列表（静态禁止）
HIGH_RISK_FUNCS = {
    'os.system', 'os.popen', 'subprocess.Popen', 'subprocess.run', 'subprocess.call',
    'subprocess.check_output', 'eval', 'exec', '__import__',
}

# 破坏性文件操作（中危，根据使用场景提升为高危）
DESTRUCTIVE_FILE_FUNCS = {
    'shutil.rmtree', 'os.remove', 'os.unlink', 'os.rmdir'
}

# 网络/外部交互（提示中危）
NETWORK_FUNCS = {
    'requests.get', 'requests.post', 'requests.put', 'requests.delete',
    'socket.socket', 'http.client', 'urllib.request', 'urllib3.PoolManager'
}


def _get_full_name(node: ast.AST) -> str:
    """获取调用节点的全限定名称，如 subprocess.run / os.system / requests.get"""
    if isinstance(node, ast.Attribute):
        value = _get_full_name(node.value)
        return f"{value}.{node.attr}" if value else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ''


def _is_string_command(arg: ast.AST) -> str:
    """如果参数是字符串常量，返回其值，否则返回空字符串"""
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value.strip().lower()
    return ''


def _contains_blacklisted_command(command: str) -> bool:
    command_low = command.lower()
    for bad in BLACKLIST_COMMANDS:
        if bad in command_low:
            return True
    return False


def review_tool_code(code: str) -> Dict[str, Any]:
    """
    对用户提交的代码字符串进行安全性审查。

    返回: {
      'safe': bool,           # 是否通过
      'issues': [str],        # 问题描述列表（中文）
      'summary': str          # 总结说明
    }
    """
    issues: List[str] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            'safe': False,
            'issues': [f"代码语法错误：{e}"],
            'summary': '提交的代码无法解析，请修正语法后再试'
        }

    high_risk_found = False

    for node in ast.walk(tree):
        # 检测调用
        if isinstance(node, ast.Call):
            func_name = _get_full_name(node.func)

            # 高危调用：直接判定不通过
            if func_name in HIGH_RISK_FUNCS:
                # 检查 subprocess 是否使用 shell=True 或执行黑名单命令
                if func_name.startswith('subprocess.') or func_name in {'os.system', 'os.popen'}:
                    shell_true = any(
                        isinstance(kw, ast.keyword) and kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value is True
                        for kw in node.keywords
                    )
                    # 首个参数可能是命令字符串
                    cmd_str = ''
                    if node.args:
                        cmd_str = _is_string_command(node.args[0])

                    if shell_true:
                        issues.append(f"高危：使用 {func_name} 且 shell=True，可能执行系统命令")
                        high_risk_found = True
                    if cmd_str and _contains_blacklisted_command(cmd_str):
                        issues.append(f"高危：{func_name} 执行黑名单命令：{cmd_str}")
                        high_risk_found = True

                if func_name in {'eval', 'exec', '__import__'}:
                    issues.append(f"高危：检测到 {func_name} 调用，存在执行任意代码风险")
                    high_risk_found = True

            # 破坏性文件操作：记录并视情况判定
            if func_name in DESTRUCTIVE_FILE_FUNCS:
                issues.append(f"中危：检测到破坏性文件操作 {func_name}，可能删除系统/用户文件")

            # 网络交互：记录提示
            if any(func_name.startswith(net) for net in NETWORK_FUNCS):
                issues.append(f"中危：检测到网络/外部交互 {func_name}，请确保安全使用和可信目的")

            # open 写入模式提示
            if func_name == 'open' and len(node.args) >= 2:
                mode = _is_string_command(node.args[1])
                if any(m in mode for m in ['w', 'a', 'x']):
                    issues.append("中危：检测到文件写入操作 open(..., 'w/ a/ x')，请确保不覆盖或破坏系统文件")

        # import 检测（弱指示）
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.name
                if name in {'os', 'subprocess', 'shutil'}:
                    issues.append(f"提示：导入了 {name} 模块，请谨慎使用系统/文件相关操作")

    safe = not high_risk_found

    # 若存在大量中危/提示信息，也给出综合说明
    summary = (
        '未发现高危操作，存在一些中危/提示项，请谨慎审阅'
        if safe and issues else
        '发现高危操作，已拒绝；请移除高危代码后再提交'
    )

    return {
        'safe': safe,
        'issues': issues,
        'summary': summary,
    }