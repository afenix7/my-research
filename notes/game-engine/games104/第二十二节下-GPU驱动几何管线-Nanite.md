# GAMES104 第二十二节（下）：Nanite 虚拟几何系统

> 本节是 GAMES104 第二十二节下半部分，聚焦 Unreal Engine 5 的 **Nanite** 技术——实现"无限几何细节"的核心系统。内容涵盖 Nanite 的设计目标与选型、Cluster Group 与 DAG 结构、运行时 LOD 选择、软光栅化，以及 Visibility Buffer 在 Nanite 中的应用。

---

## 目录

1. [Nanite 的设计目标](#1-nanite-的设计目标)
2. [几何表示方案的选型](#2-几何表示方案的选型)
3. [Cluster Group 与简化策略](#3-cluster-group-与简化策略)
4. [DAG 结构：有向无环图而非树](#4-dag-结构有向无环图而非树)
5. [运行时 LOD 选择：误差度量](#5-运行时-lod-选择误差度量)
6. [Streaming 与显存管理](#6-streaming-与显存管理)
7. [软光栅化（Software Rasterizer）](#7-软光栅化software-rasterizer)
8. [Visibility Buffer 在 Nanite 中的应用](#8-visibility-buffer-在-nanite-中的应用)
9. [Shadow 裁剪策略](#9-shadow-裁剪策略)
10. [关键术语表](#10-关键术语表)
11. [总结](#11-总结)

---

## 1. Nanite 的设计目标

### 1.1 渲染者的梦想

从真实世界可以观察到"无穷无尽的细节"——海浪拍击岩石时，你可以看到无限层次的几何精度。实时渲染领域长久以来的梦想，就是在计算机中还原这种"电影级（Cinematic）"的几何精度。

**Nanite 的核心承诺**：

> 场景中有多少几何体，就能在屏幕上显示多少细节；但实际绘制的三角形数量，不超过屏幕像素数量。

### 1.2 类比 Virtual Texture

Nanite 的设计灵感直接来源于 **Virtual Texture**（虚拟纹理，John Carmack 提出）：

| 维度 | Virtual Texture | Virtual Geometry (Nanite) |
|------|-----------------|---------------------------|
| 核心问题 | 场景纹理总量超出显存 | 场景几何总量超出处理能力 |
| 解决思路 | 只加载当前视角所需精度的纹理片段 | 只渲染当前视角所需精度的几何片段 |
| 精度控制 | 基于屏幕空间纹素密度 | 基于屏幕空间像素密度 |

**关键约束**：

$$\text{屏幕像素数} = W \times H \approx \text{最多需要绘制的三角形数}$$

例如 1080p 屏幕有约 200 万像素，因此理论上每帧只需绘制约 200 万个三角形（每像素一个三角形即可达到"电影级"精度）。

### 1.3 几何数据的挑战

与纹理不同，几何（Geometry）是 **Irregular Data**（非均匀数据）：

- 顶点在内存中的布局不连续（index buffer 可能跳跃式访问 vertex buffer）
- LOD0 和 LOD1 的 mesh 完全独立，无法直接 filtering
- 对大场景做动态 streaming 非常困难

---

## 2. 几何表示方案的选型

Nanite 作者在决定方案前系统分析了所有可能的几何表示形式：

### 2.1 候选方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Voxel（体素）** | Uniform 数据，易于 filtering | 数据量惊人（高频细节需极高分辨率）；现有艺术家工具不生产 voxel 资产 |
| **Subdivision Surface** | 光滑、可细分；艺术家常用四边形建模 | 只能往上细分，不能减面；无法从原始 mesh 直接生成粗糙 LOD |
| **Displacement Map** | 少量三角形 + 贴图 = 高精细度 | 硬表面效果差；生成高质量 displacement map 本身需额外计算 |
| **Point Cloud（点云）** | 3D Scanner 原生格式；可 filtering | 高精度时数据量大；rendering 质量一般（splat 模式 overdraw 严重）|
| **Triangle Mesh（三角网格）** | 最成熟；全链路工具支持；硬件最优化 | Irregular data，难以 filtering；传统 LOD 管线有接缝问题 |

### 2.2 最终选择：Triangle Mesh

作者的结论：

> 选择三角形网格，是因为整个**内容创作管线**（3ds Max、Maya、ZBrush）都基于三角形，强行转换到其他格式的成本是**致命的**。硬件对三角形的支持也是最成熟的。

---

## 3. Cluster Group 与简化策略

### 3.1 朴素 Cluster LOD 层次的问题

基础思路：将 Mesh 切成 Cluster（128 个三角形），然后每次将相邻两个 Cluster 合并、减面，形成层次结构：

```
L0:  [C0][C1][C2][C3][C4][C5][C6][C7]   (8个cluster，共1024个三角形)
                  ↓ 两两合并简化，面数减半
L1:     [C01]      [C23]      [C45]      [C67]   (4个cluster)
                  ↓
L2:           [C0123]                [C4567]   (2个cluster)
                  ↓
L3:                   [C01234567]               (1个cluster)
```

**致命问题**：LOD 切换时不同 Cluster 使用不同 LOD Level，相邻 Cluster 的边会出现**裂缝（Crack）**：

```
LOD0 Cluster (精细)   |  LOD1 Cluster (粗糙)
                      |
  ████████████████████|░░░░░░░░░░░░
  ─────────────────── | ─ ─ ─ ─ ─ ─   ← 边不对齐 → 裂缝！
```

### 3.2 朴素解法：锁边（Edge Locking）

在简化时锁住 Cluster 的**外边**（boundary edges），确保相邻 Cluster 无论如何简化，共享边都保持 L0 的位置：

**问题**：
1. **面数利用率低**：高 LOD 层的 Cluster 表达大范围几何，但 128 个三角形中很多被锁边"浪费"了
2. **视觉 artifact**：锁边区域的三角形密度与内部不一致，人眼对频率突变极其敏感，会注意到边界

### 3.3 Nanite 解法：Cluster Group（组级简化）

Nanite 的核心创新：

> 不对单个 Cluster 锁边，而是将**若干 Cluster 聚成一个 Group**，**打碎 Group 内部的边界，只锁 Group 的外边**，然后整体简化。

```
L0 的 16 个 Cluster 聚成一个 Cluster Group:
┌─────────────────────────────────────┐
│  [C0][C1][C2][C3]                   │
│  [C4][C5][C6][C7]     外边锁住       │
│  [C8][C9][CA][CB]                   │
│  [CC][CD][CE][CF]  内边全打碎        │
└─────────────────────────────────────┘
          ↓ 整体简化（减半面数）
          ↓ 重新做 Cluster 划分
L1 的 8 个 Cluster（面数减半）
```

**优势**：
- 同样是锁边，但锁的是 Group 外边（三角形数量少得多）
- 内部 2万 个三角形自由简化，利用率高
- 简化效果质量远超单 Cluster 方案

### 3.4 边界 Jitter（随机化）的重要性

**关键设计**：每层 LOD 的 Cluster Group 分组方式不同（不与上一层对齐）。

效果类比：在 Screen Space AO 中对采样半径做 jitter（旋转），使 artifact 无法聚焦成固定 pattern。

```
L0 的 Group 边界（红色）:
  ┌──────┬──────┐
  │  G0  │  G1  │   ← 某些位置锁边
  └──────┴──────┘

L1 的 Group 边界（绿色）:
  ┌───┬──────┬───┐
  │G0'│  G1' │G2'│   ← 边界位置与 L0 不同
  └───┴──────┴───┘
```

由于每层 LOD 的锁边位置不同，LOD 切换时没有固定的"高频缝合线"，人眼无法注意到 LOD 过渡边界。

---

## 4. DAG 结构：有向无环图而非树

### 4.1 为什么是 DAG，不是 Tree

由于 Cluster Group 简化后重新做 Cluster 划分，新的 Cluster 与原来 L0 Cluster 的关系不再是简单的一对一，而是**多对多**：

```
传统树结构（不准确）:
  L1: [A]      [B]
       |        |
  L0: [a1][a2] [b1][b2]

Nanite 实际结构（DAG）:
  L1: [A]              [B]
       /  \           /  \
  L0: [a1][a2]     [a3][b1]
                     ↑
               跨 Group 关联！
```

原因：简化过程以 Cluster Group 为单元，简化后重新划分 Cluster，新 Cluster 可能覆盖原来多个 Group 的区域。

### 4.2 DAG 节点的含义

- 每个节点 = 一个 **Cluster**（约 128 个三角形）
- 每条有向边 = "子 Cluster 的精细化表示"
- **兄弟关系**：同一 Cluster Group 内的 Cluster 是兄弟节点，必须同步切换 LOD

```
Nanite Cluster DAG 示意:
                    ┌─────────────────┐
  L2 (最粗)         │  [CG2_A]        │
                    │  cl_A  cl_B     │
                    └────┬───────┬────┘
                         │       │
                    ┌────┴──┐  ┌─┴────┐
  L1               │[CG1_A]│  │[CG1_B]│
                   │cl_c   │  │cl_e   │
                   │cl_d   │  │cl_f   │
                   └─┬──┬──┘  └──┬──┬─┘
                     │  │        │  │
                   ┌─┴┐┌┴─┐  ┌──┴┐┌┴──┐
  L0 (最精细)      │c0││c1│  │c2 ││c3 │
                   └──┘└──┘  └───┘└───┘
```

**关键约束**：同一 Cluster Group 内的所有 Cluster 在 LOD 选择时必须**同时选相同层级**（要么全选当前层级，要么全用子节点）。

---

## 5. 运行时 LOD 选择：误差度量

### 5.1 误差度量（Error Metric）

每次几何简化（Mesh Simplification）都会引入误差，Nanite 使用 **QEM（Quadric Error Metric，二次误差度量）** 记录每层 Cluster 相对于原始几何的误差：

$$e_i = \text{max}_{v \in \text{Cluster}_i} \|v - v_0\|$$

其中 $v_0$ 是原始 L0 mesh 上对应的最近点，$e_i$ 是该 Cluster 层级的**空间误差**（World Space Error）。

**单调性约束**（Monotonic Error）：

$$e_{\text{parent}} > e_{\text{child}} \quad \forall \text{ levels}$$

父层级的误差**严格大于**子层级，保证 LOD 选择的确定性：不会出现"选了父节点，但某个子节点误差更大"的矛盾情况。

### 5.2 运行时 LOD 选择算法

对于每个 Cluster Group，计算其在当前视图下的**屏幕空间投影误差**：

$$e_{\text{screen}} = \frac{e_{\text{world}}}{d} \cdot \frac{W}{2 \tan(\theta/2)}$$

其中：
- $e_{\text{world}}$：世界空间误差
- $d$：Cluster 到相机的距离
- $W$：屏幕宽度（像素）
- $\theta$：相机垂直视场角

**选择规则**：

```
function select_LOD(cluster_group):
  e_screen = compute_screen_error(cluster_group)
  if e_screen < threshold (通常为 1 subpixel):
    → 使用当前 Cluster Group（足够精细）
  else:
    → 使用子 Cluster Group（需要更精细）
```

### 5.3 Cut Line（切割线）的确定性

由于误差的单调性，LOD 选择可以在 DAG 上确定一条**切割线（Cut Line）**，切割线上下恰好覆盖所有几何区域且无重叠：

```
               [CG2_A]              ← 太粗，e > threshold
              /         \
          [CG1_A]     [CG1_B]      ← 刚好合适（切割线）
          /    \       /    \
        [c0]  [c1]  [c2]  [c3]     ← 不需要到这层
```

---

## 6. Streaming 与显存管理

### 6.1 按需加载策略

利用 LOD 层次结构，Nanite 实现了**几何数据的 Streaming**：

```
初始加载: 只加载 L2/L3 等粗糙 LOD

相机推近时:
  发现 L2 误差 > threshold → 请求 L1 数据
  发现 L1 误差 > threshold → 请求 L0 数据

相机拉远时:
  L0 不再需要 → 释放 L0 数据
```

**显存预算（Memory Budget）**：
- 类比 Virtual Texture 的 clip map 概念
- 在有限显存内维护当前视角所需的几何数据集合
- 超出预算时使用更粗糙的 LOD

---

## 7. 软光栅化（Software Rasterizer）

### 7.1 小三角形的问题

Nanite 的目标是"每像素一个三角形"——这意味着场景中会存在大量**极小三角形**（projected size < 1 pixel）。

硬件光栅化管线对小三角形效率低下：
- 固定的 setup overhead（无论三角形多小都有固定代价）
- 小三角形可能触发 GPU 上不必要的 quad shading overhead

### 7.2 软光栅化实现

对投影面积小于**阈值**的 Cluster，Nanite 在 **Compute Shader** 中实现软光栅化：

```
判断条件（预处理阶段）:
  对每个 Cluster，计算最大投影边长 max_edge:
    max_edge = max(|v1-v0|_screen, |v2-v1|_screen, |v0-v2|_screen)

  if max_edge <= threshold:
    → 走 Software Rasterizer 路径
  else:
    → 走 Hardware Rasterizer 路径
```

**软光栅核心：64-bit Atomic 实现 Early-Z**

传统 early-z 由硬件实现，软光栅需要手动模拟：

```hlsl
// 对每个像素做原子比较并交换
// packed_value = (depth << 32) | (material_id)
uint64_t packed = pack(depth, cluster_id, triangle_id);
InterlockedMax(visibility_buffer[x][y], packed);
```

利用 64-bit atomic max 操作：
- 高 32 bit 存深度（z 越小值越大 → 近处覆盖远处）
- 低 32 bit 存 Cluster ID + Triangle ID

这样一次原子操作同时完成 early-z test 和 visibility 写入。

### 7.3 软/硬光栅化的分工

```
所有 Cluster
     ↓
 投影大小判断
     /      \
  小三角形    大三角形
(< threshold)(>= threshold)
     ↓           ↓
Software     Hardware
Rasterizer   Rasterizer
     \          /
      ↓        ↓
    Visibility Buffer（统一输出）
```

**性能优势**：Nanite 内部统计显示，大量 Cluster（场景中高密度几何）走软光栅化路径，整体性能提升显著。

---

## 8. Visibility Buffer 在 Nanite 中的应用

### 8.1 两 Pass 架构

Nanite 渲染采用 Visibility Buffer 架构：

```
Pass 1: Rasterization Pass (软/硬光栅化)
  输出:
  ┌────────────────────────────────┐
  │ Visibility Buffer              │
  │ 每像素: [ClusterID | TriID]    │
  │ (64-bit packed, depth+id)      │
  └────────────────────────────────┘

Pass 2: Material Evaluation Pass
  For each pixel:
    1. 读 ClusterID + TriID
    2. 查 index buffer → 得到三顶点索引
    3. 读 vertex buffer → 得到三顶点属性
    4. 计算重心坐标 (α, β, γ)
    5. 插值 UV、Normal 等
    6. 采样材质纹理
    7. 执行 Lighting 计算
  输出: Final Color Buffer
```

### 8.2 材质切换的处理

由于 Nanite 场景可以有成百上千种材质，Pass 2 中需要高效处理：

```
方案: 基于 Material ID 的分 Bucket Shading

1. 全屏分析 Visibility Buffer，对每个材质生成 tile mask
2. 每种材质只需在覆盖它的像素上执行 Shader
3. 可以 batch 同材质的像素，提高 cache 效率

  Material A:  ████░░░░████  ← 只在 A 覆盖的像素执行 A 的 Shader
  Material B:  ░░░░████░░░░  ← 同理
```

### 8.3 与 G-Buffer 方案的对比

```
                G-Buffer                    Visibility Buffer (Nanite)
Pass 1         写 Albedo/Normal/Roughness   写 ClusterID+TriangleID (极轻量)
               (带宽大)                     (带宽小)

overdraw 代价  每次覆写都采样材质            只写 packed int，无纹理采样
               (O(overdraw))               (O(1) atomic op)

Pass 2         直接读 G-Buffer 做 Lighting  重建 attributes → 采样材质 → Lighting
               (简单)                      (重建有额外计算，但总代价更低)

适合场景       低 overdraw（建筑内部等）     任意场景，尤其是高 overdraw（植被等）
```

---

## 9. Shadow 裁剪策略

### 9.1 Shadow 的挑战

Nanite 场景的高精度几何带来了 Shadow 渲染的挑战：从光源角度也需要渲染同等复杂度的几何体。

对应方案：**Virtual Shadow Map（虚拟阴影贴图）**

### 9.2 Shadow Caster 裁剪

在城市场景中，大量几何体对 shadow 的贡献可以被提前裁剪：

**方案一：低分辨率采样预判断**

```
用 64×64 低分辨率纹理采样:
  从光源方向粗略判断哪些区域会被投影
  只有在该区域内的 Caster 才需要参与 Shadow Map 渲染
```

**方案二：相机空间体积裁剪**

```
Shadow Volume Culling:
  计算 shadow 可能影响到的相机可见区域
  只渲染那些位于"相机视锥 + 光源方向延伸体"内的物体

  ┌───────────────────────┐
  │     Camera Frustum    │
  │   ╲               ╱  │
  │    ╲             ╱   │← Shadow Volume
  │     ╲           ╱    │
  │      ╲_________╱     │
  └───────────────────────┘
  只有在此体积内的 Caster 才可能产生可见阴影
```

**方案三：重用上一帧 Shadow Map**

对于静止几何体（城市建筑等），上一帧的 Shadow Map 可以直接复用，只对动态物体（角色、粒子）重新渲染。

---

## 10. 关键术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| **虚拟几何** | Virtual Geometry | Nanite 的核心概念，按需流式加载和渲染几何体 |
| **簇组** | Cluster Group | 若干相邻 Cluster 组成的简化单元，是 Nanite LOD 的基本管理粒度 |
| **有向无环图** | DAG (Directed Acyclic Graph) | Nanite 中 Cluster 层次关系的数据结构，非树形 |
| **切割线** | Cut Line | 在 DAG 上确定的一条分界线，其上的 Cluster 组合覆盖完整几何且无重叠 |
| **二次误差度量** | QEM (Quadric Error Metric) | 量化 Mesh 简化误差的方法 |
| **投影误差** | Screen-Space Error | 将世界空间误差投影到屏幕空间后的大小（单位：像素） |
| **单调误差** | Monotonic Error | 每层 LOD 误差严格递增的约束，保证 LOD 选择的确定性 |
| **软光栅化** | Software Rasterizer | 在 Compute Shader 中实现的三角形光栅化，专用于小三角形 |
| **边锁** | Edge Locking | 在简化时固定 Cluster/Group 外边的顶点位置，防止裂缝 |
| **裂缝** | Crack / Seam | LOD 切换时相邻 Cluster 边不对齐产生的视觉空洞 |
| **水密性** | Watertight | 相邻几何体共享边的顶点完全对齐，无裂缝 |
| **水管级联** | Streaming | 按需加载几何数据，远处用粗糙 LOD，近处流式加载精细 LOD |
| **虚拟阴影贴图** | Virtual Shadow Map | 与 Nanite 配合使用的大规模高精度阴影系统 |
| **遮挡体** | Occluder | 用于遮挡测试的大型几何体 |
| **子像素精度** | Subpixel Accuracy | 投影误差小于一个像素，视觉上无法察觉与原始几何的差异 |

---

## 11. 总结

### Nanite 核心技术栈

```
Nanite 技术体系:
┌─────────────────────────────────────────────────────────────┐
│                    Nanite Pipeline                          │
│                                                             │
│  离线预处理:                                                 │
│  Mesh → Cluster → Cluster Group → 简化 → DAG              │
│                                                             │
│  运行时:                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐ │
│  │ LOD 选择      │  │ 剔除          │  │ 光栅化           │ │
│  │ (误差 + 距离) │  │ (Frustum +   │  │ (小三角形:软光栅 │ │
│  │              │  │  HZ-Occlusion)│  │  大三角形:硬件)  │ │
│  └──────────────┘  └───────────────┘  └──────────────────┘ │
│                              ↓                              │
│                    Visibility Buffer                        │
│                              ↓                              │
│                 Material Evaluation Pass                    │
│                 (重建 Attributes + Shading)                  │
└─────────────────────────────────────────────────────────────┘
```

### 关键创新点

| 创新 | 传统方案 | Nanite 方案 |
|------|---------|------------|
| LOD 粒度 | 整个实例切换一个 LOD | 每个 Cluster 独立选择 LOD |
| LOD 边界 | 单 Cluster 锁边（浪费三角形，有 artifact）| Cluster Group 整体简化（高利用率，边界 jitter）|
| 层次结构 | BVH 树（树形，一对一）| DAG（多对多，更准确） |
| 小三角形 | 硬件光栅化（overhead 高）| 软光栅化（64-bit atomic，无 setup 代价）|
| 着色方式 | G-Buffer（overdraw 代价高）| Visibility Buffer（overdraw 代价为 O(1)）|

### 性能特征

- **三角形绘制数**：约等于屏幕像素数（1080p 约 200 万三角形）
- **场景几何量**：可处理亿级三角形场景（通过 Streaming）
- **LOD 切换**：无 popping（无感知过渡），因为 jitter 使过渡边界不固定
- **适用限制**：Nanite 不适用于蒙皮动画（骨骼动画角色）、需要形变的几何体

### Nanite 与 Lumen 的配合

Unreal Engine 5 中，Nanite（几何）与 Lumen（全局光照）共同构成新一代渲染基础设施：

```
Nanite          →   提供高精度几何表示
Lumen           →   提供高质量动态全局光照
Virtual Shadow Map → 提供高质量阴影（配合 Nanite 几何密度）
```

三者相互依存，共同实现 UE5 的"电影级实时渲染"愿景。

### Nanite 技术的历史地位

Nanite 代表了实时渲染史上的一次范式转变：

- 2015 年：刺客信条大革命提出 **GPU Driven + Cluster Based** 概念
- 2021 年：UE5 Nanite 将其发展为 **Virtual Geometry**，实现了业界长期追求的目标

> 作者（Brian Karis 等）在 GDC/SIGGRAPH 的原始演讲 *"A Deep Dive into Nanite"* 是理解这一技术的权威参考。
