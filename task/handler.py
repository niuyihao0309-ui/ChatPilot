# itwwy/task/handler.py

from domain.messages import BotMessage
from domain.state import DialogueState
from task.action.runner import ActionRunner
from task.command.models import Command
from task.flow.executor import FlowExecutor
from task.flow.flows import FlowsList
from task.command.processor import CommandProcessor

class TaskHandler:

    def __init__(
            self,
            flows: FlowsList,
            command_processor: CommandProcessor,
            flow_executor: FlowExecutor,
            action_runner: ActionRunner
    ):
        self.command_processor = command_processor
        self.flows = flows
        self.flow_executor = flow_executor
        self.action_runner = action_runner

    async def handle(self, commands: list[Command], state: DialogueState) -> list[BotMessage]:
        # 阶段1:把命令应用到 state
        self.command_processor.run(commands, state, self.flows)

        # 阶段2:推进流程,生成回复(下一节)
        messages: list[BotMessage] = await self.flow_executor.run_task(
            state, self.flows, self.action_runner
        )
        return messages

        return [BotMessage(text="任务已经处理")]