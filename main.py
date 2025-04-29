import sys
import subprocess
import logging
import os
import re
import traceback
from typing import Any, Dict, Optional
from mcp.server import FastMCP
from dotenv import load_dotenv

CMD_ENCODING = 'GBK'
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(script_dir, '.env'))

DEFAULT_WORKDIR = os.getenv('SANDBOX_PATH') or "D:\\Sandbox"
if not os.path.isdir(DEFAULT_WORKDIR):
    logging.warning(f"默认工作目录 '{DEFAULT_WORKDIR}' 不存在！")

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - Sydney - %(levelname)s - %(message)s')

def process_output_for_message(text: str) -> str:
    """处理输出文本，替换换行符为空格，合并多个空格为一个空格"""
    if not text:
        return ""
    processed = text.replace('\n', ' ')
    processed = re.sub(r'\s+', ' ', processed)
    return processed.strip()

def execute_command(cmd: str, workdir: str) -> Dict[str, Any]:
    """执行 CMD 命令并返回包含 message 和 log 的字典"""
    logging.info(f"执行命令: '{cmd}' (目录: {workdir})")
    final_message = ""
    log_content = ""

    try:
        if not os.path.isdir(workdir):
            err_msg = f"工作目录 '{workdir}' 无效！"
            logging.error(err_msg)
            final_message = f"命令准备失败: {err_msg}"
            log_content = f"命令准备失败..."
            return {"message": final_message, "log": log_content}

        proc = subprocess.run(
            ['cmd', '/c', cmd],
            capture_output=True,
            text=True,
            encoding=CMD_ENCODING,
            errors='replace',
            cwd=workdir,
            check=False
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        returncode = proc.returncode

        if returncode == 0:
            status_msg = "命令执行成功..." 
            processed_stdout = process_output_for_message(stdout)

            log_for_info = f"'{cmd[:30]}{'...' if len(cmd)>30 else ''}' 命令执行成功~ 返回码: {returncode}"
            if stderr:
                 log_for_info += f"\n[stderr]:\n{stderr}"
            logging.info(log_for_info)

            message_parts = [status_msg]
            if processed_stdout:
                message_parts.append(processed_stdout)

            final_message = " ".join(filter(None, message_parts)).strip()
            log_content = "命令执行成功"

        else:
            status_msg = f"命令执行失败..."
            processed_stderr_for_msg = process_output_for_message(stderr)

            message_parts = [status_msg]
            if processed_stderr_for_msg: 
                message_parts.append(processed_stderr_for_msg)

            final_message = " ".join(filter(None, message_parts)).strip()
            log_content = f"命令执行失败... 返回码: {returncode}"

            detailed_log_parts = [f"命令执行失败... 返回码: {returncode}"]
            if stdout:
                detailed_log_parts.append(f"[stdout]:\n{stdout}")
            if stderr:
                detailed_log_parts.append(f"[stderr]:\n{stderr}")
            logging.error("\n".join(detailed_log_parts))

        return {"message": final_message, "log": log_content}

    except FileNotFoundError:
        err_msg = "找不到 'cmd' 命令！请检查系统 PATH 环境变量。"
        final_message = f"命令执行失败: {err_msg}"
        log_content = "命令执行失败... 内部错误"
        logging.error(f"{err_msg}\n{traceback.format_exc()}")
    except OSError as e:
        err_msg = f"OS 错误: {e}"
        final_message = f"命令执行失败: OS 错误 - {e}"
        log_content = "命令执行失败... OS 错误"
        logging.error(f"{err_msg}\n{traceback.format_exc()}")
    except Exception as e:
        err_msg = f"执行命令时发生意外错误: {e}"
        final_message = f"命令执行失败: 发生意外错误 - {e}"
        log_content = "命令执行失败... 意外错误"
        logging.error(f"{err_msg}\n{traceback.format_exc()}")

    return {"message": final_message, "log": log_content}


mcp = FastMCP("Sydney_CMD_Executor")

@mcp.tool()
def execute(command: str, cwd: Optional[str] = None) -> str:
    """执行 CMD 命令并以 key='value' 格式返回结果"""
    target_cwd = cwd or DEFAULT_WORKDIR
    logging.info(f"使用工作目录: {target_cwd}")

    result_dict = execute_command(command, workdir=target_cwd)

    try:
        msg = str(result_dict.get("message", ""))
        log_val = str(result_dict.get("log", ""))

        formatted_string = f"message='{msg}', log='{log_val}'"
        return formatted_string

    except Exception as e:
        logging.error(f"格式化结果字符串时出错: {e}\n{traceback.format_exc()}")
        error_message = f"服务端格式化错误: {e}"
        fallback_string = f"message='格式化结果时出错！', log='{error_message}'"
        return fallback_string
