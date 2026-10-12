# itwwy/api/dependencies.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge.handler import KnowledgeHandler
from knowledge.intents import KNOWLEDGE_INTENTS
from knowledge.providers import ProductAPIProvider, OrderAPIProvider, FAQProvider, RAGProvider
from knowledge.registry import KnowledgeProviderRegistry
from knowledge.responder import KnowledgeResponder
from service.dialogue_service import DialogueService
from repository.dialogue_state_repository import DialogueStateRepository
from engine.dialogue_engine import DialogueEngine
from infrastructure import database
from plan.turn_planner import TurnPlanner
from task.flow.executor import FlowExecutor
from task.flow.loader import FlowLoader
from pathlib import Path
from task.handler import TaskHandler
from task.command.processor import CommandProcessor
from task.action.builder import build_action_runner
from clarify.responder import ClarifyResponder
from plan.turn_validator import TurnPlanValidator
from chitchat.handler import ChitChatHandler       # 导入闲聊处理器
from chitchat.responder import ChitChatResponder   # 导入闲聊响应器


async def get_session():
    """
    实际流程：
        进入 async with → 打开 session
        yield session → 把 session 交给repository函数使用
        路由函数执行完毕 → 回到 yield 之后
        退出 async with → 自动关闭 session ✅
    :return:
    """
    async with database.async_session() as session:  # 异步方式获取session  获取session要网络传输（耗时的）
        yield session


async def get_dialogue_state_repository(session: AsyncSession = Depends(get_session)):
    """
    创建 DialogueStateRepository 实例

    依赖链执行顺序：
       1. get_session() 打开 session 并 yield
       2. 这里拿到 session，创建 Repository
       3. Repository 被Service使用，Service被路由函数使用
       4. 路由函数返回后，get_session() 继续执行，自动关闭 session
    :param session:
    :return:
    """
    return DialogueStateRepository(session=session)
    # 3. 函数返回后，FastAPI 继续执行 get_session() y


# async def get_engine():
#     return DialogueEngine(get_dialogue_engine)


async def get_dialogue_engine():
    base = Path(__file__).resolve().parents[2]
    flow_list = FlowLoader().load_many([
        base / "flow_config" / "user_flows.yml",
        base / "flow_config" / "system_flows.yml",
    ])

    return DialogueEngine(
        turn_planner=TurnPlanner(),
        task_handler=TaskHandler(
            flows=flow_list,
            command_processor=CommandProcessor(),
            action_runner=build_action_runner(),
            flow_executor=FlowExecutor()
        ),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=KNOWLEDGE_INTENTS,
            knowledge_responder=KnowledgeResponder(),
            provider_registry=KnowledgeProviderRegistry([ProductAPIProvider(),OrderAPIProvider(),FAQProvider(),RAGProvider(),]),
        ),
        clarify_responder=ClarifyResponder(),
        turn_plan_validator=TurnPlanValidator(),
        chitchat_handler=ChitChatHandler(ChitChatResponder())
    )

async def get_dialogue_service(
        dialogue_state_repository: DialogueStateRepository = Depends(get_dialogue_state_repository),
        dialogue_engine: DialogueEngine = Depends(get_dialogue_engine),
) -> DialogueService:
    return DialogueService(
        dialogue_state_repository=dialogue_state_repository,
        dialogue_engine=dialogue_engine,
    )













