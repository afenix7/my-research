# Claude Code + Autoresearch = 自我进化的 AI

## 概述

本视频介绍了 Andrej Karpathy 发布的开源项目 **autoresearch**，以及如何将其"自动化科学实验"思路从机器学习训练领域迁移到任何有可追踪指标的业务场景中——借助 Claude Code 构建全自动自我进化的优化流水线。

核心理念：**赋予 AI 代理一个真实的实验环境，让它整夜自主循环实验，早上醒来即可看到改进结果。**

---

## 核心内容

### 1. Autoresearch 项目起源

Karpathy 在训练自己的语言模型时，想到为什么不让 AI 来自动训练模型。他构建了一个完全自动化实验流程：

```
修改超参数 → 训练 5 分钟 → 检查验证损失 → 保留/舍弃 → 重复
```

- 核心指标：**validation loss**（验证损失）
- 变动因子：超参数（学习率、批大小等）
- 运行方式：整夜自主运行，早上查看实验日志

---

### 2. 自动实验的三要素

任何想要接入 autoresearch 模式的场景，必须同时满足：

| 要素 | 说明 |
|------|------|
| **可追踪的客观指标** | 数字化、可量化，不依赖人工主观判断 |
| **可通过 API 修改的输入变量** | 代理必须能够自动修改实验对象 |
| **快速的反馈循环** | 循环越短，单位时间内迭代次数越多 |

---

### 3. Autoresearch 工作流程

```
1. 设定假设（Hypothesis）
        ↓
2. 修改变量（Modify Variable）
        ↓
3. 运行实验（Run Experiment via API）
        ↓
4. 收集结果（Collect Metrics）
        ↓
5. 选出胜者（Select Winner / Baseline Update）
        ↓
6. 生成新挑战者（Generate Challenger）
        ↓
7. 重复循环（Repeat Every N Hours）
```

实验结果积累在 `resources.md` 文件中，每次新的实验迭代都能读取历史经验，形成**滚雪球式的自我改进**。

---

### 4. 将 Autoresearch 迁移到业务场景：冷邮件优化案例

**背景**：博主大量使用冷邮件营销，核心指标是**回复率**。

**系统架构**：

```
orchestrator.py（协调代理）
    ├── 撰写文案子代理
    ├── Instantly API 调用工具
    ├── 结果存储（JSON + resources.md）
    └── GitHub Actions 调度（每 4 小时）
```

**运行逻辑**：
1. 每 4 小时触发一次 GitHub Actions workflow
2. 协调代理读取上次实验结果
3. 基于 `resources.md` 中积累的知识，生成新版**挑战者（Challenger）**邮件
4. 同时运行**基线版（Baseline）**和挑战者版
5. 收集两个版本的回复率
6. 胜出的挑战者成为下一轮的新基线
7. 将本次经验写入 `resources.md`

**命名约定**：
- `B_xxx`：Baseline 基线版本
- `C_xxx`：Challenger 挑战者版本

---

### 5. 使用 Claude Code 实现的具体步骤

#### 步骤 1：克隆 Autoresearch 仓库

```bash
git clone https://github.com/karpathy/autoresearch
```

Claude Code 读取整个仓库上下文，理解框架后迁移到新领域。

#### 步骤 2：语音描述需求（系统提示词结构）

关键 prompt 要素：
```
受 Karpathy autoresearch 模式启发
核心理念：自主循环实验的代理，使用客观指标作为反馈信号
架构：每 4 小时运行一次循环
优化指标：[目标指标，如回复率]
可变因素：[变动对象，如冷邮件文案]
平台：[工具名，如 Instantly]
API 信息：[稍后提供]
部署：GitHub Actions，每小时运行一次
```

#### 步骤 3：生成核心文件结构

```
email-optimizer/
├── orchestrator.py          # 核心协调代理提示词
├── instantly_client.py      # Instantly API 封装
├── utils/
│   ├── lead_manager.py      # 潜在客户管理
│   └── deploy.py            # 活动部署工具
├── config/
│   ├── resources.md         # 累积的学习知识库
│   └── baseline_test.md     # 基准测试邮件
├── results/                 # JSON 结果存储
├── .env.example             # 环境变量模板
└── .github/
    └── workflows/
        └── optimizer.yml    # GitHub Actions 调度
```

#### 步骤 4：orchestrator.py 的提示词结构

```python
ORCHESTRATOR_PROMPT = """
受 Karpathy autoresearch 模式启发，你是一个邮件优化协调器。

你的职责：
1. 收集前次实验结果（调用 Instantly API）
2. 基于 resources.md 中的历史经验生成新挑战者
3. 部署基线版和挑战者版到 Instantly 平台
4. 等待实验周期结束，收割结果

优化指标：回复率（reply rate）
每次只改变一个变量：邮件文案

挑战者生成规则：
- 基于已知的优质冷邮件策略
- 每次测试一个具体假设（如：缩短长度、增强 CTA、添加社会证明）
- 所有经验记录到 resources.md
"""
```

