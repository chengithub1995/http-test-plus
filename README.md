# http-test-plus

一个用于 AI Skill 的 HTTP 接口测试工具，支持：

- 单请求 JSON HTTP 调试
- 批量 YAML 用例执行
- 登录取 token、变量提取、串联请求
- `expected_status` 负例校验
- 自动生成完整中文 Markdown 测试报告

适合放到 Codex / Claude Code 风格的本地 skill 目录中，供 AI 在联调接口、验证流程、编写批量接口测试时直接调用。

## 目录结构

```text
http-test-plus/
├── SKILL.md
├── README.md
├── .gitignore
├── agents/
│   └── openai.yaml
├── references/
│   ├── agent-platform-demo.md
│   ├── batch-yaml.md
│   └── report-artifacts.md
└── scripts/
    └── http_client.py
```

## 功能说明

这个 skill 的核心能力包括：

1. 单接口测试：适合快速调试某个 GET/POST/PUT/PATCH/DELETE 接口。
2. 批量流程测试：适合登录、创建、查询、更新、删除等多步骤串联场景。
3. 变量提取与复用：支持从上一步响应中提取 token、ID 等字段供后续步骤引用。
4. 中文报告输出：每次执行默认生成完整 Markdown 中文测试报告。

## 依赖环境

- Python 3.10+
- `requests`
- `PyYAML`
- `jmespath`

安装依赖：

```bash
pip install requests pyyaml jmespath
```

## 安装为本地 Skill

把这个目录放到你的 Codex skill 目录下，目录名保持为 `http-test-plus`。

常见位置：

- Windows: `%USERPROFILE%\.codex\skills\http-test-plus`
- macOS / Linux: `~/.codex/skills/http-test-plus`
- 如果设置了 `CODEX_HOME`：`$CODEX_HOME/skills/http-test-plus`

如果你是从 GitHub 拉取：

```bash
git clone <your-repo-url> http-test-plus
```

然后把仓库放到上述 skill 目录中，或直接克隆到该目录下。

如果当前终端没有识别新 skill，重启终端或新开一个会话后再试。

## 使用方式

### 1. 通过 Skill 调用

在支持 skill 的 AI 会话中，可直接让模型使用：

```text
使用 $http-test-plus 测试这个接口，并返回中文结论和报告路径
```

### 2. 直接运行脚本

单请求模式：

```bash
python scripts/http_client.py ^
  --url "https://api.example.com/items" ^
  --method "GET" ^
  --headers "{}" ^
  --auth-header "{}" ^
  --query "{}" ^
  --body "{}" ^
  --timeout 30
```

批量模式：

```bash
python scripts/http_client.py ^
  --batch "path/to/your-suite.yml" ^
  --timeout 30
```

说明：

- 默认在当前目录输出 Markdown 报告
- 可通过 `--report-dir` 指定报告目录
- 终端默认输出中文结论、统计信息和报告路径

## 批量 YAML 规则

完整规则见 [references/batch-yaml.md](references/batch-yaml.md)。

核心约定：

- `config.auth_header` 放共享静态请求头
- `request.headers` 放动态请求头
- 使用 `${tests.step_id.key}` 引用前序步骤提取值
- 使用 `extract` + JMESPath 提取响应字段
- 使用 `expected_status` 声明负例期望状态码

示例：

```yaml
config:
  base_url: "http://127.0.0.1:8000"
  stop_on_error: true

tests:
  - id: login
    description: "登录并提取 token"
    request:
      method: POST
      url: "/auth/login"
      body:
        username: "creator"
        password: "demo123"
    extract:
      token: "data.token"

  - id: list_items
    description: "携带 token 查询列表"
    request:
      method: GET
      url: "/items"
      headers:
        Authorization: "Bearer ${tests.login.token}"
```

## 发布到 GitHub 的步骤

1. 在 GitHub 新建一个仓库，建议仓库名也叫 `http-test-plus`。
2. 在本地进入当前目录，初始化 Git：

```bash
git init
git add .
git commit -m "feat: add http-test-plus skill"
```

3. 绑定远程仓库：

```bash
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main
```

4. 以后更新 skill 时继续：

```bash
git add .
git commit -m "docs: update README"
git push
```

## 建议补充

如果你后面想让别人更容易安装，还可以继续补这些内容：

- 一个真实可运行的 `examples/` 批量 YAML 示例
- `LICENSE`
- GitHub Release 或版本标签

当前这个仓库作为个人 skill 仓库发布，已经具备基础可用结构。
