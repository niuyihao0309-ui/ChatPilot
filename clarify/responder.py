from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
import json
from domain.messages import BotMessage
from domain.state import DialogueState
from infrastructure.llm import llm          # 全局唯一的 LLM 客户端（init_chat_model 创建）
from plan.models import ClarifyReason       # 澄清原因枚举，如"缺轨道""缺意图"
from prompts.history_builder import HistoryBuilder
from prompts.loader import load_prompt


class ClarifyResponder:

    # ============ 第①步：根据澄清原因，返回一句"打底话术" ============
    # 纯 if-else，不调 LLM、无副作用，方便单测。
    # 注意用 `is` 比较：ClarifyReason 是枚举，枚举成员是单例，`is` 比较最稳妥。
    def build_clarify_message(
            self,
            reason: ClarifyReason,   # 为什么要澄清（上游校验给出的原因）
            state: DialogueState,    # 对话状态（这里只用它的 focused_object）
    ) -> str:

        # 用户一句话里同时想办多件事 → 让用户二选一
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return "你这次同时提到了多个方向。我们先处理一个，你想先办业务还是先咨询信息呢？"

        # 需要聚焦对象（订单/商品卡片）但用户没发 → 让用户先发对象
        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先发送你想咨询的对象，我再继续帮你看。"

        # 走了知识咨询轨道但意图不明 → 问清想咨询哪类信息
        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return "你是想了解商品信息、订单信息，还是售后配送规则呢？"

        # 分不清是"办业务"还是"咨询信息" → 问轨道
        if reason is ClarifyReason.MISSING_TRACK:
            return "你是想先处理业务问题，还是先咨询信息呢？"

        # 确定办业务，但不知道具体办什么 → 给例子引导
        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return "你这次是想办理什么业务呢？比如查订单、查物流，或者申请退款。"

        # 用户点了某个对象（订单/商品），但没说要干嘛 → 按对象类型追问
        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.focused_object
            # 聚焦的是订单 → 给出订单相关的三种意图选项
            if focused_object is not None and focused_object.type == "order":
                return "我已经收到这个订单了。你想查订单状态、查物流，还是申请退款呢？"
            # 聚焦的是商品 → 给出商品相关的三种意图选项
            if focused_object is not None and focused_object.type == "product":
                return "我已经收到这个商品了。你想了解它的商品信息、发货情况，还是售后相关问题呢？"
            # 聚焦对象为 None 或类型不认识（如 coupon）→ 落到下面的兜底

        # 兜底：以上都不匹配时（如 INVALID_TASK_COMMANDS 等未单独处理的 reason）
        return "我还需要再确认一下你的意思，你可以换个更具体的说法告诉我。"

    # ============ 第②步：把打底话术 + 上下文交给 LLM，润色成自然口语 ============
    # 为什么要润色？固定话术太生硬，让 LLM 结合历史对话改写得像真人客服，
    # 但模板里明确要求"不许扩写、不许改变澄清意图"，所以语义是受控的。
    async def respond(
            self,
            state: DialogueState,
            reason: ClarifyReason,
    ) -> list[BotMessage]:

        # --- 1. 准备素材：把对话状态里的东西全部序列化成"字符串" ---

        # 本轮用户消息（pending_turn 在 engine.begin_turn 时已挂好，不会为 None）
        message = state.pending_turn.user_message

        # ① 基础话术：先拿到那句固定文案
        clarify_message = self.build_clarify_message(reason=reason, state=state)

        # 把用户消息渲染成文本，如 "帮我看看"（对象消息会渲染成 [label=订单对象, ...]）
        user_message = HistoryBuilder._render_user_message(message)

        # 把当前会话的历史轮次渲染成多行文本：
        # "USER: 在吗\nBOT: 在的，请讲"
        history = HistoryBuilder.build(state.current_session().turns)

        # 聚焦对象 → JSON 字符串（如 '{"id": "o1", "type": "order", ...}'）
        # 注意防御：没有聚焦对象时给空串，否则对 None 调方法会崩；
        # 模板里有 {% if focused_object %}，空串会自动跳过这一段。
        #focused_object = json.dumps(state.focused_object.to_dict())
        focused_object = json.dumps(state.focused_object.model_dump()) if state.focused_object else ""

        # --- 2. 组装 LangChain 链：模板 → LLM → 取纯文本 ---

        # 加载 prompts/jinja2/clarify_respond.jinja2 模板原文
        prompt_text = load_prompt("clarify_respond")

        # 用 jinja2 语法解析模板（模板里用了 {% if %} 条件块，默认的 f-string 格式不支持）
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")

        # 管道语法：PromptTemplate 渲染出的 PromptValue 喂给 llm，
        # llm 输出的 AIMessage 再被 StrOutputParser 抽出 .content 纯文本。
        # 即：dict → 渲染好的提示词 → AIMessage → str
        chain = prompt | llm | StrOutputParser()

        # 异步调用整条链。dict 的 key 必须和模板里的 {{ }} 变量名一一对应。
        # reason.value：ClarifyReason 是 (str, Enum)，.value 取出枚举的字符串值，
        # 如 OBJECT_REQUIRES_INTENT → "object_requires_intent"
        rewritten = await chain.ainvoke(  # ② LLM 润色
            {
                "reason": reason.value,                # 澄清原因
                "clarify_message": clarify_message,    # 打底话术
                "focused_object": focused_object,      # 聚焦对象 JSON（可能为空串）
                "history": history,                    # 历史对话文本
                "user_message": user_message,          # 用户本轮说的话
            }
        )

        # 统一包装成 BotMessage 列表返回（列表是因为一轮可能回多条消息）
        return [BotMessage(text=rewritten)]

