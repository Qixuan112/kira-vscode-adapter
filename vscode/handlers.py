from __future__ import annotations

import json
import os
from typing import Any, Optional

from core.logging_manager import get_logger
from .protocol import VSMessage, MessageType

logger = get_logger("vscode_handlers", "cyan")


class EventHandlers:
    """VS Code 事件处理器
    处理来自 Extension 的各种事件消息
    """

    def __init__(self, adapter):
        self.adapter = adapter
        self._last_diagnostics = []
        self._last_workspace_info = {}

    async def handle_chat_request(self, ws, msg: VSMessage):
        """处理聊天请求消息"""
        import time
        import uuid

        payload = msg.payload
        text = payload.get("text", "")
        context = payload.get("context", {})
        history = payload.get("history", [])
        command = payload.get("command")

        logger.info(f"Chat request received (command={command}): {text[:100]}...")

        # 构造消息事件
        from core.chat import KiraMessageEvent, KiraIMMessage, MessageChain, User, Group
        from core.chat.message_elements import Text

        timestamp = int(time.time())

        # 构建消息链
        elements = [Text(text)]
        chain = MessageChain(elements)

        # 构建 KiraIMMessage
        message = KiraIMMessage(
            message_id=f"vscode_{msg.seq}",
            self_id="kira_vscode",
            chain=chain,
            timestamp=timestamp,
            sender=User(user_id="vscode_user", nickname="VSCode User"),
            group=Group(group_id="vscode", group_name="VS Code"),
            is_mentioned=True,
        )

        # 构建 KiraMessageEvent
        event = KiraMessageEvent(
            adapter=self.adapter.info,
            message_types=self.adapter.message_types,
            message=message,
            timestamp=timestamp,
        )
        event.trigger(force=True)

        # 注入 VS Code 上下文到 message.extra
        message.extra = {
            "vscode_context": context,
            "vscode_history": history,
            "vscode_command": command,
        }

        # 放入事件总线
        self.adapter.publish(event)

    async def handle_diagnostics_update(self, ws, msg: VSMessage):
        """处理诊断更新消息"""
        diagnostics = msg.payload.get("diagnostics", [])
        self._last_diagnostics = diagnostics
        logger.debug(f"Diagnostics updated: {len(diagnostics)} issues")

        # 将诊断信息存储到 adapter 供 LLM 使用
        self.adapter.current_diagnostics = diagnostics

    async def handle_liveshare_event(self, ws, msg: VSMessage):
        """处理 Live Share 事件"""
        event_type = msg.payload.get("type", "")
        logger.info(f"Live Share event: {event_type}")

        # 将最新的事件保存到 adapter
        self.adapter.last_liveshare_event = msg.payload

    async def handle_file_content(self, ws, msg: VSMessage):
        """处理文件内容快照"""
        path = msg.payload.get("path", "")
        content = msg.payload.get("content", "")
        language = msg.payload.get("language", "")

        # 更新 adapter 中的文件缓存
        if path:
            self.adapter.file_cache[path] = {
                "content": content,
                "language": language,
                "timestamp": msg.timestamp,
            }

    async def handle_terminal_output(self, ws, msg: VSMessage):
        """处理终端输出"""
        output = msg.payload.get("output", "")
        if output:
            self.adapter.last_terminal_output = output

    async def handle_workspace_info(self, ws, msg: VSMessage):
        """处理工作区信息"""
        info = msg.payload
        # 如果配置了 workspace_path，将其注入到工作区信息中
        if self.adapter.workspace_path:
            info["workspace_path"] = self.adapter.workspace_path
            # 将指定的工作区路径添加到 folders 列表首位（如果不存在）
            folders = info.get("folders", [])
            if self.adapter.workspace_path not in folders:
                folders.insert(0, self.adapter.workspace_path)
                info["folders"] = folders
        self._last_workspace_info = info
        self.adapter.workspace_info = info

    def get_last_diagnostics(self):
        """获取最近的诊断信息"""
        return self._last_diagnostics

    def get_last_workspace_info(self):
        """获取最近的工作区信息"""
        return self._last_workspace_info
