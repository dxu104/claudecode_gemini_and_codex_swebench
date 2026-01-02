# 前置条件检查清单 (Prerequisites Checklist)

在运行 SWE-bench 之前，请确保完成以下所有前置条件。

## ✅ 1. Python 3.8 或更新版本

### 检查是否已安装
```bash
python3 --version
```

### 如果没有安装或版本太旧

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

**macOS:**
```bash
# 使用 Homebrew
brew install python3
```

**Windows:**
- 从 https://www.python.org/downloads/ 下载并安装

### 验证
```bash
python3 --version  # 应该显示 3.8 或更高版本
```

---

## ✅ 2. 代码模型 CLI 安装并登录

你需要安装以下之一（或全部）：
- **Claude Code CLI** (Anthropic) - 推荐
- **Codex CLI** (OpenAI)
- **Gemini CLI** (Google)

### 选项 A: Claude Code CLI（推荐）

**安装:**
- 访问 https://claude.ai/download
- 下载并安装 Claude Code CLI

**验证安装:**
```bash
claude --version
```

**登录:**
```bash
claude  # 打开 Claude Code 进行登录
```

---

### 选项 B: Codex CLI (OpenAI)

**前置条件: Node.js 18+**
```bash
# 检查 Node.js 是否已安装
node --version  # 需要 18 或更高版本
npm --version
```

**如果没有 Node.js:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nodejs npm

# 或者从官网下载: https://nodejs.org/
```

**安装 Codex CLI:**
```bash
# 全局安装 Codex CLI
npm install -g @openai/codex

# 验证安装
codex --version
```

**登录/配置:**
```bash
# 首次运行会提示登录
codex

# 或者设置 API key (可选)
export OPENAI_API_KEY=your_api_key
```

**注意:** Codex CLI 需要有效的 OpenAI 订阅（ChatGPT Plus、Pro、Business、Edu 或 Enterprise）

---

### 选项 C: Gemini CLI

**安装:**
```bash
# 使用 snap (Ubuntu)
sudo snap install gemini

# 或者从 Google 官网安装
```

**验证:**
```bash
gemini --version
```

### 检查是否已安装
```bash
claude --version
```

### 如果没有安装

**所有平台:**
1. 访问 https://claude.ai/download
2. 下载并安装 Claude Code CLI
3. 确保 `claude` 命令在 PATH 中

**验证安装:**
```bash
which claude  # 应该显示 claude 的路径
claude --version  # 应该显示版本号
```

### 登录 Claude Code

**重要:** 即使 CLI 已安装，也需要登录才能使用。

```bash
# 运行 Claude Code 进行登录
claude
```

这会打开 Claude Code 界面，你需要：
1. 登录你的 Anthropic 账户
2. 确保你有 Claude Code 的访问权限（Max 或 Pro 订阅者不需要 API key）

**验证登录:**
```bash
# 测试一个简单命令
echo "test" | claude --dangerously-skip-permissions
```

如果成功，应该能看到 Claude 的响应。

---

## ✅ 3. Docker 安装并运行

### 检查是否已安装
```bash
docker --version
docker ps  # 检查 Docker daemon 是否运行
```

### 如果没有安装

**Ubuntu/Debian:**
```bash
# 更新包索引
sudo apt update

# 安装必要的包
sudo apt install -y ca-certificates curl gnupg lsb-release

# 添加 Docker 的官方 GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 设置仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# 将用户添加到 docker 组（避免每次都需要 sudo）
sudo usermod -aG docker $USER

# 注意：需要注销并重新登录才能使组更改生效
# 或者运行: newgrp docker
```

**macOS:**
```bash
# 使用 Homebrew
brew install --cask docker

# 或者从官网下载 Docker Desktop
# https://www.docker.com/products/docker-desktop/
```

**Windows:**
- 从 https://www.docker.com/products/docker-desktop/ 下载 Docker Desktop
- 需要 Windows 10/11 64-bit 和 WSL 2

### 启动 Docker

**Linux:**
```bash
# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker  # 设置开机自启

# 验证
docker ps
```

**macOS/Windows:**
- 启动 Docker Desktop 应用程序

### 验证 Docker 工作正常
```bash
docker run hello-world
```

如果看到 "Hello from Docker!" 消息，说明 Docker 正常工作。

### Docker 资源要求
- **磁盘空间**: ~50GB 用于 Docker 镜像
- **内存**: 16GB+ 推荐
- **macOS/Windows**: 在 Docker Desktop 设置中将内存增加到 8GB+

---

## ✅ 4. 安装 Python 依赖包

### 安装所有必需的包
```bash
# 在项目目录中
cd claudecode_gemini_and_codex_swebench
python3 -m pip install -r requirements.txt
```

### 验证安装
```bash
python3 -c "import datasets, tqdm, jsonlines; print('All packages installed!')"
```

---

## 🧪 完整验证

运行诊断工具检查所有前置条件：

```bash
python3 diagnose.py
```

或者手动验证：

```bash
# 1. 检查 Python
python3 --version

# 2. 检查 Claude CLI
claude --version

# 3. 检查 Docker
docker --version
docker ps

# 4. 检查 Python 包
python3 -c "import datasets, tqdm, jsonlines; print('OK')"
```

---

## 🚀 完成所有前置条件后

一旦所有前置条件都满足，你可以：

1. **运行第一个测试（不评估）:**
   ```bash
   python3 swe_bench.py run --limit 1 --no-eval
   ```

2. **运行完整测试（包含评估）:**
   ```bash
   python3 swe_bench.py run --limit 1
   ```

3. **查看结果:**
   ```bash
   python3 swe_bench.py check
   ```

---

## ❓ 常见问题

### "Command 'python' not found"
- 在 Linux 上使用 `python3` 而不是 `python`
- 或安装 `python-is-python3`: `sudo apt install python-is-python3`

### "Claude CLI not found"
- 确保已从 https://claude.ai/download 安装
- 检查 PATH: `which claude`
- 确保已登录: 运行 `claude` 命令

### "Docker daemon not running"
- Linux: `sudo systemctl start docker`
- macOS/Windows: 启动 Docker Desktop 应用程序

### "Permission denied (Docker)"
- 将用户添加到 docker 组: `sudo usermod -aG docker $USER`
- 注销并重新登录，或运行 `newgrp docker`

