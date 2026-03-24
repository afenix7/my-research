# GAMES104 第十七节（上）：游戏引擎 Gameplay 玩法系统——高级 AI

## 概述

本节课介绍高级 AI 系统的三种核心规划技术：HTN（分层任务网络）、GOAP（目标导向行动规划）以及 MCTS（蒙特卡洛树搜索）。这些技术是现代 3A 游戏 NPC 行为系统的基础，与 Behavior Tree 相比更具表达力和规划能力。

---

## 一、HTN（Hierarchical Task Network，分层任务网络）

### 1.1 背景与动机

**Behavior Tree** 本质上是一个反应机器（reaction machine）：它响应世界输出做出反应，缺乏主观意图。设计师在构建 BT 时其实在心里有"任务目标"，但 BT 结构无法直观表达这一意图（只能靠注释说明"这棵子树是为了什么"）。

**HTN** 从任务目标出发，更符合人类的认知方式：

> 我要上一门课 → 准备学习资料 → 到达教室 → 学习 → Q&A

被使用于 **Horizon Zero Dawn**、**Deus Ex** 等知名 3A 产品。

### 1.2 HTN 基本框架

| 组件 | 说明 |
|------|------|
| **World State** | AI 大脑中对世界关键要素的主观抽象，不是客观世界的完整镜像 |
| **Sensor** | 类似 Perception，负责从游戏环境抓取状态并更新 World State |
| **Domain (HTN Domain)** | 树状层次任务结构及其关联关系 |
| **Planner** | 根据 World State 展开任务树，生成 primitive task 序列 |
| **Plan Runner** | 执行 Planner 生成的计划 |

> **注意**：World State 是主观认知（AI 眼中的世界），Sensor 是感知机制——二者必须区分清楚。

### 1.3 两大核心任务类型

#### Primitive Task（原子任务）

最小执行单元，不可再分解，直接映射为 AI 动作。

```
PrimitiveTask {
    precondition: [条件列表]   // 执行前必须满足
    effect:       [状态变化]   // 执行后对 World State 的修改
}
```

#### Compound Task（复合任务）

由若干 Method 组成，每个 Method 是一个带 precondition 的 task 序列（类比 BT 的 selector + sequencer 组合）。

```
CompoundTask {
    methods: [
        Method {
            precondition: [条件]
            subtasks: [task1, task2, task3]  // 依次执行（sequencer语义）
        },
        Method { ... },   // 优先级更低的备选（selector语义）
    ]
}
```

> **类比**：Compound Task 的多个 Method = BT 的 Selector；单个 Method 内的 subtask 序列 = BT 的 Sequencer。

### 1.4 Root Task

一个特殊的 Compound Task，定义了 AI 体的顶层行为集合。设计师从最 high-level 定义 NPC 的几个关键行为，再逐层展开直到 Primitive Task。

**示例（精英小怪）**：
```
RootTask: BeEliteEnemy
  Method 1 (中毒时): CurePoison
    → MakePotion → UsePotion
  Method 2 (遇强敌时): Flee
    → FindEscapeRoute → RunAway
  Method 3 (遇普通怪): Attack
    → AimWeapon → Strike
  Method 4 (默认): Idle
    → Patrol
```

### 1.5 HTN 规划流程（Planner 伪代码）

```python
def htn_plan(world_state, root_task):
    plan = []
    task_stack = [root_task]

    while task_stack:
        task = task_stack.pop(0)

        if is_primitive(task):
            if check_precondition(task, world_state):
                apply_effect(task, world_state)  # 更新预测状态
                plan.append(task)
            else:
                return None  # 规划失败，需重新规划

        elif is_compound(task):
            method = select_method(task, world_state)  # 按优先级选满足条件的method
            if method:
                task_stack = method.subtasks + task_stack
            else:
                return None

    return plan  # 返回 primitive task 列表
```

### 1.6 Replanning（重新规划）

触发 Replanning 的条件：

1. 当前计划已成功执行完毕
2. 当前计划执行中途失败
3. World State 发生重大变化（Sensor 检测到），使当前计划的 precondition 失效

> **工程意义**：高度不确定环境中，过长的计划链会频繁触发 Replanning，导致 AI 行为"震荡"（今天要练肌肉、明天要游泳、后天要学数学）。需权衡计划长度与环境稳定性。

### 1.7 HTN vs BT 对比

| 维度 | Behavior Tree | HTN |
|------|--------------|-----|
| 设计直觉 | 逐个节点（selector/sequencer）组装 | 以任务目标为出发点层层分解 |
| 执行效率 | 每次 tick 从 root 遍历（O(树大小)） | 仅在 Replanning 时重算，其余 tick 只跑 Plan Runner |
| 表达方式 | 反应式（reaction） | 规划式（planning） |
| 上手难度 | selector/sequencer 概念抽象 | 更符合人类任务分解直觉 |
| 长期行为 | 不擅长 | 天然支持 |

### 1.8 HTN 的局限与注意事项

