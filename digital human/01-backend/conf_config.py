# itwwy/conf/config.py
# 说明：这是「已加数字人字段的完整版 config.py」。合并方式见 01-backend/01-后端改动说明.md 第 1 节。

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):

    # LLM
    llm_api_key: str
    llm_model: str
    llm_base_url: str

    # 数据库
    database_url: str

    # 商城 API
    commerce_api_base_url: str

    # 服务器
    app_host: str
    app_port: int

    # 数字人（魔珐星云）
    # 凭证只存在 .env，本字段带默认空串：没填时应用仍能正常启动，
    # /api/digital-human/credentials 会返回空值，前端据此提示去填 .env。
    digital_human_app_id: str = ""
    digital_human_app_secret: str = ""
    digital_human_gateway_server: str = "https://nebula-agent.xingyun3d.com/user/v1/ttsa/session"

    # 从.env文件中读取配置信息
    # 如果读取真实环境变量，则不写这句话
    # extra="ignore" 表示忽略.env中有，这里没有的配置项，不会报错
    # env_file_encoding：如果遇到乱码问题则添加这个属性解决
    # 注意这里对象名必须叫model_config ，而且必须定义，否则配置会被回收
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", env_file_encoding="utf-8")

settings = Settings()


if __name__ == '__main__':
    print(settings.llm_base_url)
