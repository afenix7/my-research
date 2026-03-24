# 第十六节（上）：游戏引擎 Gameplay 玩法系统 — 基础 AI

> GAMES104 游戏引擎理论与实践 · 第十六节上

---

## 目录

1. [课程概述](#课程概述)
2. [导航系统](#导航系统)
3. [世界表达方式](#世界表达方式)
4. [寻路算法](#寻路算法)
5. [感知系统](#感知系统)
6. [决策系统](#决策系统)
7. [行为树](#行为树)
8. [关键术语表](#关键术语表)
9. [总结](#总结)

---

## 课程概述

本节是 GAMES104 第十六节上部分，主题为 **游戏引擎 Gameplay 基础 AI**。AI 内容因内容量庞大（约 180 页课件）被拆成两节：

- **基础 AI（本节）**：导航、寻路、群体模拟、环境感知、基础决策（FSM / 行为树）
- **高级 AI（下节）**：GOAP、HTN、蒙特卡洛树搜索、深度强化学习

---

## 导航系统

### 导航管道三阶段

```
世界表达 (World Representation)
    ↓
寻路 (Pathfinding)
    ↓
路径运动 / 路径平滑 (Path Motion / Steering)
```

### 可行区域（Workable Area）

**Workable Area** 是整个导航系统的基础：定义 AI 体可以活动的区域。

- 由**关卡设计师（Designer）**专门标注，而非美术几何体自动生成
- 约束条件包括物理碰撞、可攀爬高度（climb height）、可跨越间隙
- **角色能力相关**：步兵、骑马 NPC、载具的可行区域各不相同
- 进入**不可行区域（Unworkable Area）**的 AI 体，寻路系统完全失效（产生卡死、抖动等 bug）

---

## 世界表达方式

| 表达方式 | 特点 | 适用场景 |
|---------|------|---------|
| **路点网络（Waypoint Network）** | 手动放置节点；简单但覆盖不全 | 简单线性关卡 |
| **网格地图（Grid Map）** | 均匀切割；直觉；内存开销大 | 2D 游戏、RTS |
| **导航网格（Navigation Mesh）** | 凸多边形；现代引擎首选 | 3D 动作 / 开放世界 |
| **八叉树（Octree）** | 三维空间递归细分 | 3D 飞行 AI |

### 导航网格（NavMesh）

**NavMesh** 是现代游戏引擎的标准导航表达：

- 用**凸多边形（Convex Polygon）**铺满可行区域
- 相邻多边形通过**门廊（Portal）**（共享边）连通
- 将可行区域转化为**多边形图（Polygon Graph）**，节点数远少于等效网格
- Portal 中点连线路径可用**漏斗算法（Funnel Algorithm）**进一步优化

---

## 寻路算法

### Dijkstra 算法

带权图单源最短路径算法：
1. 起点距离 = 0，其余节点 = ∞
2. 维护最小堆优先队列
3. 取出距离最小的节点，更新邻居距离：
   $$\text{dist}[\text{neighbor}] = \min(\text{dist}[\text{neighbor}],\ \text{dist}[\text{current}] + \text{cost})$$
4. 重复直至到达目标

缺点：在大地图上朝所有方向均匀扩展，效率低。

---

### A* 算法

**评估函数：**

$$f(n) = g(n) + h(n)$$

| 符号 | 含义 |
|------|------|
| $g(n)$ | 从起点到节点 $n$ 的**实际代价** |
| $h(n)$ | 从节点 $n$ 到目标的**估计代价（启发值）** |
| $f(n)$ | 综合评分，值越小越优先扩展 |

**常用启发函数：**

曼哈顿距离（网格）：
$$h(n) = |x_n - x_{\text{goal}}| + |y_n - y_{\text{goal}}|$$

欧氏距离（NavMesh）：
$$h(n) = \sqrt{(x_n - x_{\text{goal}})^2 + (y_n - y_{\text{goal}})^2}$$

**关键性质：**
- **可采纳性（Admissibility）**：$h(n)$ 永远不高估实际代价 → 保证找到最优路径
- **一致性（Consistency）**：$h(n) \leq \text{cost}(n, n') + h(n')$

**A* 完整实现（Python）：**

```python
import heapq

def astar(start, goal, graph, heuristic):
    open_list = []
    heapq.heappush(open_list, (0 + heuristic(start, goal), start))
    came_from = {}
    g_score = {start: 0}

    while open_list:
        _, current = heapq.heappop(open_list)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return list(reversed(path))

        for neighbor, cost in graph.neighbors(current):
            tentative_g = g_score[current] + cost
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, goal)
                came_from[neighbor] = current
                heapq.heappush(open_list, (f_score, neighbor))

    return None
```

---

## 感知系统

### 三类感知来源

1. **内部状态**：生命值、弹药、技能冷却
2. **静态空间信息**：战术地图（Tactical Map）、掩体点（Cover Points）、智能对象（Smart Object）
3. **动态感知**：
   - **视觉（Vision）**：视锥（FOV）+ Raycast 判断可见性
   - **听觉（Hearing）**：感知半径 + 障碍物遮挡衰减
   - **影响力图谱（Influence Map）**：地图各区域控制力热图

### 工程优化

| 手段 | 说明 |
|------|------|
| **感知共享** | 同队 AI 共享感知结果，避免重复计算 |
| **可调精度** | 远处 AI 降低感知精度 |
| **Tick 降频** | 远处 AI 降低更新频率 |

---

## 决策系统

### 有限状态机（FSM）

```
[巡逻] ---(发现敌人)---> [追击]
[追击] ---(进入攻击范围)---> [攻击]
[攻击] ---(目标死亡)---> [巡逻]
[攻击] ---(生命值 < 30%)---> [逃跑]
```

**优点：** 简单、可预测、性能好
**缺点：** 状态爆炸、难维护、难复用

---

## 行为树

### 节点状态

```cpp
enum class NodeStatus {
    Success,   // 执行成功
    Failure,   // 执行失败
    Running    // 执行中（异步）
};
```

### 控制节点类型

| 类型 | 成功条件 | 失败条件 |
|------|---------|---------|
| **Sequence（序列）** | 所有子节点 Success | 任一子节点 Failure |
| **Selector（选择器）** | 任一子节点 Success | 所有子节点 Failure |
| **Parallel（并行）** | 可配置 | 可配置 |
| **Decorator（装饰器）** | 取决于装饰器类型 | — |

### 示例：开门进入房间

```
[Root: Selector]
├── [Sequence: 直接进入]
│   ├── [Condition: 门是否开着？]
│   └── [Action: 穿过门]
└── [Sequence: 开门进入]
    ├── [Action: 走向门]
    ├── [Action: 开门]
    └── [Action: 穿过门]
```

### 黑板（Blackboard）

```python
blackboard = {
    "target":           enemy_entity,
    "target_position":  Vector3(10, 0, 5),
    "health":           85,
    "ammo":             30,
    "can_see_player":   False,
    "alert_level":      2,
}
```

---

## 关键术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 可行区域 | Workable Area | 设计师定义的 AI 可活动区域 |
| 导航网格 | Navigation Mesh (NavMesh) | 凸多边形组成的导航结构 |
| 门廊 | Portal | NavMesh 相邻多边形共享边 |
| 漏斗算法 | Funnel Algorithm | 利用 Portal 计算最短路径 |
| 启发函数 | Heuristic Function | A* 中估计到目标代价的函数 |
| 可采纳性 | Admissibility | h(n) 不高估实际代价的性质 |
| 视锥 | Field of View (FOV) | 模拟 AI 视觉范围的锥形区域 |
| 影响力图谱 | Influence Map | 表示地图控制力的热图 |
| 有限状态机 | FSM | 用状态和转换建模 AI 行为 |
| 行为树 | Behavior Tree (BT) | 树状结构的 AI 决策框架 |
| 黑板 | Blackboard | 节点间共享数据的键值存储 |
| 序列节点 | Sequence | 依次执行，全部成功才成功 |
| 选择器节点 | Selector | 依次执行，任一成功即成功 |

---

## 总结

1. **导航系统**：NavMesh（凸多边形 + Portal）构建高效图结构；A* 算法（$f = g + h$）在保证路径质量的前提下高效搜索；漏斗算法 + Steering 完成路径平滑。
2. **感知系统**：三类感知（内部状态 / 静态地图信息 / 动态感知）；工程优化关键是感知共享 + 精度自适应 + Tick 降频。
3. **决策系统**：FSM → HFSM → 行为树的演进；行为树通过 Sequence / Selector / Parallel + Blackboard 实现高模块化、高可维护性的 AI 行为设计。
