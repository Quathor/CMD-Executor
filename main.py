import sys
import json
import subprocess
import traceback
import logging
import os
from typing import Any, Dict, Optional
from mcp.server import FastMCP
from dotenv import load_dotenv

CMD_ENCODING = 'GBK'

script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)
logging.info(f"已尝试加载 .env 文件: {dotenv_path}")

DEFAULT_WORKING_DIRECTORY = os.getenv('SANDBOX_PATH')
if not DEFAULT_WORKING_DIRECTORY:
    DEFAULT_WORKING_DIRECTORY = "D:\\Sandbox"
    logging.info("未在环境变量中找到 SANDBOX_PATH，使用硬编码默认路径: D:\\Sandbox")
else:
    logging.info(f"从环境变量 SANDBOX_PATH 加载默认工作目录: {DEFAULT_WORKING_DIRECTORY}")

if not os.path.isdir(DEFAULT_WORKING_DIRECTORY):
     logging.warning(f"警告！默认工作目录 '{DEFAULT_WORKING_DIRECTORY}' 不存在或不是一个目录。")

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - Sydney - %(levelname)s - %(message)s')

def execute_command(cmd_string: str, working_directory: str) -> Dict[str, Any]:
    logging.info(f"准备执行命令: '{cmd_string}' (工作目录: {working_directory})")

    try:
        if not os.path.isdir(working_directory):
             error_msg = f"工作目录 '{working_directory}' 不存在或者不是一个有效的目录！"
             logging.error(error_msg)
             return {"success": False, "error": error_msg, "returncode": -1, "stdout": "", "stderr": ""}

        process = subprocess.run(
            ['cmd', '/c', cmd_string],
            capture_output=True,
            text=True,
            encoding=CMD_ENCODING,
            errors='replace',
            cwd=working_directory,
            check=False
        )

        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        returncode = process.returncode

        logging.info(f"命令执行完毕. 返回码: {returncode}")
        if stdout:
            logging.debug(f"Stdout (已从 {CMD_ENCODING} 解码):\n{stdout[:200]}{'...' if len(stdout)>200 else ''}")
        if stderr:
            logging.debug(f"Stderr (已从 {CMD_ENCODING} 解码):\n{stderr[:200]}{'...' if len(stderr)>200 else ''}")

        result_dict = {}
        if returncode == 0:
            result_dict = {
                "message": f"命令 '{cmd_string[:30]}{'...' if len(cmd_string)>30 else ''}' 在 '{working_directory}' 成功执行了喵~",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode,
                "success": True
            }
        else:
            error_message = f"命令 '{cmd_string[:30]}{'...' if len(cmd_string)>30 else ''}' 在 '{working_directory}' 执行出错了... (返回码: {returncode})"
            if stderr: error_message += f"\n错误详情:\n{stderr}"
            elif stdout: error_message += f"\n输出信息可能包含错误详情:\n{stdout}"
            result_dict = {
                "error": error_message,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode,
                "success": False
            }
        return result_dict

    except FileNotFoundError:
        error_msg = "错误：找不到 'cmd' 命令. 请检查系统环境变量 PATH 是否配置正确。"
        logging.error(error_msg)
        return {"success": False, "error": "找不到 Windows 的 'cmd' 命令... ", "returncode": -1, "stdout": "", "stderr": error_msg}
    except OSError as e:
        error_msg = f"执行命令时发生 OS 错误 (工作目录: '{working_directory}'): {e}"
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        return {"success": False, "error": f"执行命令时发生了系统错误 (工作目录 '{working_directory}' 有问题吗？): {e}", "returncode": -1, "stdout": "", "stderr": str(e)}
    except Exception as e:
        error_msg = f"执行命令时发生意外错误: {e}"
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        return {"success": False, "error": f"执行命令时发生了意料之外的错误: {e}", "returncode": -1, "stdout": "", "stderr": str(e)}

mcp = FastMCP("Sydney_CMD_Executor")

@mcp.tool()
def execute(command: str, cwd: Optional[str] = None) -> str:
    target_cwd = None
    if cwd:
        logging.info(f"使用用户指定的 CWD: {cwd}")
        target_cwd = cwd
    else:
        logging.info(f"未指定 CWD，使用默认工作目录: {DEFAULT_WORKING_DIRECTORY}")
        target_cwd = DEFAULT_WORKING_DIRECTORY

    result_dict = execute_command(command, working_directory=target_cwd)

    try:
        json_string = json.dumps(result_dict, ensure_ascii=False, indent=None)
        return json_string
    except Exception as e:
        logging.error(f"将结果字典序列化为 JSON 时出错: {e}\n{traceback.format_exc()}")
        fallback_error_dict = {
            "success": False,
            "error": f"服务端序列化结果时发生错误: {e}",
            "returncode": -2,
            "stdout": "",
            "stderr": ""
        }
        return json.dumps(fallback_error_dict)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    logging.info(f"当前 Python 进程工作目录已设置为: {os.getcwd()}")

    logging.info(f"CMD 工具启动！默认命令执行目录: {DEFAULT_WORKING_DIRECTORY}")
    logging.info("准备接收指令...")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logging.exception("MCP 服务器运行时发生了一个严重错误！")
    finally:
        logging.info("CMD 工具关闭。")
