from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Dict
from enum import Enum

from core.logging_manager import get_logger

logger = get_logger("vscode_protocol", "cyan")


class MessageType(str, Enum):
    """消息类型枚举"""
    # Extension → KiraAI
    CHAT_REQUEST = "chat_request"
    FILE_CONTENT = "file_content"
    DIAGNOSTICS = "diagnostics"
    DIAGNOSTICS_UPDATE = "diagnostics_update"
    SELECTION = "selection"
    WORKSPACE_INFO = "workspace_info"
    LIVESHARE_EVENT = "liveshare_event"
    TERMINAL_OUTPUT = "terminal_output"

    # KiraAI → Extension
    CHAT_RESPONSE = "chat_response"
    EDIT_FILE = "edit_file"
    CREATE_FILE = "create_file"
    OPEN_FILE = "open_file"
    SHOW_MESSAGE = "show_message"
    RUN_TERMINAL = "run_terminal"
    APPLY_DIFF = "apply_diff"
    TOOL_RESULT = "tool_result"


@dataclass
class VSMessage:
    """VS Code 通信消息"""
    type: str
    seq: int
    payload: dict
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "seq": self.seq,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> "VSMessage":
        obj = json.loads(data)
        return cls(
            type=obj["type"],
            seq=obj["seq"],
            payload=obj.get("payload", {}),
            timestamp=obj.get("timestamp", time.time()),
        )


class VSCodeProtocol:
    """WebSocket 协议处理器
    管理 WebSocket 连接、消息收发、请求-响应匹配
    """

    def __init__(self):
        self._seq: int = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._handlers: Dict[str, list[Callable]] = {}
        self._ws = None
        self._running = False
        self._server = None

    def on(self, msg_type: str, handler: Callable):
        """注册消息处理器"""
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)

    def off(self, msg_type: str, handler: Callable):
        """移除消息处理器"""
        if msg_type in self._handlers:
            self._handlers[msg_type].remove(handler)

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def send_message(self, ws, msg_type: str, payload: dict) -> int:
        """发送消息（不等待响应）"""
        seq = self._next_seq()
        msg = VSMessage(type=msg_type, seq=seq, payload=payload)
        data = msg.to_json()
        await ws.send(data)
        logger.debug(f"Sent: {msg_type}({seq})")
        return seq

    async def send_request(self, ws, msg_type: str, payload: dict, timeout: float = 30.0) -> Any:
        """发送请求并等待响应"""
        seq = self._next_seq()
        msg = VSMessage(type=msg_type, seq=seq, payload=payload)
        data = msg.to_json()

        future = asyncio.get_event_loop().create_future()
        self._pending[seq] = future

        await ws.send(data)
        logger.debug(f"Sent request: {msg_type}({seq})")

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(seq, None)
            raise TimeoutError(f"Request {msg_type}({seq}) timed out after {timeout}s")

    async def handle_message(self, ws, raw: str):
        """处理收到的消息"""
        try:
            msg = VSMessage.from_json(raw)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse message: {e}")
            return

        logger.debug(f"Received: {msg.type}({msg.seq})")

        # 检查是否是 pending request 的响应
        if msg.seq in self._pending:
            future = self._pending.pop(msg.seq)
            if not future.done():
                future.set_result(msg.payload)
            return

        # 分发给注册的处理器
        handlers = self._handlers.get(msg.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(ws, msg)
                else:
                    handler(ws, msg)
            except Exception as e:
                logger.error(f"Handler error for {msg.type}: {e}")

    async def start_server(self, host: str = "127.0.0.1", port: int = 9527):
        """启动 WebSocket 服务端"""
        import websockets

        self._running = True

        async def handler(ws):
            logger.info(f"Extension connected: {ws.remote_address}")
            self._ws = ws
            try:
                async for raw in ws:
                    await self.handle_message(ws, raw)
            except websockets.exceptions.ConnectionClosed:
                logger.info("Extension disconnected")
            finally:
                self._ws = None

        self._server = await websockets.serve(handler, host, port)
        logger.info(f"VSCode WebSocket server started at ws://{host}:{port}")

    async def stop(self):
        """停止服务"""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        # 取消所有 pending futures
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
        logger.info("VSCode protocol stopped")
