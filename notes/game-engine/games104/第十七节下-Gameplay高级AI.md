# GAMES104 第十七节（下）：游戏引擎 Gameplay 玩法系统——高级 AI

## 概述

本节重点讲解机器学习（Machine Learning）在游戏 AI 中的应用，以 AlphaStar（DeepMind 打星际争霸的 AI）为核心案例，介绍强化学习（Reinforcement Learning）、马尔可夫决策过程（MDP）、Q-learning、策略梯度等基础概念，以及 Utility AI 等实用方法。

> 讲师说明：机器学习本身是独立的系统性学科，本节仅涵盖游戏引擎视角下的基础概念与应用方法。

---

## 一、机器学习分类概览

| 类别 | 英文 | 核心思想 | 游戏应用 |
|------|------|----------|----------|
| **监督学习** | Supervised Learning | 人工打标签，学分类/回归 | 行为克隆（模仿玩家） |
| **无监督学习** | Unsupervised Learning | 自动聚类，发现数据规律 | 用户画像、玩家行为分析 |
| **半监督学习** | Semi-supervised Learning | 少量标签 + 大量无标签数据 | — |
| **强化学习** | Reinforcement Learning | 通过奖惩信号自主学习策略 | AlphaStar、游戏 AI 策略训练 |

> **监督学习**本质是分类器，经典案例：ImageNet 图像识别（CNN 出现后已无悬念）。
>
> **无监督学习**本质是聚类器，经典案例：推荐系统中的用户画像（上千维度无法手动定义）。
>
> **强化学习**是本节核心，适用于决策序列问题（游戏 AI 的天然场景）。

---

## 二、强化学习基础：MDP（马尔可夫决策过程）

### 2.1 核心概念

强化学习的数学框架是 **MDP（Markov Decision Process）**，包含以下核心元素：