#### 步骤 5：GitHub Actions 调度

```yaml
# .github/workflows/optimizer.yml
name: Email Optimizer
on:
  schedule:
    - cron: '0 */4 * * *'  # 每 4 小时运行一次
  workflow_dispatch:

jobs:
  optimize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Optimizer
        env:
          INSTANTLY_API_KEY: ${{ secrets.INSTANTLY_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          pip install -r requirements.txt
          python orchestrator.py
```

#### 步骤 6：配置 API 密钥

需要的 API 密钥：
- `INSTANTLY_API_KEY`：邮件平台 API（获取指标 + 创建活动）
- `ANTHROPIC_API_KEY`：Claude Opus 4（用于生成文案和协调决策）
- `SLACK_WEBHOOK_URL`：（可选）实时通知每次更新

---

### 6. 自我进化机制的关键设计

#### resources.md：滚雪球式知识积累

每次实验结束后，协调代理将结论写入 `resources.md`：

```markdown
## 实验记录

### 第 1 轮（基线 vs 挑战者 C1）
- 基线回复率：1.5%
- 挑战者回复率：1.8%
- 胜出：挑战者 C1
- 关键发现：缩短邮件至 75 词以内、添加具体时间的 CTA 效果更好

### 第 2 轮（C1 为新基线 vs 挑战者 C2）
- 基线回复率：1.8%
- 挑战者回复率：2.1%
- 胜出：挑战者 C2
- 关键发现：以具体成果开头（"我帮 X 公司做到了...") 优于通用开场
```

随着迭代次数增加，`resources.md` 积累了大量"什么有效、什么无效"的知识，后续的挑战者生成质量越来越高。

#### 进化轨迹

```
基线 B → C1（+20%）→ C1 成为新基线 → C2（+17%）→ ...
随着 500~1000 次迭代，最终回复率可能是初始基线的数倍
```

---

### 7. Claude Code Hooks 系统的利用

视频中提到的 Claude Code 特性：
- **语音转写（Whisper）**：直接语音描述需求，按住 fn 键输入
- **仓库上下文**：克隆 autoresearch 后，Claude Code 直接读取所有文件作为上下文
- **多代理协调**：orchestrator 作为主代理，子代理分别负责文案生成、API 调用、数据存储

---

### 8. 其他适用场景

凡是满足"可追踪客观指标 + API 可修改输入"的场景都可接入：

| 场景 | 指标 | API 工具 |
|------|------|----------|
| 冷邮件文案 | 回复率 | Instantly API |
| 着陆页优化 | 转化率（CVR） | Wix/WordPress/Webflow API |
| 广告创意 | 点击率/CVR | Facebook/Google Ads API |
| 聊天机器人脚本 | 客户满意度评分 | CRM API |
| 电商产品描述 | 销售额 | 平台 API 或 Chrome MCP |
| YouTube 标题 | 点击率 | YouTube Data v3 API |
| 邮件主题行 | 开信率 | 邮件平台 API |
| 定价页面 | 购买转化率 | 网站 API |

---

### 9. 不适合 Autoresearch 的场景

- **反馈循环太慢**：如果一次实验需要数周才能看到结果，迭代效率极低
- **指标主观模糊**：如"品牌美誉度"等无法量化的目标
- **没有 API 访问权限**：代理无法自动修改变量，只能输出人工操作清单（违背初衷）

---

## 关键术语表

| 术语 | 解释 |
|------|------|
| Autoresearch | Karpathy 的自动化 ML 实验框架，核心是代理自主循环优化 |
| Orchestrator | 协调代理，像交响乐团指挥，管理所有子代理和工具 |
| Baseline | 当前表现最好的版本，作为对照组 |
| Challenger | 新生成的实验版本，与 Baseline 对比 |
| resources.md | 累积知识文件，记录历次实验的发现和经验 |
| validation loss | ML 中的验证损失，Karpathy 案例中的核心指标 |
| GitHub Actions | 云端定时任务调度工具，用于定期触发实验循环 |
| CVR | Conversion Rate，转化率 |
| Feedback loop | 反馈循环，越短越好，决定迭代速度 |

---

## 总结

Autoresearch 的本质是将科学实验方法（假设→实验→观测→结论→新假设）完全自动化。Karpathy 将其用于 ML 模型超参数搜索，而视频作者将其迁移到冷邮件文案优化。

核心洞察：**AI 代理不仅能执行单次任务，还能充当永不停歇的科学家，在无人值守的情况下持续迭代逼近最优解。**

与人工优化相比的优势：
- 人需要睡觉、吃饭，代理 24 小时不间断
- 人每天最多做几次测试，代理每小时可做数次
- 代理的决策质量虽可能低于专家，但**频率优势**远超弥补了质量差距

Claude Code 在其中扮演：
1. **需求翻译器**：将自然语言描述转化为完整可运行代码
2. **上下文理解器**：读取 autoresearch 仓库后迁移架构
3. **代理编排者**：生成 orchestrator + 子代理 + API 客户端的完整系统
