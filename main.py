import sys
import subprocess
import logging
import os
import re
import traceback
from typing import Any, Dict, Optional
from mcp.server import FastMCP
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(script_dir, '.env'))

CMD_ENCODING = 'GBK'

DEFAULT_WORKDIR = os.getenv('SANDBOX_PATH') or "D:\\Sandbox"
if not os.path.isdir(DEFAULT_WORKDIR):
    logging.warning(f"默认工作目录 '{DEFAULT_WORKDIR}' 不存在！")

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - Sydney - %(levelname)s - %(message)s')

def process_output_for_message(text: str) -> str:
    if not text:
        return ""
    processed = text.replace('\r\n', ' ').replace('\n', ' ')
    processed = re.sub(r'\s+', ' ', processed)
    return processed.strip()

def decode_with_fallback(byte_content: bytes, encodings: list[str]) -> str:
    if not byte_content:
        return ""

    for i, encoding in enumerate(encodings):
        try:
            errors = 'strict' if i == 0 else 'replace'
            decoded_text = byte_content.decode(encoding, errors=errors)
            if '\ufffd' in decoded_text and errors == 'replace':
                 if decoded_text.count('\ufffd') > len(decoded_text) / 10: # 如果替换字符占比超过10%，可能不是正确编码
                     logging.debug(f"使用 {encoding} 解码包含大量替换字符，可能是错误编码")
                     continue 
            logging.debug(f"成功使用 {encoding} ({errors}) 解码")
            return decoded_text
        except UnicodeDecodeError:
            logging.debug(f"无法使用 {encoding} 解码")
            continue
        except Exception as e:
            logging.debug(f"使用 {encoding} 解码时发生其他错误: {e}")
            continue

    logging.error(f"所有解码尝试 ({encodings}) 都失败！")
    return f"解码失败，尝试了 {', '.join(encodings)}。原始字节前100: {byte_content[:100]}..."


def execute_command(cmd: str, workdir: str) -> Dict[str, Any]:
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
            text=False, 
            cwd=workdir,
            check=False,
            # timeout=60 # 可以考虑增加超时设置
        )

        stdout_bytes = proc.stdout
        stderr_bytes = proc.stderr
        returncode = proc.returncode

        stderr = decode_with_fallback(stderr_bytes, [CMD_ENCODING, 'utf-8', 'latin-1']).strip()

        command_lower = cmd.strip().lower()
        if command_lower.startswith('curl ') or command_lower.startswith('wsl curl '):
             stdout = decode_with_fallback(stdout_bytes, ['utf-8', CMD_ENCODING, 'latin-1']).strip()
        else:
             stdout = decode_with_fallback(stdout_bytes, [CMD_ENCODING, 'utf-8', 'latin-1']).strip()


        if returncode == 0:
            status_msg = "命令执行成功..."
            processed_stdout_for_msg = process_output_for_message(stdout)

            log_for_info = f"'{cmd[:30]}{'...' if len(cmd)>30 else ''}' 命令执行成功，返回码: {returncode}"
            if stderr:
                 log_for_info += f"\n[stderr]:\n{stderr}"
            log_detail = f"返回码: {returncode}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
            logging.info(f"命令执行日志详情:\n{log_detail}")


            message_parts = [status_msg]
            if processed_stdout_for_msg:
                message_parts.append(processed_stdout_for_msg)

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

            log_detail = f"命令执行失败... 返回码: {returncode}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
            logging.error(f"命令执行日志详情:\n{log_detail}")

        return {"message": str(final_message), "log": str(log_content)}

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

    return {"message": str(final_message), "log": str(log_content)}


mcp = FastMCP("Sydney_CMD_Executor")

@mcp.tool()
def execute(command: str, cwd: Optional[str] = None) -> str:
    """执行 CMD 命令并以 key='value' 格式返回结果"""
    target_cwd = cwd or DEFAULT_WORKDIR
    logging.info(f"使用工作目录: {target_cwd}")

    result_dict = execute_command(command, workdir=target_cwd)

    try:
        msg = result_dict.get("message", "")
        log_val = result_dict.get("log", "")

        formatted_string = f"message={repr(msg)}, log={repr(log_val)}"
        return formatted_string

    except Exception as e:
        logging.error(f"格式化结果字符串时出错: {e}\n{traceback.format_exc()}")
        error_message = f"服务端格式化错误: {e}"
        # 回退时也使用 repr()
        fallback_string = f"message={repr('格式化结果时出错！')}, log={repr(error_message)}"
        return fallback_string

if __name__ == "__main__":
    os.chdir(script_dir)
    logging.info(f"切换工作目录到脚本所在位置: {os.getcwd()}")
    logging.info(f"CMD工具启动，默认目录: {DEFAULT_WORKDIR}")
    logging.info("准备接收指令...")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logging.exception("MCP服务器运行时发生错误！")
    finally:
        logging.info("CMD工具关闭。")
