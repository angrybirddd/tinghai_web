# 🌊 Tinghai Web (听海)
> **连接云端交互与本地算力的私有化 AI 编排中枢**
> *Your Private AI Orchestrator Bridging Web Interaction & Local Execution*

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/backend-Flask-black.svg)](https://flask.palletsprojects.com/)
[![MCP Ready](https://img.shields.io/badge/MCP-Ready-orange.svg)](https://modelcontextprotocol.io/)

---

## 🌟 为什么选择 Tinghai (听海)?

在 AI 时代，我们常常面临两难：云端模型强大但难以触及本地数据，本地模型安全但交互体验不佳。

**Tinghai (听海)** 并不是另一个简单的 Chatbot UI，而是一套优雅的 **C/S (Client-Server) 架构 AI 协作系统**。它将 **Web 交互界面** 与 **AI 执行端** 完美解耦，让您可以：

*   💻 **在任何地方交互**：通过优雅的 Web 界面（支持移动端）随时随地发送指令。
*   🔒 **在本地执行**：AI 逻辑运行在您可控的本地机器（Client）上，直接操作本地文件、数据库，数据无需上传云端。
*   🧩 **无限能力扩展**：原生支持 **MCP (Model Context Protocol)**，轻松接入数千种现有工具。

如果你正在寻找一个**既能保护隐私，又能灵活定制角色，还能让 AI 真正帮你在本地干活**的解决方案，那么 **Tinghai** 就是为你打造的！

---

## ✨ 核心亮点 (Key Features)

### 1. 🛡️ 隐私至上与安全隔离
Server 端只负责转发消息和展示界面，真正的 AI 推理、文件读写、敏感操作全部在您的 **Client 端** 完成。即便 Server 部署在公网，您的核心数据依然安全地留在本地。

### 2. 🎭 灵活的角色编排 (Role Play)
不再是单调的一问一答。在 Tinghai 中，您可以创建多个 **"虚拟角色"** 或 **"群组"**，并为它们设定独特的 Prompt（人设/指令）。
*   想要一个 Python 专家？创建一个 `@PythonExpert`。
*   需要一个文案写手？创建一个 `@CopyWriter`。
*   **@提及** 即可唤醒对应角色，就像在 Slack 或钉钉里 @同事 一样自然！

### 3. 🔌 MCP 协议原生支持
Tinghai Client 集成了最新的 **Model Context Protocol (MCP)**。这意味着您不需要重复造轮子，可以直接使用社区丰富的 MCP Server 资源（如 GitHub, Google Drive, Postgres 等），让您的 AI 瞬间拥有三头六臂。

### 4. 📂 强大的本地文件操作
通过内置的安全沙箱工具，AI 可以直接读取、分析、甚至生成本地文件（Excel, Text, Code）。不再需要复制粘贴，直接告诉它：“帮我分析一下 `data.xlsx` 并生成一份总结报告”。

---

## 🚀 快速开始 (Quick Start)

只需要几分钟，构建属于你的 AI 中枢。

### 第一步：启动服务端 (Web Interface)

Server 是大脑的 "嘴巴" 和 "耳朵"。

```bash
cd tinghai_web

# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库并启动
python server.py
```
> 🌐 访问 `http://localhost:5000`，你将看到漂亮的聊天界面。

### 第二步：启动客户端 (AI Worker)

Client 是大脑的 "手" 和 "脑"。它可以运行在同一台机器，也可以是家里的高性能 PC 或公司内网服务器。

```bash
cd tinghai_web/client

# 1. 配置环境（建议使用 .env 或环境变量配置 API Key）
# export DASHSCOPE_API_KEY="sk-..." 

# 2. 启动客户端
python client.py
```
> 首次运行客户端时，会提示您注册/登录账号。请确保与 Web 端使用相同的账号体系。

---

## 📖 使用指南 (User Guide)

1.  **登录系统**：打开 Web 界面，输入您在 Client 端注册的账号密码。
2.  **创建角色**：点击左侧边栏的 `+` 号，添加一个新的角色（例如：`@数据分析师`），并写下它的 Prompt（例如："你是一个资深数据分析师，擅长用 Python 处理 Excel..."）。
3.  **开始对话**：
    *   普通聊天：直接输入内容。
    *   召唤专家：输入 `@数据分析师 请帮我看看这个月的数据`。
4.  **享受魔法**：Client 端会接收任务，调用 AI 模型和本地工具，并将结果实时流式传输回 Web 界面。

---

## 🏗️ 架构概览

```mermaid
graph LR
    User((🤵 User)) -->|Browser| Web[🖥️ Web Server (Flask)]
    Web <-->|Task Queue| DB[(🗄️ SQLite)]
    
    subgraph "Your Private Zone (Local/Intranet)"
        Client[🤖 AI Client] 
        Client -->|Long Poll| Web
        Client -->|Execute| Tools[🛠️ Local Tools / MCP]
        Client -->|Inference| LLM[🧠 Qwen/OpenAI]
    end
```

---

## 🤝 参与贡献 (Contributing)

Tinghai 还是一个年轻的项目，我非常欢迎各种形式的贡献！
无论是 **提交 Bug**、**提出新功能建议 (PR)**，还是仅仅是 **完善文档**，都是对我最大的支持。

如果你喜欢这个项目，请不吝点亮右上角的 **⭐️ Star**，这会让我更有动力持续更新！💖

---

## 📄 开源协议 (License)

本项目基于 [MIT License](LICENSE) 开源。这意味着您可以自由地使用、修改和分发它。

---

<p align="center">Made with ❤️ by Tinghai Engineer</p>

