from __future__ import annotations

from typing import Any, Optional
from core.logging_manager import get_logger

logger = get_logger("vscode_tools", "cyan")

# VS Code Tools 的模式定义
# 这些 Tools 通过 WebSocket 发送到 Extension 执行

TOOL_DEFINITIONS = [
    {
        "name": "vscode_read_file",
        "description": "读取指定文件的内容",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "start": {"type": "integer", "description": "起始行（可选，1-indexed）"},
                "end": {"type": "integer", "description": "结束行（可选）"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "vscode_edit_file",
        "description": "编辑文件（替换文本）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "old_str": {"type": "string", "description": "被替换的旧文本（必须是精确匹配）"},
                "new_str": {"type": "string", "description": "替换后的新文本"},
                "force": {"type": "boolean", "description": "如果旧文本未找到，是否强制替换整个文件"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
            "required": ["path", "old_str", "new_str"],
        },
    },
    {
        "name": "vscode_create_file",
        "description": "创建新文件",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "文件内容"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "vscode_open_file",
        "description": "在编辑器中打开文件",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "vscode_run_terminal",
        "description": "在 VS Code 终端中执行命令",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"},
                "cwd": {"type": "string", "description": "工作目录（可选）"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "vscode_get_diagnostics",
        "description": "获取当前工作区的诊断错误信息",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "可选，限定文件路径"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
        },
    },
    {
        "name": "vscode_search_files",
        "description": "在工作区中搜索文件",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "文件搜索模式（glob 语法，如 **/*.ts）"},
                "max_results": {"type": "integer", "description": "最大返回数量（可选）"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "vscode_grep_search",
        "description": "在工作区中全文搜索代码",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词或正则表达式"},
                "path": {"type": "string", "description": "限定搜索的文件路径（可选）"},
                "is_regexp": {"type": "boolean", "description": "是否为正则搜索（可选）"},
                "max_results": {"type": "integer", "description": "最大返回数量（可选）"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "vscode_get_workspace",
        "description": "获取当前工作区的项目结构信息",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
        },
    },
    {
        "name": "vscode_git_commit",
        "description": "创建 Git 提交",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "提交信息"},
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要提交的文件列表（可选，默认提交所有变更）",
                },
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "vscode_git_diff",
        "description": "查看文件的 Git diff",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径（可选，查看所有变更）"},
                "workspace_path": {"type": "string", "description": "工作区根目录路径（可选，覆盖默认工作区）"},
            },
        },
    },
    {
        "name": "vscode_show_message",
        "description": "在 VS Code 中显示通知消息",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["info", "warning", "error"],
                    "description": "消息类型",
                },
                "message": {"type": "string", "description": "消息内容"},
            },
            "required": ["type", "message"],
        },
    },
]


def get_tool_definitions():
    """获取 VS Code 相关 Tool 定义列表"""
    return TOOL_DEFINITIONS