| 符号 | 名称 | 说明 |
|------|------|------|
| $S$ | **State（状态）** | 对世界当前情况的表示 |
| $A$ | **Action（动作）** | AI 可执行的操作集合 |
| $R$ | **Reward（奖励）** | 执行动作后环境给出的反馈信号 |
| $P(s' \mid s, a)$ | **状态转移概率** | 在状态 $s$ 执行动作 $a$ 后转移到 $s'$ 的概率 |
| $\pi$ | **Policy（策略）** | 给定状态，输出动作概率分布的函数 |
| $\gamma$ | **折扣因子** | $0 < \gamma \leq 1$，平衡短期与长期奖励 |

### 2.2 状态转移概率

$$P(s' \mid s, a) = \Pr(\text{下一状态} = s' \mid \text{当前状态} = s, \text{动作} = a)$$

> **要点**：状态转移不是确定性函数，而是**随机变量**。例如：精英怪射箭有 80% 概率命中玩家，小怪只有 10% 概率命中——这些都是概率分布。

### 2.3 Policy（策略）

策略 $\pi$ 是 AI 的"大脑"——一个从状态到动作概率分布的映射：

$$\pi(a \mid s) = \Pr(\text{执行动作} a \mid \text{当前状态} s)$$

> **重要**：Policy 输出的不是确定的单一动作，而是所有可能动作的概率分布。例如在超级马里奥中：向左 0.7、向右 0.1、跳跃 0.2。

Policy 可以用任意机制实现：神经网络、有限状态机、HTN、GOAP、行为树……它们都是 Policy 的不同实现形式。

### 2.4 Total Reward（折扣累积奖励）

从时间步 $t$ 开始的折扣累积奖励（Return）：

$$G_t = r_t + \gamma r_{t+1} + \gamma^2 r_{t+2} + \cdots = \sum_{k=0}^{\infty} \gamma^k r_{t+k}$$

**折扣因子 $\gamma$ 的含义**：

| $\gamma$ 值 | 效果 |
|------------|------|
| $\gamma \approx 1$（如 0.999） | 重视长期奖励，AI 更具"战略眼光" |
| $\gamma \approx 0.95$ | 偏重近期奖励，AI 更"响应灵敏" |
| $\gamma = 1$ | 无折扣，完全看长期（适用于有限步骤博弈） |

> **直觉**：今天好好读书将来能赚一个亿（长期奖励），但今天不吃饭三天后会饿死（短期惩罚）。$\gamma$ 控制 AI 多大程度上"顾眼前"还是"谋长远"。

### 2.5 Value Function & Q Function

**状态价值函数（V-function）**：

$$V^\pi(s) = \mathbb{E}_\pi\left[\sum_{k=0}^{\infty} \gamma^k r_{t+k} \,\Big|\, s_t = s\right]$$

**动作价值函数（Q-function）**：

$$Q^\pi(s, a) = \mathbb{E}_\pi\left[\sum_{k=0}^{\infty} \gamma^k r_{t+k} \,\Big|\, s_t = s, a_t = a\right]$$

**Bellman 方程**（Q-function 的递推形式）：

$$Q^\pi(s, a) = \mathbb{E}\left[r + \gamma \sum_{a'} \pi(a' \mid s') Q^\pi(s', a')\right]$$

---

## 三、Q-learning

Q-learning 是一种**无模型（model-free）**的强化学习算法，直接通过与环境交互学习最优 Q 函数。

### 3.1 Q-learning 更新公式

$$Q(s, a) \leftarrow Q(s, a) + \alpha \left[r + \gamma \max_{a'} Q(s', a') - Q(s, a)\right]$$

| 符号 | 含义 |
|------|------|
| $\alpha$ | 学习率（learning rate），控制更新步长 |
| $r$ | 执行动作 $a$ 后获得的即时奖励 |
| $\gamma \max_{a'} Q(s', a')$ | 对下一状态最优 Q 值的折扣估计 |
| $[r + \gamma \max_{a'} Q(s', a') - Q(s, a)]$ | **TD 误差**（Temporal Difference Error） |

### 3.2 Q-learning 伪代码

```python
def q_learning(env, episodes, alpha=0.1, gamma=0.99, epsilon=0.1):
    Q = defaultdict(lambda: defaultdict(float))  # Q(s, a) 初始化为 0

    for episode in range(episodes):
        state = env.reset()

        while not done:
            # epsilon-greedy 策略（平衡探索与利用）
            if random() < epsilon:
                action = env.random_action()       # Explore
            else:
                action = argmax(Q[state])          # Exploit

            next_state, reward, done = env.step(action)

            # TD 更新
            td_target = reward + gamma * max(Q[next_state].values())
            td_error  = td_target - Q[state][action]
            Q[state][action] += alpha * td_error

            state = next_state

    return Q
```

---

## 四、Policy Gradient（策略梯度）

与 Q-learning 不同，策略梯度方法直接优化 Policy 参数（通常是神经网络权重）。

### 4.1 目标函数

$$J(\theta) = \mathbb{E}_{\pi_\theta}\left[G_t\right] = \mathbb{E}_{\pi_\theta}\left[\sum_{t=0}^T \gamma^t r_t\right]$$

### 4.2 策略梯度定理

$$\nabla_\theta J(\theta) = \mathbb{E}_{\pi_\theta}\left[\nabla_\theta \log \pi_\theta(a \mid s) \cdot Q^{\pi_\theta}(s, a)\right]$$

**直觉**：若某动作带来正回报，就增加该动作的概率；若带来负回报，就减小该动作的概率。

### 4.3 Actor-Critic 架构

```
Actor（策略网络）:  π_θ(a | s) → 输出动作概率分布
Critic（价值网络）: V_φ(s)     → 评估当前状态价值，提供基准线（baseline）

更新：
  Advantage: A(s, a) = Q(s, a) - V(s)
  Actor 梯度: ∇_θ log π_θ(a|s) · A(s, a)
  Critic 更新: MSE(V_φ(s), G_t)
```

---

## 五、AlphaStar 案例分析

AlphaStar 是 DeepMind 用深度强化学习打星际争霸（StarCraft II）的 AI，是游戏 AI 领域的标杆案例。

### 5.1 星际争霸 vs 围棋的挑战对比

| 特性 | 围棋（AlphaGo） | 星际争霸（AlphaStar） |
|------|----------------|----------------------|
| **信息对称性** | 完全对称，双方均可见全局 | 信息不对称，战争迷雾遮蔽 |
| **步骤确定性** | 每步规则明确 | 实时，动作空间连续 |
| **状态空间** | 超大但结构清晰 | 超大且包含空间信息 |
| **当前 AI 表现** | 完胜人类 | 仍在人类顶级玩家附近 |

> 围棋的信息对称性使 MCTS + 深度学习能彻底解决它。星际争霸的战争迷雾（信息不对称）是额外的挑战。

### 5.2 State 表示（三类输入）

AlphaStar 针对星际争霸的状态，设计了三类不同的 State 表示并用对应的神经网络处理：

#### 第一类：标量/定场数据（资源、人口等）

```
输入: 资源量、各类单位数量、已用人口、科技树状态等固定维度数据
处理: MLP（Multi-Layer Perceptron，多层感知机）
```

#### 第二类：地图/图像数据

```
输入: 小地图、战争迷雾图、地形高低图、已探索区域图、influence map 等
处理: CNN（Convolutional Neural Network，卷积神经网络）
      具体用 ResNet（残差网络，作者孙剑博士提出）
      ResNet 的 skip connection 保留了高频细节信息
```

#### 第三类：可变长度单位数据（单位列表）

```
输入: 我方/敌方单位的种类、坐标、状态（长度随时间变化）
处理: Transformer（处理不定长序列的自注意力机制）
```

#### 时序整合

```
将三类输出整合后，输入 LSTM（Long Short-Term Memory）
LSTM 维护跨时间步的"记忆"，让 AI 像人类一样有历史感知
```

### 5.3 Action 设计

```
原始输入方式: 鼠标点击/拖动（不合适）
AlphaStar: 直接向单位下达语义命令（移动、攻击、建造等）
公平性约束: 实际比赛中限制 APM，模拟人类手速
```

### 5.4 Reward 设计

```
简单 Reward: 赢得比赛 +1，输 0（稀疏奖励）
进阶 Reward: 为各种中间行为添加奖励信号
  - 消灭敌方单位 +
  - 建造关键建筑 +
  - 控制资源点 +
  - 损失我方单位 -
```

> **稀疏奖励的问题**：一局星际长达 20~60 分钟，只有最后胜负才有奖励信号，AI 很难从如此稀疏的信号中有效学习。精心设计 reward shaping 是 AlphaStar 成功的关键之一。

### 5.5 网络架构总图

```
输入层:
  标量数据 ──→ MLP ──┐
  地图数据 ──→ CNN ──┼──→ LSTM ──→ Actor（Policy）──→ Action
  单位数据 ──→ Transformer ──┘           ↓
                                    Critic（Value）
```

### 5.6 训练策略

AlphaStar 使用多阶段训练：

1. **行为克隆**（Supervised Learning）：先用人类玩家对局数据预训练，使 AI 获得基础能力
2. **自我对弈**（Self-Play）：用多个 AI 互相对打，通过联盟训练（League Training）不断进化
3. **联盟训练**：维护一个 AI 玩家池（main agents + exploiters + league exploiters），相互博弈避免策略退化

> "训练策略设计得好不好，直接决定 AI 聪不聪明。"

---

## 六、Utility AI（效用 AI）

### 6.1 基本思想

Utility AI 为每个可能的动作计算一个**效用分数（Utility Score）**，然后选择效用最高（或按概率采样）的动作执行。适合需要在多个目标间权衡的复杂 NPC。

### 6.2 效用函数

$$U(a) = \sum_{i} w_i \cdot f_i(s, a)$$

| 符号 | 含义 |
|------|------|
| $a$ | 候选动作 |
| $w_i$ | 第 $i$ 个考量因素的权重 |
| $f_i(s, a)$ | 第 $i$ 个考量因素的评分函数（通常归一化到 [0, 1]） |

**示例：NPC 战斗决策**

```python
def compute_utility(action, state):
    scores = {
        "attack":  health_factor(state) * 0.4
                 + threat_factor(state) * 0.3
                 + ammo_factor(state) * 0.3,
        "flee":    (1 - health_factor(state)) * 0.5
                 + threat_factor(state) * 0.5,
        "heal":    (1 - health_factor(state)) * 0.7
                 + time_pressure(state) * 0.3,
        "patrol":  0.1  # 默认低效用
    }
    return scores[action]
```

### 6.3 Utility AI vs HTN/GOAP

| 维度 | HTN/GOAP | Utility AI |
|------|----------|------------|
| 规划深度 | 多步前向规划 | 单步决策 |
| 适用场景 | 复杂序列行为 | 多目标权衡决策 |
| 设计方式 | 显式任务/动作定义 | 权重调参 |
| 可解释性 | 高 | 中 |

---

## 七、延伸：Reward Shaping 与稀疏奖励

**稀疏奖励（Sparse Reward）**：只在游戏结束时给出奖励（赢/输），中间步骤无信号。

**问题**：AI 无法有效学习——一局游戏几千步，偶尔一次胜利信号无法指导哪一步是"好棋"。

**Reward Shaping 策略**：
```python
# 在每一步添加中间奖励信号
def shaped_reward(state, action, next_state):
    r = 0.0
    if killed_enemy_unit(state, next_state):    r += 0.1
    if lost_own_unit(state, next_state):         r -= 0.1
    if captured_resource(state, next_state):     r += 0.05
    if game_won(next_state):                     r += 1.0
    if game_lost(next_state):                    r -= 1.0
    return r
```

> 但过于精细的 Reward Shaping 会引导 AI 进入人类设计者预想的行为模式，可能限制 AI 发现创新策略（如 AlphaStar 发现的一些人类从未想到的战术）。这是 RL 研究的重要课题。

---

## 关键术语表

| 术语 | 英文全称 | 简要说明 |
|------|----------|----------|
| **RL** | Reinforcement Learning | 强化学习 |
| **MDP** | Markov Decision Process | 马尔可夫决策过程 |
| **Policy** | — | 策略，从状态映射到动作概率分布的函数 |
| **Reward** | — | 奖励信号，环境对 AI 动作的反馈 |
| **State** | — | 状态，对世界的表示 |
| **Action** | — | 动作，AI 可执行的操作 |
| **Q-function** | — | 动作价值函数，Q(s,a) 表示在状态 s 执行动作 a 的期望回报 |
| **V-function** | — | 状态价值函数，V(s) 表示在状态 s 下的期望回报 |
| **Bellman 方程** | — | Q/V 函数的递推关系式 |
| **TD Error** | Temporal Difference Error | 时序差分误差，Q-learning 的更新量 |
| **$\alpha$** | Learning Rate | 学习率，控制 Q-learning 更新步长 |
| **$\gamma$** | Discount Factor | 折扣因子，平衡短期与长期奖励 |
| **Policy Gradient** | — | 策略梯度，直接优化策略参数的 RL 方法 |
| **Actor-Critic** | — | 结合策略网络（Actor）和价值网络（Critic）的 RL 架构 |
| **MLP** | Multi-Layer Perceptron | 多层感知机，处理固定维度数值数据 |
| **CNN** | Convolutional Neural Network | 卷积神经网络，处理图像/地图数据 |
| **ResNet** | Residual Network | 残差网络，CNN 的改进版，保留高频细节 |
| **LSTM** | Long Short-Term Memory | 长短时记忆网络，处理时序数据 |
| **Transformer** | — | 自注意力机制，处理不定长序列数据 |
| **AlphaStar** | — | DeepMind 打星际争霸的深度强化学习 AI |
| **Utility AI** | — | 效用 AI，用评分函数在多动作间权衡选择 |
| **Reward Shaping** | — | 奖励塑形，为稀疏奖励添加中间信号 |
| **Self-Play** | — | 自我对弈，AI 与自身历史版本对打来进化 |
| **Behavior Cloning** | — | 行为克隆，从人类示范中学习初始策略 |
| **Sparse Reward** | — | 稀疏奖励，只在终局给出奖励 |
| **战争迷雾** | Fog of War | RTS 游戏中信息不对称的体现，是 AI 的主要挑战之一 |

---

## 总结

1. **机器学习分类**：监督（分类）、无监督（聚类）、强化（决策序列）——强化学习是游戏 AI 的天然匹配。

2. **MDP 框架**：游戏 AI 的数学基础。State（世界表示）、Action（可执行操作）、Reward（奖惩信号）、Policy（决策函数）、$\gamma$（短期/长期权衡），五要素缺一不可。折扣因子 $\gamma$ 的设定直接影响 AI 的行为风格。

3. **Q-learning**：无模型 RL 的经典算法，通过 TD 误差迭代更新 $Q(s,a)$，最终收敛到最优策略；更新公式 $Q(s,a) \leftarrow Q(s,a) + \alpha[r + \gamma\max Q(s',a') - Q(s,a)]$ 是核心。

4. **策略梯度与 Actor-Critic**：直接优化 Policy 参数，适合大动作空间；Actor-Critic 结合价值估计提高稳定性。

5. **AlphaStar**：通过精心设计的 State 表示（MLP+CNN+Transformer+LSTM）、Reward Shaping、行为克隆预训练 + 联盟自我对弈训练，构建了能与人类职业选手竞争的星际争霸 AI，展示了深度强化学习在复杂游戏场景的工程化应用。

6. **Utility AI**：简单高效的多目标权衡决策方法，通过效用函数评分选择动作，与 HTN/GOAP 互补——前者适合单步权衡，后者适合序列规划。

7. **实践教训**：在复杂游戏（尤其是信息不对称的 RTS）中应用 RL，核心挑战在于 State 表示设计、Reward 设计和训练策略三个方面——工程实现远比理论复杂。
