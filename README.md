# kira-vscode-adapter

轻量级的 VS Code 调试适配器（Debug Adapter）实现，使用 Python 编写，旨在将 kira（或你项目的运行时/调试后端）与 Visual Studio Code 集成。此仓库包含调试适配器的实现、开发与测试辅助脚本，以及示例配置。

> 注意：本文档中部分命令和模块名使用占位符（如 `kira_vscode_adapter`），请根据实际包/模块名替换。

---

## 目录

- [功能](#功能)
- [项目结构](#项目结构)
- [先决条件](#先决条件)
- [快速开始](#快速开始)
  - [从源码安装](#从源码安装)
  - [在开发模式运行](#在开发模式运行)
- [使用示例](#使用示例)
  - [作为独立适配器（stdio）运行](#作为独立适配器stdio运行)
  - [以 TCP 端口运行并连接](#以-tcp-端口运行并连接)
- [在 VS Code 中调试与集成](#在-vs-code-中调试与集成)
- [配置](#配置)
- [开发者指南](#开发者指南)
  - [运行单元测试](#运行单元测试)
  - [代码风格与静态检查](#代码风格与静态检查)
- [贡献](#贡献)
- [常见问题](#常见问题)
- [许可](#许可)
- [联系方式](#联系方式)

---

## 功能

- 实现 VS Code Debug Adapter Protocol (DAP) 的基础通讯与会话管理。
- 支持通过 stdio 或 TCP 与 VS Code（或其他调试客户端）通信。
- 提供适配 kira（或目标运行时）的基础断点、单步、变量、堆栈等调试功能（需根据后端能力扩展）。
- 简明的开发与测试工具，便于在本地迭代适配器逻辑。

---

## 项目结构（示例）

仓库包含（根据实际项目可能略有不同）：

- `kira_vscode_adapter/` — 适配器源码包（核心逻辑）
- `tests/` — 单元测试与集成测试
- `examples/` — 示例配置与演示脚本
- `tools/` — 辅助脚本（启动脚本、生成代码等）
- `pyproject.toml` / `setup.cfg` / `setup.py` — 构建与打包配置
- `README.md` — 本文档

---

## 先决条件

- Python 运行时：3.8+
- 建议创建并使用虚拟环境（venv、virtualenv、pipenv、poetry 等）
- 可选：用于本地调试或交互的 VS Code（带 Debug Adapter 支持）

---

## 快速开始

### 从源码安装

在仓库根目录执行：

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

pip install --upgrade pip
pip install -e .
```

> 安装后，适配器包名（用于运行）通常与目录名一致，例如 `kira_vscode_adapter`。若你的包名不同，请用实际包名替换下面的命令示例。

### 在开发模式运行

以可热重载/调试的方式直接运行适配器（示例）：

```bash
# 以 stdio 模式启动适配器（适配器通过标准输入/输出与客户端通信）
python -m kira_vscode_adapter --stdio

# 或者以端口模式（TCP）运行
python -m kira_vscode_adapter --port 4711
```

命令行参数（示例）
- `--stdio`：使用标准输入/输出（用于 VS Code 的 `adapterExecutableCommand` 或扩展直接启动）
- `--port <PORT>`：启动为 TCP server，等待客户端连接
- `--log <file>`：将通讯与日志写入文件，便于调试

---

## 使用示例

### 作为独立适配器（stdio）运行

适配器以 stdio 运行时，通常由 VS Code 扩展或调试配置直接启动：

```bash
python -m kira_vscode_adapter --stdio
```

VS Code 扩展侧会以子进程方式启动该命令，适配器通过 DAP 与 VS Code 交换 JSON-RPC 消息。

### 以 TCP 端口运行并连接

适配器监听一个端口，等待调试客户端连接：

```bash
python -m kira_vscode_adapter --port 4711
```

在 VS Code launch.json 中使用 `debugServer`（或扩展中相应字段）连接到该端口。

示例（client launch 配置仅作参考，具体取决于扩展如何实现）：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to kira adapter",
      "type": "your-debugger-type",
      "request": "launch",
      "debugServer": 4711,
      "program": "${workspaceFolder}/path/to/target"
    }
  ]
}
```

---

## 在 VS Code 中调试与集成

1. 本地开发时，建议在一个 VS Code window 中打开你的扩展或示例工程。
2. 使用 `pip install -e .` 让本地修改立即可用。
3. 在适配器里添加充足的日志（可通过 `--log` 打开），便于追踪 DAP 消息。
4. 若需要在适配器内部设置断点并调试适配器本身，可以：
   - 在适配器代码中加入 `import debugpy; debugpy.listen(("localhost", 5678)); debugpy.wait_for_client()`（或使用 preferred debug server），
   - 然后通过 VS Code 附加到适配器的调试端口进行逐步调试。

---

## 配置

适配器支持通过环境变量或命令行参数配置行为（示例）：

- KIRA_ADAPTER_LOG_LEVEL — 日志等级（DEBUG, INFO, WARNING, ERROR）
- KIRA_ADAPTER_BACKEND_URL — 后端服务地址（若适配器需要连接远端运行时）
- KIRA_ADAPTER_TIMEOUT — 请求超时时间（秒）

在实际实现中，请将这些键名与代码中使用的一致，并在此处补充完整的配置项说明。

---

## 开发者指南

- 代码风格：遵循 PEP8，推荐使用 `black`、`ruff` 或 `flake8` 做格式与静态检查。
- 依赖管理：在 `pyproject.toml` / `requirements.txt` 中声明依赖。
- 单元测试：推荐使用 `pytest`。

### 运行单元测试

```bash
# 在虚拟环境中
pip install -r requirements-dev.txt
pytest -q
```

### 代码风格与静态检查

```bash
black .
ruff check .
flake8
```

---

## 贡献

欢迎贡献！建议的流程：

1. Fork 本仓库并创建 feature 分支：`git checkout -b feat/your-feature`
2. 提交改动并推送到你的 fork。
3. 发起 Pull Request，描述变更目的与影响。
4. 在 PR 中附上可复现步骤 / 测试说明与截图（如适用）。
5. 维护者会进行代码审查，必要时请求修改。

在贡献前请查看并遵守项目的代码规范、分支策略与测试覆盖要求。

---

## 常见问题（FAQ）

Q: 适配器如何与 kira 后端通信？
A: 根据你的后端能力，适配器可以通过 subprocess（启动本地进程）、TCP/HTTP 接口或自定义 RPC 与后端通信。请在 `kira_vscode_adapter/backend.py`（或相应模块）实现具体连接逻辑。

Q: 我需要支持远程调试吗？
A: 支持。建议实现 TCP 模式并在 VS Code 启动配置中使用 `debugServer` 或在扩展中实现远程连接逻辑。注意网络安全与鉴权。

Q: 如何查看 DAP 消息？
A: 在适配器中打开详细日志（DEBUG），或者在启动时将通讯写入文件（`--log`），日志会包含 DAP 请求/响应与事件。

---

## 许可

本项目采用 MIT 许可（或根据实际选择的许可替换此处）。详见 LICENSE 文件。

---

## 致谢与联系方式

- 作者 / 维护者: Qixuan112
- 仓库: https://github.com/Qixuan112/kira-vscode-adapter

如果你有问题或建议，请在仓库 Issues 中创建 issue，或向作者发起 PR。

---