1. **静态检查工具**：多个 Primitive Task 的 precondition/effect 形成逻辑链，若某个 task 忘记定义 effect，会导致后续任务 precondition 永不满足。需要构建静态验证工具帮助设计师排查。

2. **长链不稳定**：在高度不确定性环境中，过长过缜密的计划链会导致 AI 行为震荡。建议控制计划深度。

3. **效果**：已在 Horizon Zero Dawn、Deus Ex 等游戏中被大规模采用，证明其实用性。

---

## 二、GOAP（Goal-Oriented Action Planning，目标导向行动规划）

### 2.1 背景与动机

GOAP 将 AI 规划问题转化为**图搜索问题**，用 A* 或其他最短路径算法自动求解最优动作序列。这使得 AI 不需要设计师手动维护复杂的 precondition/effect 链，更具环境适应性。

被使用于：**Tomb Raider**、**Assassin's Creed Odyssey** 等。

### 2.2 GOAP 基本构件

```
Agent:
  goal_set:    [目标列表，每个目标是对 World State 的期望条件]
  action_set:  [可用动作列表]

Action {
    precondition:  [执行前 World State 必须满足]
    effect:        [执行后 World State 的变化]
    cost:          float  // 执行代价（时间/资源/风险）
}
```

### 2.3 规划图构造

GOAP 将规划问题转化为有向加权图：

- **节点**：World State 的快照（state combination）
- **边**：Action（从满足其 precondition 的状态，经执行 effect 转移到新状态）
- **边权**：Action 的 cost

```
起始节点: 当前 World State
目标节点: 满足 Goal 的 World State

问题: 找从起始节点到目标节点的最小 cost 路径
算法: A* 搜索（启发式 = 离目标状态的"距离"估计）
```

### 2.4 后向规划（Backward Planning）

GOAP 通常采用**从目标倒推**的方式：

```python
def goap_backward_plan(goal, current_state, actions):
    # 从目标状态开始，找能"造成"目标 effect 的 action
    unsatisfied = Stack([goal])
    plan = []

    while not unsatisfied.empty():
        current_goal = unsatisfied.pop()
        # 找到 effect 能满足 current_goal 的 action
        candidate_actions = find_actions_satisfying(current_goal, actions)
        best_action = min(candidate_actions, key=lambda a: a.cost)
        plan.prepend(best_action)
        # 将该 action 的 precondition 作为新的待满足目标
        for pre in best_action.precondition:
            if not satisfied(pre, current_state):
                unsatisfied.push(pre)

    return plan
```

### 2.5 GOAP vs HTN 对比

| 维度 | HTN | GOAP |
|------|-----|------|
| 规划方式 | 层次化任务分解（人工定义） | 图搜索自动求解 |
| 设计工作量 | 手动维护 precondition/effect 链 | 只需定义 action 集和 goal |
| 适应性 | 中（需 Replanning） | 高（动态重规划） |
| 行为直觉性 | 高 | 中 |
| 计算成本 | 低（缓存计划） | 较高（每次搜索图） |

---

## 三、MCTS（Monte Carlo Tree Search，蒙特卡洛树搜索）

### 3.1 背景与动机

MCTS 最早因 **AlphaGo** 打败人类围棋冠军而广为人知，同时也被用于 **Total War** 等电子游戏 AI。其核心思想：**用随机模拟（Monte Carlo）评估当前局面优劣，替代难以计算的精确估值函数**。

### 3.2 MCTS 四步迭代

```
初始状态: 根节点 = 当前游戏局面

每次迭代:
  1. Selection（选择）
     从根节点出发，按 UCT 策略选择最值得探索的子节点，
     直到到达叶节点。

  2. Expansion（扩展）
     在叶节点处扩展一个或多个新子节点（对应可行动作）。

  3. Simulation（模拟 / Playout）
     从新节点出发，用 Default Policy（快速随机策略）
     模拟到游戏结束，得到胜负结果。

  4. Backpropagation（反向传播）
     将模拟结果沿路径反向传播，更新路径上各节点的 Q 和 N。
```

### 3.3 节点统计量

每个节点维护：

$$Q(v) = \text{该节点经过的模拟中，胜利次数}$$
$$N(v) = \text{该节点被访问次数（模拟次数）}$$
$$\bar{Q}(v) = \frac{Q(v)}{N(v)} = \text{胜率估计}$$

### 3.4 UCT 策略（Exploit vs Explore 权衡）

UCT（Upper Confidence Bound for Trees）公式：

$$\text{UCT}(v) = \frac{Q(v)}{N(v)} + c \sqrt{\frac{\ln N(\text{parent}(v))}{N(v)}}$$

| 项 | 含义 |
|----|------|
| $\frac{Q(v)}{N(v)}$ | **Exploit**：利用已知信息，选胜率高的节点 |
| $c \sqrt{\frac{\ln N(\text{parent})}{N(v)}}$ | **Explore**：探索访问次数少的节点（避免局部最优） |
| $c$ | 权衡系数（典型值 $c = \sqrt{2}$） |

