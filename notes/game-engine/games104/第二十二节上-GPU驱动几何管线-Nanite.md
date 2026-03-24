# GAMES104 第二十二节（上）：GPU 驱动的几何管线

> 本节是 GAMES104 游戏引擎课程的最后一讲，主题是现代 GPU 驱动渲染管线与 Nanite 技术基础。内容涵盖传统管线的瓶颈、Cluster-Based Rendering、Indirect Draw、多级裁剪与遮挡剔除、可见性缓冲（Visibility Buffer）等核心技术。

---

## 目录

1. [传统渲染管线的瓶颈](#1-传统渲染管线的瓶颈)
2. [GPU Driven Rendering 的曙光](#2-gpu-driven-rendering-的曙光)
3. [Cluster-Based Rendering](#3-cluster-based-rendering)
4. [多级裁剪与 Index Buffer Compaction](#4-多级裁剪与-index-buffer-compaction)
5. [遮挡剔除与 HZ-Buffer](#5-遮挡剔除与-hz-buffer)
6. [Visibility Buffer（ID 缓冲）](#6-visibility-bufferid-缓冲)
7. [关键术语表](#7-关键术语表)
8. [总结](#8-总结)

---

## 1. 传统渲染管线的瓶颈

### 1.1 传统渲染流程概览

传统渲染管线以 **CPU** 为主导：每帧 CPU 准备所有渲染所需参数，逐物体发起 `Draw Primitive` 指令，再由 GPU 执行顶点着色、光栅化、像素着色。

```
  CPU                                  GPU
  ┌─────────────────────────────┐      ┌──────────────────────────────┐
  │  场景遍历                    │      │  Vertex Shader               │
  │  可见性剔除 (Frustum Cull)   │      │  Rasterization               │
  │  LOD 选择                   │ ──→  │  Pixel Shader                │
  │  设置 Render State           │      │  Output Merger               │
  │  Draw Primitive × N         │      │                              │
  └─────────────────────────────┘      └──────────────────────────────┘
              CPU Bound                       GPU Bound
```

### 1.2 瓶颈分析

| 问题 | 说明 |
|------|------|
| **Draw Call 开销** | 每次 Draw Primitive 都需要完整的管线切换，即使只画一个三角形代价也相同 |
| **Render State 切换** | 切换材质、纹理、着色器时需重新设置大量状态，极其昂贵 |
| **CPU-GPU 数据传输** | 可见性、LOD 等计算结果需要从 CPU 内存传到 GPU 显存 |
| **CPU render thread 饱和** | CPU 忙于准备绘制命令，游戏逻辑（AI、物理、网络）受到挤压 |

对于现代 3A 游戏场景（例如《刺客信条：大革命》），场景中有：
- 上亿面片级别的几何体
- 每帧上万个需要独立渲染的物体
- 上千种不同材质

这些都导致传统管线在如此高复杂度下**无法高效运行**。

---

## 2. GPU Driven Rendering 的曙光

### 2.1 技术基础

两个关键技术支撑了 GPU Driven 管线的可行性：

**（1）Compute Shader 成熟**

Compute Shader 允许在 GPU 上执行任意通用计算，不再局限于图形管线固定阶段：

- 可见性剔除 (Visibility Culling)
- LOD 选择 (LOD Selection)
- 视锥裁剪 (Frustum Culling)
- 遮挡剔除 (Occlusion Culling)

以上全部可在 GPU 内部完成，无需 CPU 参与。

**（2）Indirect Draw API**

现代图形 API (DirectX 12, Vulkan) 支持 **Indirect Draw**：

```
传统做法:
  CPU 遍历每个物体 → CPU 设置参数 → CPU 发 Draw Call × N

Indirect Draw:
  CPU 发一条指令 → GPU 从 parameter buffer 自行读取参数 → GPU 执行 N 个绘制
```

参数缓冲（parameter buffer / indirect buffer）结构：

```
┌─────────────────────────────────────────┐
│  [DrawArgs0] [DrawArgs1] ... [DrawArgsN] │
│  每项包含: IndexCount, InstanceCount,   │
│           StartIndex, BaseVertex, etc.  │
└─────────────────────────────────────────┘
         ↑ GPU 读取，无需 CPU 干预
```

### 2.2 GPU Driven Rendering 理想形态

```
  CPU                    GPU (Compute)              GPU (Render)
  ┌──────────────┐      ┌──────────────────────┐   ┌────────────────┐
  │ 设置相机参数  │      │ 实例可见性剔除        │   │                │
  │ 发一条       │ ──→  │ Cluster 可见性剔除    │   │ 一个 Draw Call │
  │ Dispatch     │      │ LOD 选择             │   │ 绘制所有可见几何│
  │              │      │ Index Buffer 压缩    │──→│                │
  └──────────────┘      └──────────────────────┘   └────────────────┘
    CPU 基本空闲              GPU 全权处理
```

**好处**：
- CPU 被释放，专注游戏逻辑
- GPU 信息完整，并行度充分发挥
- 大幅减少 CPU-GPU 同步点

---

## 3. Cluster-Based Rendering

### 3.1 核心思想

以《刺客信条：大革命》（Assassin's Creed: Unity，SIGGRAPH 2015）为例，这是 GPU Driven 渲染管线的里程碑式实践。

**Cluster（簇）** 的定义：

> 将一个 mesh 切割成由固定数量三角形（通常 **64 或 128 个三角形**）构成的小片，称为 Cluster（也称 Meshlet）。

```
一个复杂 Mesh (如建筑):
┌──────────────────────────────────────────────┐
│  [C0][C1][C2][C3][C4][C5][C6][C7][C8][C9]... │
│  每个 Ci = 64~128 个三角形                    │
│  每个 Ci 有独立的 Bounding Box                │
└──────────────────────────────────────────────┘
```

### 3.2 Chunk 的引入

若干 Cluster 组成一个 **Chunk**（通常 32 个 Cluster / Chunk）。

原因：**GPU wave（warp）大小对齐**
- NVIDIA GPU：一个 warp = 32 线程
- AMD GPU（旧版）：一个 wavefront = 64 线程

将 Chunk 大小与 wave 大小对齐，使 Compute Shader 中批处理效率最高：

$$\text{Chunk 大小} = \text{GPU Wave 大小} = 32 \text{ (NVIDIA)}$$

### 3.3 View-Dependent LOD 选择

相比传统 LOD（整个实例只能有一个 LOD Level），Cluster-Based 方法实现了：

> **每个 Cluster 独立选择 LOD Level**

对于龙（2400 万三角形）的例子：
- 靠近相机的部分 → 使用精细 Cluster（高 LOD）
- 远离相机的部分 → 使用粗糙 Cluster（低 LOD）
- 最终只需绘制约 **1/30** 的三角形

这在刺客信条的方案里，每个实例的 LOD 仍是整体切换的；Nanite 将其进化到每个 Cluster 独立切换（后文 下节 详述）。

---

## 4. 多级裁剪与 Index Buffer Compaction

### 4.1 四级裁剪流程

GPU Driven 管线中，裁剪分四个精细层次：

```
Level 1: Instance 裁剪
         ┌──────────┐
         │ 视锥剔除  │ ← CPU 做粗略剔除，GPU 做精细剔除
         └──────────┘
              │
Level 2: Chunk 裁剪
         ┌──────────┐
         │ 视锥+深度 │ ← 利用 HZ-Buffer 做遮挡测试
         └──────────┘
              │
Level 3: Cluster 裁剪
         ┌──────────────────────────┐
         │ 每个 Cluster 独立做       │
         │ · Frustum Culling        │
         │ · Occlusion Culling      │
         │ · Back-face Culling      │
         └──────────────────────────┘
              │
Level 4: Triangle 裁剪
         ┌──────────────┐
         │ 背面三角形剔除 │
         └──────────────┘
```

### 4.2 Index Buffer Compaction

所有可见三角形的 Index 被打包写入一个**超大 Index Buffer**：

```
Step 1: 预分配大 Index Buffer (约 8MB)

Step 2: GPU Compute Shader 并行遍历
        For each Instance:
          For each Chunk:
            For each Cluster:
              For each Triangle:
                if visible:
                  atomic_add(&offset, 3)  // 原子加，确保偏移唯一
                  write indices to buffer[offset]

Step 3: 一次 Indirect Draw 将整个 Index Buffer 渲染完
```

**注意点：写入顺序不确定（乱序写入）**

由于并行写入，不同帧间绘制顺序可能不同，当几何密度很高时可能产生 **Z-Fighting**。解决方案：
- 使用硬件厂商提供的 `MultiDrawIndirect` 锁定绘制顺序
- 保证绘制 deterministic，避免帧间闪烁

### 4.3 Back-Face Culling 的 Cube 加速

对每个 Cluster 预计算一个 **Cone（法锥）表**：

- 64 个三角形可能的朝向，映射到一个 Cube 的 6 个面
- 每面对应 64-bit 的可见性 bitmap
- 给定相机方向，直接查表得到哪些三角形正面朝向相机

$$\text{可见性 mask} = \text{面片可见性表}[\text{相机方向}] \cap \text{法线朝向}$$

---

## 5. 遮挡剔除与 HZ-Buffer

### 5.1 问题：Occlusion Culling 的重要性

若没有遮挡剔除，游戏帧率会大幅下降（通常数个量级）。城市场景中，大量几何体被建筑物遮挡，必须裁剪。

### 5.2 Hierarchical Z-Buffer（层次深度缓冲）

**HZ-Buffer** 是对 Depth Buffer 建立多级 Mipmap，每级存储对应区域的**最小深度**（最近距离）：

```
Depth Buffer (1920×1080)
     ↓ 取最大值（最远 z）
Mip1 (960×540)
     ↓ 取最大值
Mip2 (480×270)
     ↓
...
```

> 注：这里取的是 **最大 Z**（NDC 中远处 z 值更大），用于保守遮挡：若物体的深度 > HZ-Buffer 对应层级的值，则确定被遮挡。

保守遮挡测试：

$$\text{if } z_{\text{cluster\_min}} > z_{\text{HZ}}[\text{level}] \Rightarrow \text{Cluster 被遮挡，剔除}$$

### 5.3 深度重投影（Depth Reprojection）

上一帧的 Depth Buffer 可以重投影到当前帧相机空间，作为当前帧 HZ-Buffer 的初始填充：

```
上一帧 Depth Buffer
       ↓
   重投影变换:
   P_world = unproject(x_prev, y_prev, z_prev)
   P_cur   = project(P_world, camera_cur)
       ↓
当前帧 HZ-Buffer 初始值
```

**有效性前提**：
1. 相机运动平滑（两帧差异不大）
2. 场景中大量物体静止

### 5.4 启发式遮挡体选择（Heuristic Occluder Selection）

第一帧无历史数据时的冷启动策略：

1. 选取**少量最大、最近的物体**作为遮挡体（Occluder）先渲染
2. 建立初步 HZ-Buffer
3. 对剩余所有物体做遮挡测试

流程：

```
Phase 1: 渲染 Top-K 遮挡体（大体积 + 靠近相机）
          ↓
         建立 HZ-Buffer
          ↓
Phase 2: 对所有其他 Cluster 做遮挡测试
          ↓
         通过测试的 Cluster → 加入 Visible List
          ↓
Phase 3: 一次 Indirect Draw 绘制所有可见 Cluster
```

---

## 6. Visibility Buffer（ID 缓冲）

### 6.1 G-Buffer 的问题

传统 Deferred Rendering 使用 G-Buffer：

```
Pass 1 (Geometry Pass):
  每个像素写入:
    · Albedo
    · Normal
    · Roughness / Metallic
    · Depth
    ← 大量带宽消耗

Pass 2 (Lighting Pass):
  读取 G-Buffer 做 Lighting 计算
```

**问题**：当场景中有大量植被（草、树叶），发生严重的 **overdraw**（同一像素被多个三角形覆盖），每次覆盖都需要采样多张纹理，极其昂贵。

| 场景类型 | G-Buffer 表现 |
|---------|--------------|
| 建筑内部（低 overdraw）| 尚可 |
| 开阔草原（高 overdraw）| 极差（大量无效纹理采样）|

### 6.2 Visibility Buffer 方案

**第一 Pass：仅写 Visibility（ID Buffer）**

```
每个像素只存储:
  · Instance ID  (16 bits)
  · Cluster ID   (16 bits)
  · Triangle ID  (16 bits)
  共 48 bits，远小于 G-Buffer
```

**第二 Pass：重建 Attributes 并 Shading**

```
For each pixel (u, v):
  1. 读取 Visibility Buffer → 得到 Instance/Cluster/Triangle ID
  2. 从 Index Buffer 读取三顶点的世界坐标
  3. 计算重心坐标 (barycentric coordinates):
     (α, β, γ) such that α+β+γ=1
  4. 插值所需 attributes:
     UV = α·UV₀ + β·UV₁ + γ·UV₂
     Normal = α·N₀ + β·N₁ + γ·N₂
  5. 采样纹理，做 Lighting 计算
```

**优势**：
- 每个像素只做**一次**纹理采样（基于最终可见的三角形）
- 无论场景 overdraw 多严重，Shading 代价只与屏幕像素数成正比

```
         G-Buffer 方案              Visibility Buffer 方案
         ┌─────────────┐           ┌────────────────────┐
overdraw │ 纹理采样 × N │           │ 写 ID (极便宜) × N  │
时的代价  │  (N 次覆写)  │    vs.    │                    │
         └─────────────┘           │ 最终 Shading × 1   │
                                   └────────────────────┘
         随 overdraw 线性增长         与 overdraw 无关
```

---

## 7. 关键术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| **绘制调用** | Draw Call / Draw Primitive | CPU 发起的 GPU 绘制指令 |
| **间接绘制** | Indirect Draw | GPU 从 parameter buffer 自行读取绘制参数，无需每次 CPU 干预 |
| **参数缓冲** | Parameter Buffer / Indirect Buffer | 存放多个绘制指令参数的 GPU Buffer |
| **计算着色器** | Compute Shader | 用于在 GPU 上执行通用计算的可编程着色阶段 |
| **簇** | Cluster / Meshlet | 由固定数量（64-128）三角形构成的最小几何单元 |
| **块** | Chunk | 若干 Cluster 组成的分组，对应 GPU wave 大小 |
| **视锥裁剪** | Frustum Culling | 剔除相机视锥之外的物体/簇 |
| **遮挡剔除** | Occlusion Culling | 剔除被其他几何体遮挡的物体/簇 |
| **层次深度缓冲** | HZ-Buffer / Hierarchical Z | Depth Buffer 的多级 Mipmap，用于快速遮挡测试 |
| **深度重投影** | Depth Reprojection | 将上一帧 depth buffer 变换到当前帧相机空间重用 |
| **索引缓冲压缩** | Index Buffer Compaction | 将所有可见三角形的索引打包成连续 buffer |
| **可见性缓冲** | Visibility Buffer / ID Buffer | 每像素只存 InstanceID+ClusterID+TriangleID |
| **G 缓冲** | G-Buffer | Deferred Rendering 中存储几何信息的多张纹理 |
| **重心坐标** | Barycentric Coordinates | 三角形内任意点表示为三顶点的加权平均 |
| **波/线程束** | Wave / Warp | GPU 上一次调度执行的一批线程（NVIDIA 32，AMD 64） |
| **原子操作** | Atomic Operation | 并行写入时保证数据一致性的不可分割操作 |
| **Z 冲突** | Z-Fighting | 两个深度相近的面片交替遮挡对方，产生闪烁 |

---

## 8. 总结

本节（上）系统介绍了从传统管线走向 GPU 驱动管线的演进逻辑：

### 核心演进路线

```
传统 CPU-Driven 管线
    │  瓶颈: Draw Call 过多、CPU 负载过重
    ▼
Compute Shader + Indirect Draw
    │  基础设施: GPU 可自主执行通用计算和批量绘制
    ▼
Cluster-Based Rendering（刺客信条大革命，2015）
    │  精细化: 将几何细分为 Cluster，以 Cluster 为粒度做裁剪
    ▼
多级裁剪 + Index Buffer Compaction
    │  高效性: 4级裁剪 → 只提交可见三角形 → 一次 Draw
    ▼
HZ-Buffer 遮挡剔除 + 深度重投影
    │  遮挡处理: 重用历史帧深度，保守遮挡测试
    ▼
Visibility Buffer
    │  Shading 效率: 解耦 visibility 与 shading，消除 overdraw 代价
    ▼
以上所有技术共同构成 Nanite 的基础（详见下节）
```

### 性能数据参考

- **刺客信条大革命**：上亿面片场景，通过 GPU Driven 方案在 PS4 时代实现实时渲染
- **Cluster 大小**：64~128 三角形/Cluster 是工程经验值，过小则管理开销大，过大则裁剪精度差
- **HZ-Buffer 效果**：遮挡剔除有效时，去掉该功能场景帧率可能下降数个量级

### 关键设计哲学

> 从 `Draw Primitive` 到 `Dispatch Compute`：
> 让 GPU 自己决定渲染什么，CPU 只需提供场景描述和相机参数。
