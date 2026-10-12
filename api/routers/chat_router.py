import uuid
from fastapi import APIRouter, Depends

from api.routers.dependencies import get_dialogue_service
from api.schemas import ChatResponse, ChatBotMessage, ChatObject, ChatRequset, HistoryResponse, HistoryMessage
from domain.messages import ProcessResult, UserMessage, MessageType, FocusedObject
from service.dialogue_service import DialogueService

router = APIRouter()


# 定义接口

@router.post("/api/chat")
async def chat_endpoint(
        chat_requset: ChatRequset,
        dialogue_service: DialogueService = Depends(get_dialogue_service),
) -> ChatResponse:
    # 1. 处理输入接口模型
    user_message = _build_user_message(chat_requset)
    # 2. 业务处理
    process_result:ProcessResult = await dialogue_service.process_message(user_message)
    # 3. 处理输出接口模型
    return _build_chat_response(process_result)

def _build_user_message(chat_requset: ChatRequset) -> UserMessage:
    """
    将请求数据模型转换为领域数据模型 供业务使用
    :param chat_requset:
    :return:
    """
    return UserMessage(
        sender_id=chat_requset.sender_id,
        message_id=chat_requset.message_id if chat_requset.message_id else str(uuid.uuid4()),
        type=MessageType.TEXT if chat_requset.text else MessageType.OBJECT,
        text=chat_requset.text,
        object=FocusedObject(
            id=chat_requset.object.id,
            type=chat_requset.object.type,
            title=chat_requset.object.title,
            attributes=chat_requset.object.attachments,
        ) if chat_requset.object else None,
    )


def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[
            ChatBotMessage(
                text=bot_msg.text,
                object=ChatObject(
                    type=bot_msg.object.type,
                    id=bot_msg.object.id,
                    title=bot_msg.object.title,
                    attachments=bot_msg.object.attributes,
                ) if bot_msg.object else None,
            )
            for bot_msg in process_result.messages
        ]
    )

# @router.get('/api/chat/history')
# async def history(sender_id:str) -> HistoryResponse:
#     return HistoryResponse(
#         sender_id=sender_id,
#         messages=[
#             HistoryMessage(role='user',text='你好'),
#             HistoryMessage(role='bot', text='我不好')
#         ]
#     )



@router.get("/api/chat/history")
async def history(sender_id: str, service: DialogueService = Depends(get_dialogue_service)) -> HistoryResponse:
    chat_message_response: list[HistoryMessage] = await service.load_chat_history(sender_id)
    return HistoryResponse(sender_id=sender_id, messages=chat_message_response)