### 3.5 Default Policy（快速落子策略）

Simulation 阶段使用的快速策略，无需精确——目标是快速得到胜负结果：
- 随机策略（最简单，效率最高）
- 轻量级启发式策略

### 3.6 MCTS 伪代码

```python
def mcts(root_state, iterations):
    root = MCTSNode(state=root_state)

    for _ in range(iterations):
        # 1. Selection
        node = root
        while node.is_fully_expanded() and not node.is_terminal():
            node = node.best_child(c=sqrt(2))  # UCT selection

        # 2. Expansion
        if not node.is_terminal():
            node = node.expand()  # 添加一个未探索子节点

        # 3. Simulation
        result = simulate(node.state)  # default policy playout

        # 4. Backpropagation
        while node is not None:
            node.N += 1
            node.Q += result
            node = node.parent

    return root.best_child(c=0).action  # 返回 N 最大的动作

def simulate(state):
    while not state.is_terminal():
        action = random.choice(state.legal_actions())
        state = state.apply(action)
    return state.reward()
```

### 3.7 MCTS 在游戏中的应用特点

| 场景 | 适用性 |
|------|--------|
| 围棋/象棋（信息对称） | 极强（AlphaGo/AlphaZero 已完胜人类） |
| RTS 游戏（信息不对称，战争迷雾） | 较难，信息不完全增加复杂度 |
| 回合制策略游戏 | 较好 |
| 实时射击/格斗游戏 | 时间预算有限，需快速模拟 |

> **关键观察**：围棋的信息对称性使 MCTS + 深度学习能够碾压人类。但在有战争迷雾的 RTS 游戏（如星际争霸）中，信息不对称大幅增加难度——"人类最后的尊严还在"。

---

## 四、分层 AI 架构与工程实践

### 4.1 AI 服务化

大型游戏引擎通常将 AI 作为独立的服务（AI Server）运行，与渲染线程解耦，允许按各 AI 体类型分配不同的 tick 预算。

### 4.2 预算（Budget）管理

- **高频更新**（每帧/10ms）：感知层 Sensor、动画状态机
- **中频更新**（100ms~500ms）：行为决策、Plan Runner
- **低频更新**（500ms~2s）：HTN Planner / GOAP 重规划

### 4.3 性能注意点

- BT 每次 tick 从 root 完整遍历，自身可能消耗 70%~80% AI 预算
- HTN 仅在 Replanning 触发时重算，其余时间只执行 Plan Runner（高效）
- MCTS 的 iteration 数量与时间预算成正比，可动态调整质量

---

## 关键术语表

| 术语 | 英文全称 | 简要说明 |
|------|----------|----------|
| **HTN** | Hierarchical Task Network | 分层任务网络，从目标出发层层分解任务 |
| **GOAP** | Goal-Oriented Action Planning | 目标导向行动规划，将规划转化为图搜索 |
| **MCTS** | Monte Carlo Tree Search | 蒙特卡洛树搜索，用随机模拟评估局面 |
| **Primitive Task** | — | 原子任务，不可再分，直接执行 |
| **Compound Task** | — | 复合任务，包含多个 Method 和子任务序列 |
| **Root Task** | — | HTN 的根节点任务，定义 AI 顶层行为 |
| **World State** | — | AI 对世界的主观认知状态抽象 |
| **Sensor** | — | 感知模块，更新 World State |
| **Planner** | — | 根据 World State 生成执行计划 |
| **Plan Runner** | — | 执行 Planner 生成的 primitive task 序列 |
| **Replanning** | — | 触发重新规划的机制 |
| **Precondition** | — | 任务/动作执行前必须满足的条件 |
| **Effect** | — | 任务/动作执行后对 World State 的修改 |
| **Default Policy** | — | MCTS Simulation 阶段的快速落子策略 |
| **UCT** | Upper Confidence Bound for Trees | MCTS 的 Selection 策略，平衡利用与探索 |
| **Q(v)** | — | MCTS 节点累计胜利次数 |
| **N(v)** | — | MCTS 节点访问次数 |

---

## 总结

1. **HTN** 将 AI 行为组织为层次化的任务树，设计直观、执行高效，已被 Horizon Zero Dawn 等大作采用；其核心是 primitive task 与 compound task 的两层抽象，以及 Replanning 机制应对动态环境。

2. **GOAP** 将规划问题转化为加权图搜索（通常用 A*），AI 的"智慧"来自对 action precondition/effect/cost 的建模；行为更具适应性，设计师无需手工编排动作序列，代价是实时计算开销较高。

3. **MCTS** 用迭代的随机模拟替代精确估值，通过 UCT 平衡利用与探索；在围棋等信息对称博弈中表现卓越（AlphaGo），但在信息不对称的实时游戏中面临更大挑战。

4. **工程实践**：三种技术均需结合预算管理（tick 频率控制）、AI 服务化解耦，以及针对各游戏类型的特殊优化，才能在实际产品中高效运行。
