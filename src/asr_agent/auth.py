"""API Key只从项目.env读取；预检查不发网络请求，也不返回密钥。"""

from .environment import Project, SetupError, child_environment


def read_api_key(project: Project) -> str:
    from dotenv import dotenv_values

    path = project.path(".env")
    if not path.is_file():
        raise SetupError("请先将.env.example复制为.env，并填写DASHSCOPE_API_KEY。")
    # 不加载到全局os.environ，不展开${变量}，不从其他目录自动寻找.env。
    value = dotenv_values(path, encoding="utf-8-sig", interpolate=False).get("DASHSCOPE_API_KEY")
    if value is None or not value.strip():
        raise SetupError(".env中的DASHSCOPE_API_KEY尚未填写。")
    key = value.strip()
    if any(character.isspace() for character in key):
        raise SetupError("DASHSCOPE_API_KEY中不能包含空格或换行。")
    return key


def api_key_status(project: Project) -> dict:
    try:
        read_api_key(project)
    except (SetupError, OSError, UnicodeError) as exc:
        message = str(exc) if isinstance(exc, SetupError) else "无法读取项目.env，请检查文件与编码。"
        return {"mode": "api_key", "configured": False, "verified_online": False, "message": message}
    return {"mode": "api_key", "configured": True, "verified_online": False,
            "message": "已读取本地配置；密钥有效性和模型权限由BL正式调用时校验。"}


def bailian_environment(project: Project, auth_mode: str) -> dict[str, str]:
    env = child_environment(project)
    if auth_mode == "api_key":
        env["DASHSCOPE_API_KEY"] = read_api_key(project)
    elif auth_mode != "console":
        raise SetupError("未知鉴权方式。")
    return env
