"""读取项目API Key并准备BL凭据环境。"""

from .environment import Project, SetupError, child_environment


def read_api_key(project: Project) -> str:
    """读取项目.env中的API Key并检查空值与内部空白。"""
    from dotenv import dotenv_values

    path = project.path(".env")
    if not path.is_file():
        raise SetupError("尚未配置 API Key。请将项目中的 .env.example 复制为 .env，并填写 DASHSCOPE_API_KEY。")
    # 不加载到全局os.environ，不展开${变量}，不从其他目录自动寻找.env。
    value = dotenv_values(path, encoding="utf-8-sig", interpolate=False).get("DASHSCOPE_API_KEY")
    if value is None or not value.strip():
        raise SetupError("尚未配置 API Key，请在 .env 文件中填写 DASHSCOPE_API_KEY。")
    key = value.strip()
    if any(character.isspace() for character in key):
        raise SetupError("API Key 中含有空格或换行，请检查 .env 中填写的内容。")
    return key


def api_key_status(project: Project) -> dict:
    """返回本机API Key的配置状态与提示。"""
    try:
        read_api_key(project)
    except (SetupError, OSError, UnicodeError) as exc:
        message = str(exc) if isinstance(exc, SetupError) else "无法读取 .env 文件，请检查文件权限，并使用 UTF-8 编码保存。"
        return {"mode": "api_key", "configured": False, "verified_online": False, "message": message}
    return {"mode": "api_key", "configured": True, "verified_online": False,
            "message": "已检测到 API Key，尚未验证可用性。"}


def bailian_environment(project: Project, auth_mode: str) -> dict[str, str]:
    """构造BL环境，按鉴权方式配置项目API Key。"""
    env = child_environment(project)
    if auth_mode == "api_key":
        env["DASHSCOPE_API_KEY"] = read_api_key(project)
    elif auth_mode != "console":
        raise SetupError("未知鉴权方式。")
    return env
