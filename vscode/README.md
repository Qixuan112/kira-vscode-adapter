# VSCodeAdapter

KiraAI 的 VS Code IDE 集成适配器。

## 工作原理

VSCodeAdapter 作为 WebSocket 服务端运行，与 VS Code Extension (`kira-vscode/`) 通信：

1. **Extension 侧（TypeScript）**：提供聊天面板 UI、编辑器操作、终端执行、诊断收集
2. **Adapter 侧（Python）**：处理聊天请求、管理 Tools、路由消息到 KiraAI Agent

## 配置

在 `data/config/system_config.json` 的 `adapters` 中添加：

```json
{
    "vscode": {
        "enabled": true,
        "name": "VS Code",
        "platform": "vscode",
        "config": {
            "host": "127.0.0.1",
            "port": 9527,
            "auto_register_tools": true
        }
    }
}
```

## 启动方式

### 方式一：自动启动（推荐）

VS Code Extension 会自动启动 KiraAI 后端并建立连接。

### 方式二：手动启动

```bash
cd KiraAI
python main.py --adapter vscode
```

## 协议

通信使用 WebSocket + MCP 风格消息，详见设计文档 `docs/vscode_extension_design.md`。
