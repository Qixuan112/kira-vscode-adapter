from __future__ import annotations

import asyncio
import os
import json
from typing import Optional, Union, Any

from core.logging_manager import get_logger
from core.adapter.adapter_utils import IMAdapter
from core.chat import KiraMessageEvent, KiraIMMessage, MessageChain, KiraIMSentResult
from core.chat.message_elements import Text, Image

from .protocol import VSCodeProtocol, VSMessage, MessageType
from .handlers import EventHandlers
from .tools import get_tool_definitions

logger = get_logger("vscode_adapter", "cyan")


class VSCodeAdapter(IMAdapter):
    """VSCode Adapter
    通过 WebSocket 与 VS Code Extension 通信，
    作为 KiraAI 在 IDE 中的"眼睛"和"手"
    """

    def __init__(self, info, loop: asyncio.AbstractEventLoop, event_bus: asyncio.Queue, llm_api):
        super().__init__(info, loop, event_bus, llm_api)

        self.host: str = self.config.get("host", "127.0.0.1")
        self.port: int = self.config.get("port", 9527)
        self.auto_register_tools: bool = self.config.get("auto_register_tools", True)
        self.workspace_path: str = self.config.get("workspace_path", "")

        self.message_types = ["text"]

        # WebSocket 协议处理器
        self.protocol = VSCodeProtocol()
        self.handlers = EventHandlers(self)

        # 状态
        self._ws = None
        self._running = False
        self._server_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # 缓存
        self.file_cache: dict = {}
        self.current_diagnostics: list = []
        self.last_liveshare_event: Optional[dict] = None
        self.last_terminal_output: str = ""
        self.workspace_info: dict = {}
        self._pending_actions: dict = {}

        # 注册消息处理器
        self._register_handlers()

    def _register_handlers(self):
        """注册 Extension 消息处理器"""
        self.protocol.on(MessageType.CHAT_REQUEST, self.handlers.handle_chat_request)
        self.protocol.on(MessageType.DIAGNOSTICS_UPDATE, self.handlers.handle_diagnostics_update)
        self.protocol.on(MessageType.LIVESHARE_EVENT, self.handlers.handle_liveshare_event)
        self.protocol.on(MessageType.FILE_CONTENT, self.handlers.handle_file_content)
        self.protocol.on(MessageType.TERMINAL_OUTPUT, self.handlers.handle_terminal_output)
        self.protocol.on(MessageType.WORKSPACE_INFO, self.handlers.handle_workspace_info)

    async def start(self):
        """启动 VSCodeAdapter WebSocket 服务"""
        try:
            # 注册 VS Code Tools 到 LLM
            if self.auto_register_tools:
                await self._register_tools()

            # 启动 WebSocket 服务
            self._shutdown_event.clear()
            self._server_task = asyncio.create_task(
                self.protocol.start_server(self.host, self.port)
            )
            self._running = True
            logger.info(f"VSCodeAdapter started at ws://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start VSCodeAdapter: {e}")
            raise

    async def _register_tools(self):
        """向 LLMClient 注册 VS Code 相关 Tools"""
        tool_defs = get_tool_definitions()

        for tool_def in tool_defs:
            name = tool_def["name"]
            description = tool_def["description"]
            parameters = tool_def["parameters"]

            self.llm_api.register_tool(
                name=name,
                description=description,
                parameters=parameters,
                func=lambda event, tool_name=name, **kwargs: self._execute_tool(tool_name, event, **kwargs),
            )

            logger.info(f"Registered VS Code tool: {name}")

    async def _execute_tool(self, tool_name: str, event, **kwargs) -> dict:
        """执行 VS Code Tool
        通过 WebSocket 将 tool 调用转发到 Extension 执行
        """
        if not self.protocol._ws:
            return {"error": "VSCode Extension not connected"}

        logger.info(f"Executing tool: {tool_name} with args: {kwargs}")

        try:
            # 如果配置了 workspace_path，注入到工具参数中
            if self.workspace_path:
                kwargs.setdefault("workspace_path", self.workspace_path)
            # 映射 tool 名称到消息类型
            type_map = {
                "vscode_read_file": MessageType.FILE_CONTENT,
                "vscode_edit_file": MessageType.EDIT_FILE,
                "vscode_create_file": MessageType.CREATE_FILE,
                "vscode_open_file": MessageType.OPEN_FILE,
                "vscode_run_terminal": MessageType.RUN_TERMINAL,
                "vscode_get_diagnostics": MessageType.DIAGNOSTICS,
                "vscode_search_files": "search_files",
                "vscode_grep_search": "grep_search",
                "vscode_get_workspace": "get_workspace",
                "vscode_git_commit": "git_commit",
                "vscode_git_diff": "git_diff",
                "vscode_show_message": MessageType.SHOW_MESSAGE,
            }

            msg_type = type_map.get(tool_name)
            if not msg_type:
                return {"error": f"Unknown tool: {tool_name}"}

            # 发送请求到 Extension 并等待结果
            result = await self.protocol.send_request(
                self.protocol._ws,
                msg_type,
                kwargs,
                timeout=60.0,
            )

            return result or {"success": True, "message": f"Tool {tool_name} executed"}

        except TimeoutError:
            logger.error(f"Tool {tool_name} timed out")
            return {"error": f"Tool {tool_name} execution timed out"}
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": f"Tool {tool_name} failed: {e}"}

    async def stop(self):
        """停止 VSCodeAdapter"""
        self._shutdown_event.set()
        self._running = False

        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass

        await self.protocol.stop()
        logger.info("VSCodeAdapter stopped")

    def get_client(self):
        """返回 WebSocket 连接（如果有）"""
        return self.protocol._ws

    async def send_group_message(
        self, group_id: Union[int, str], send_message_obj: MessageChain
    ) -> Optional[KiraIMSentResult]:
        """向 VS Code Extension 发送消息（在聊天面板中显示）

        将 KiraAI 的回复通过 WebSocket 发送到 VS Code Extension
        """
        if not self.protocol._ws:
            logger.warning("Cannot send message: Extension not connected")
            return None

        # 构建文本内容
        text_parts = []
        for element in send_message_obj.__root__:
            if isinstance(element, Text):
                text_parts.append(element.text)
            elif isinstance(element, Image):
                text_parts.append("[图片]")

        content = "\n".join(text_parts)

        # 发送 chat_response 到 Extension
        await self.protocol.send_message(
            self.protocol._ws,
            MessageType.CHAT_RESPONSE,
            {
                "type": "markdown",
                "chunks": [
                    {
                        "type": "markdown",
                        "content": content,
                    }
                ],
            },
        )

        import time
        return KiraIMSentResult(
            message_id=f"vscode_{int(time.time())}",
        )

    async def send_direct_message(
        self, user_id: Union[int, str], send_message_obj: MessageChain
    ) -> Optional[KiraIMSentResult]:
        """向 VS Code Extension 发送私聊消息（与群发相同，都显示在聊天面板）"""
        return await self.send_group_message(user_id, send_message_obj)

    async def send_action(self, action_type: str, payload: dict):
        """向 Extension 发送操作指令"""
        if not self.protocol._ws:
            logger.warning("Cannot send action: Extension not connected")
            return

        await self.protocol.send_message(
            self.protocol._ws,
            action_type,
            payload,
        )
