import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

load_dotenv(override=True)

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")

_openai_client = AsyncOpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
AGENT_MODEL = OpenAIChatCompletionsModel(model=LLM_MODEL, openai_client=_openai_client)

DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")

MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_COLLECTION: str = os.getenv("MILVUS_COLLECTION", "laptop_knowledge")

MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "customer_service")

BAIDU_MAP_AK: str = os.getenv("BAIDU_MAP_AK", "")

APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