if __name__ == '__main__':
    from domain.messages import FocusedObject
    import asyncio

    responder = ClarifyResponder()

    # 状态1：空状态（无聚焦对象）
    state = DialogueState(sender_id="user_001")
    # 状态2：已聚焦订单对象
    state_with_order = DialogueState(
        sender_id="user_001",
        focused_object=FocusedObject(id="ORDER_10001", type="order", title="订单10001"),
    )
    # 状态3：已聚焦商品对象
    state_with_product = DialogueState(
        sender_id="user_001",
        focused_object=FocusedObject(id="SKU_20001", type="product", title="纯棉T恤"),
    )

    def run_case(name: str, reason: ClarifyReason, st: DialogueState = state):
        msg = responder.build_clarify_message(reason, st)
        print(f"[{name}] {msg}")

    # 1. 多轨道 → 让用户选办业务还是咨询
    # run_case(" 1.多轨道        ", ClarifyReason.MULTIPLE_TRACKS)
    # # 2. 缺聚焦对象 → 让用户先发对象
    # run_case(" 2.缺聚焦对象     ", ClarifyReason.MISSING_FOCUSED_OBJECT)
    # # 3. 知识轨道缺意图 → 问咨询哪类信息
    # run_case(" 3.缺知识意图     ", ClarifyReason.MISSING_KNOWLEDGE_INTENT)
    # # 4. 缺轨道 → 问办业务还是咨询
    # run_case(" 4.缺轨道        ", ClarifyReason.MISSING_TRACK)
    # # 5. task 轨道缺 commands → 问办什么业务
    # run_case(" 5.缺任务指令     ", ClarifyReason.MISSING_TASK_COMMANDS)
    # # 6. 有订单对象缺意图 → 订单话术
    # run_case(" 6.订单缺意图     ", ClarifyReason.OBJECT_REQUIRES_INTENT, st=state_with_order)
    # # 7. 有商品对象缺意图 → 商品话术
    # run_case(" 7.商品缺意图     ", ClarifyReason.OBJECT_REQUIRES_INTENT, st=state_with_product)
    # # 8. 对象缺意图但没有聚焦对象 → 兜底话术
    # run_case(" 8.无对象兜底     ", ClarifyReason.OBJECT_REQUIRES_INTENT)
    # # 9. 未单独处理的 reason（如流程不存在）→ 兜底话术
    # run_case(" 9.未知流程兜底   ", ClarifyReason.UNKNOWN_TASK_FLOW)

    # 10.（可选）端到端验证 respond，会真实调用 LLM，需要 .env 配置
    from domain.messages import UserMessage, MessageType
    from domain.state import Turn
    state.pending_turn = Turn(
        turn_id="t1",
        user_message=UserMessage(sender_id="user_001", message_id="m1",
                                 type=MessageType.TEXT, text="我想问点事"),
        bot_messages=[],
    )
    state.start_session()
    result = asyncio.run(responder.respond(state, ClarifyReason.MULTIPLE_TRACKS))
    print(f"[10.LLM润色     ] {result[0].text}")




