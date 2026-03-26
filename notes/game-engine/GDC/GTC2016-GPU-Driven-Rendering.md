# GTC 2016: GPU-Driven Rendering 技术笔记

> 来源：NVIDIA GTC 2016 讲座《GPU-Driven Rendering》
> 讲师：Pierre（硬件架构专家）及另一位 NVIDIA 工程师
> 内容涵盖：GPU 硬件架构、图形流水线、GPU 驱动渲染（Multi-Draw Indirect、GPU Culling、MDI）

---

## 目录

1. [背景与动机](#1-背景与动机)
2. [GPU 硬件架构概述](#2-gpu-硬件架构概述)
3. [图形流水线：一个三角形的生命周期](#3-图形流水线一个三角形的生命周期)
4. [延迟与吞吐量分析](#4-延迟与吞吐量分析)
5. [Draw Call 处理与状态机](#5-draw-call-处理与状态机)
6. [GPU 驱动渲染（GPU-Driven Rendering）](#6-gpu-驱动渲染gpu-driven-rendering)
7. [数据传输与内存优化](#7-数据传输与内存优化)
8. [Warp 与线程发散](#8-warp-与线程发散)
9. [着色器优化策略](#9-着色器优化策略)
10. [内存缓冲区类型选择](#10-内存缓冲区类型选择)
11. [遮挡剔除与 LOD](#11-遮挡剔除与-lod)
12. [几何着色器 vs 细分着色器](#12-几何着色器-vs-细分着色器)
13. [实践建议汇总](#13-实践建议汇总)

---

## 1. 背景与动机

### 1.1 从 CPU 瓶颈到 GPU 瓶颈

在早期 GPU 时代，OpenGL 允许逐顶点地将数据推入图形硬件。随着场景复杂度增加，CPU 成为 GPU 的瓶颈：

```
历史演进：

早期 GL       →  每顶点单独推入硬件（简单但慢）
             ↓  场景复杂度增加
CPU 瓶颈时代  →  CPU 跟不上 GPU 速度
             ↓  API 演进
现代 API      →  Multi-Draw Indirect, NVIDIA Bindless,
               Command List Extensions（大幅降低 CPU 开销）
             ↓  未来方向
GPU 驱动渲染  →  GPU 自己产生 Draw Call、决策 LOD、
               剔除、动画驱动
```

### 1.2 本次讲座关注点的转变

过去几年一直在展示如何克服 CPU 瓶颈（大场景、大量物体、材质、几何体）。本年度的重点转移：

- **今年目标**：研究 GPU 瓶颈，改进整个渲染系统，而不只是调优单个着色器
- **同时涵盖**：如何写更高效的着色器 + 硬件架构实际如何工作

### 1.3 GPU 驱动渲染的能力展示

讲师展示了使用 Multi-Draw Indirect 的几个示例：

| 效果 | 描述 |
|------|------|
| 自适应细分渲染（绿色球体） | GPU 自主决定使用自适应曲面细分 |
| 简单网格（青色球体）       | 中等细节，直接使用网格渲染 |
| 点精灵（背景红点）         | GPU 自主决定使用 point sprite |
| GPU 驱动动画               | 所有决策留在 GPU 上，最小化延迟 |
| 距离场渲染（SDF）          | 完全不使用三角形，像素着色器内光线步进 |

> **核心思想**：当 GPU 变得更可编程时，不仅仅是在着色，而且在整个决策流程中，GPU 可以自主创建和管理 Draw Call。

---

## 2. GPU 硬件架构概述

### 2.1 GPU 芯片结构（以 GM200/Maxwell 为例）

```
┌──────────────────────────────────────────────────────┐
│                       GPU Die                         │
│                                                       │
│  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐  │
│  │  GPC  │ │  GPC  │ │  GPC  │ │  GPC  │ │  GPC  │  │
│  │(SM×n) │ │(SM×n) │ │(SM×n) │ │(SM×n) │ │(SM×n) │  │
│  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘  │
│                                                       │
│           ┌──────────────────┐                        │
│           │  ROP Units       │  ← 颜色混合 & 深度     │
│           └──────────────────┘                        │
│                                                       │
│  ┌───────────────────────────────────────────────┐   │
│  │              L2 Cache                         │   │
│  └───────────────────────────────────────────────┘   │
│                                                       │
│  ┌───────────────────────────────────────────────┐   │
│  │           Frame Buffer (DRAM)                  │   │
│  └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

主要单元：

- **GPC（Graphics Processing Cluster）**：图形处理集群，GM200 有 6 个，每个 GPC 包含多个 SM
- **SM（Streaming Multiprocessor）**：流式多处理器，包含 CUDA Core（最常见的可编程单元）
- **ROP（Raster Output Unit）**：光栅输出单元，负责颜色混合和深度写入
- **前端（Front End）**：从系统内存读取命令缓冲区（push buffer），解析命令

### 2.2 固定功能单元 vs 可编程单元

| 类型 | 代表单元 | 作用 |
|------|---------|------|
| 可编程（Programmable） | CUDA Core / SM | 顶点着色、像素着色、计算 |
| 固定功能（Fixed Function） | Rasterizer、ROP、Vertex Fetch | 光栅化、颜色混合、顶点获取 |

**固定功能单元的价值**：

- 对于特定操作（如光栅化），固定功能实现比 SM 上的通用代码更高效
- 可以把它们看作**免费资源**——只要其他单元是瓶颈，固定功能单元就在并行工作
- 随着产品线不同，单元数量会调整（高端保留全部，低端裁减部分）

### 2.3 负载均衡与反压机制

GPU 内部各单元之间通过 FIFO 队列（Work Queue）连接：

```
来自前端的工作
      ↓
┌─────────────┐
│ Primitive   │  ← 分发原语
│ Distributor │
└──────┬──────┘
       │
  ┌────┴────┐
  │  Work   │    ← 公共队列，管理顶点/像素负载平衡
  │  Queue  │
  └────┬────┘
       │
  ┌────┴────────────────┐
  │   SM Pool           │  ← 顶点和像素 Warp 分布到 SM
  └─────────────────────┘
       │
  ┌────┴────┐
  │  ROP    │   ← 光栅操作
  └─────────┘
```

**反压（Back Pressure）原理**：

当下游单元（如 ROP）忙碌时，会向上游施加反压，上游单元停止产生新工作。这确保了整个管线的有序运转，但同时意味着：**任何单元成为瓶颈，其他所有单元都在等待。**

### 2.4 多政权（Regime）现象

实际渲染帧往往呈现一系列不同的"政权"（Regime）：

```
时间轴：
[阴影图渲染] → [深度预处理] → [计算更新] → [主渲染] → [后处理]
  ROPbound      Frontbound      Compute       Pixel       ...
```

每个政权受到不同单元限制，优化时需要针对每个政权中的瓶颈单元进行优化，而不是全局调优。

---

## 3. 图形流水线：一个三角形的生命周期

### 3.1 总体流程

```
CPU 调用 Draw         →  Driver 写入 Push Buffer
                         ↓
前端（Front End）     →  从 PCIe 读取命令（高延迟）
                         ↓
工作分发器            →  从 Index Buffer 获取索引，
（Work Distributor）      分配顶点给各 SM
                         ↓
顶点着色（Vertex Shader） → 空间变换（World Space）
                         ↓
（可选）细分着色（Tessellation）
                         ↓
视口变换（Viewport Transform）
                         ↓
光栅化（Rasterization） → 世界空间 → 屏幕空间
                          分配到各光栅化器
                         ↓
像素着色（Pixel Shader）
                         ↓
光栅操作（ROP）         → 深度测试 + 颜色混合
                         ↓
写入帧缓冲区（Frame Buffer）← 带压缩
```

### 3.2 世界空间 vs 屏幕空间的分工

**重要区别**：

| 阶段 | 空间 | 分配方式 |
|------|------|---------|
| 顶点着色 | 世界/裁剪空间 | 按三角形分配到 SM，无屏幕限制 |
| 像素着色 | 屏幕空间 | 按屏幕区域分配到 SM（有物理位置限制） |

这一区别可以通过渲染调试颜色来验证：
- 顶点着色阶段按 SM ID 上色 → 颜色分布无屏幕空间规律
- 像素着色阶段按 SM ID 上色 → 颜色呈现明显的屏幕空间瓦片分布

### 3.3 Warp 与顶点缓存复用

顶点分配器创建 **Warp**（一批 32 个线程的工作单元）。当使用 indexed draw call 时：

- 顶点缓存（Vertex Cache）会缓存已变换的顶点
- 若同一顶点被多个三角形共用，可复用缓存结果（避免重复变换）
- 最坏情况：独立三角形列表（triangle list）中每个顶点被使用 1/6 次（6 个索引 = 2 个三角形共用 4 顶点，理论最优为 6:4），实践中复用率可观

**顶点 Warp 大小**：
- 每个 Warp = 32 个线程
- 对于顶点着色，32 线程最多处理 32 个顶点
- 对于三角形，32 个顶点最多形成约 10 个三角形（受共享边影响）

### 3.4 光栅化阶段

光栅化器分配了特定的**屏幕区域**（Tile）。每个光栅化器看到所有影响其负责区域的三角形：

```
屏幕
┌──────┬──────┬──────┐
│ R0   │ R1   │ R2   │  ← 每个区域对应一个光栅化器
├──────┼──────┼──────┤
│ R3   │ R4   │ R5   │
└──────┴──────┴──────┘

大三角形跨越多个区域 → 分配给多个光栅化器并行处理
```

**三角形快速拒绝**：在进入完整光栅化之前，先做粗粒度测试：
1. 背面剔除
2. 视锥体剔除
3. Hiz（Hierarchical Z）测试（在深度缓冲区中快速拒绝整块区域）

### 3.5 像素着色的 Quad（四像素组）

像素着色以 **2×2 的 Quad** 为最小处理单元。这是为了支持纹理采样时的偏导数计算：

$$\frac{\partial u}{\partial x} \approx u(x+1, y) - u(x, y)$$

$$\frac{\partial v}{\partial y} \approx v(x, y+1) - v(x, y)$$

即使三角形只覆盖了 Quad 中的 1 个像素，仍需启动整个 2×2 的线程组（另 3 个为 **Helper Pixel**，负责梯度计算但不写入结果）：

```
例子：三角形只覆盖右下角 1 像素

┌──────┬──────┐
│ 辅助  │ 辅助  │
│(死)   │(死)   │
├──────┼──────┤
│ 辅助  │ ●    │  ← 只有这个像素真正输出
│(死)   │(活)  │
└──────┴──────┘

四个线程都会执行纹理采样指令，但辅助像素不写入帧缓冲区
```

**性能影响**：小三角形（亚像素三角形）会产生大量 Helper Pixel，效率极低。

### 3.6 光栅操作（ROP）与帧缓冲压缩

ROP 阶段负责：
1. **深度测试**（可提前到像素着色器之前——Early-Z）
2. **颜色混合**（Alpha Blending）
3. **重排序**（Re-Order Buffer）：像素着色器乱序完成，ROP 保证按正确顺序写入
4. **内存压缩**（Color Compression、Delta Color Compression）

**深度缓冲区压缩技术**：
- 芯片上维护一份 **Hi-Z**（分层 Z）数据结构，提供块级别的快速深度拒绝
- Maxwell 改进了颜色压缩（Delta Color Compression）

**内存压缩最佳实践**：
- 大三角形覆盖整块区域时，压缩效率高
- 小三角形散布写入时，压缩效率低（每块数据太稀疏）

---

## 4. 延迟与吞吐量分析

### 4.1 GPU 高吞吐量的实现原理

GPU 的高吞吐量并非靠低延迟，而是靠**延迟隐藏（Latency Hiding）**：

当一个 Warp 等待内存访问时，调度器切换到另一个 Warp 继续执行。这要求足够多的在飞 Warp（In-flight Warps）来填充等待时间。

### 4.2 延迟层级（参考数量级）

> 注意：以下数字为量级参考，不同 GPU 代际和产品线有差异。

| 操作 | 延迟（近似周期数） |
|------|-----------------|
| PCI Express（首个命令）| 数千周期 |
| 首次 Draw Call 上 GPU | ~1000 周期 |
| 顶点获取（命中缓存） | ~几百周期 |
| 顶点变换（简单矩阵乘） | 几百周期（类似顶点获取） |
| 纹理采样（L1 命中）| ~100 周期 |
| 纹理采样（L2 命中）| ~200 周期 |
| 纹理采样（DRAM 命中）| ~500+ 周期 |
| DRAM（忙碌时，等待页面切换）| 更长 |

**关键洞察**：顶点数学计算（几个点积）的代价可能比顶点属性获取更便宜。即"计算是免费的，获取数据才是瓶颈"。

### 4.3 GPU 利用率的 Ramp-Up 与 Ramp-Down

每当 GPU 遇到一个 **Wait GPU Idle**（全局屏障）时：

```
利用率
 100% ─────────────────────────────
      /                              \
     /   ← Ramp Up（启动延迟）        \  ← Ramp Down（排空延迟）
    /                                  \
  0%─────────────────────────────────────→ 时间

```

- **Ramp Up**：基于命令获取延迟（PCIe + 管线填充）
- **Ramp Down**：取决于当前最长的在飞任务有多长（例如有个着色器需要 10 万周期）

**结论**：频繁插入 `glMemoryBarrier` / Vulkan Pipeline Barrier / DX12 Barrier 代价极高，应尽量减少全局屏障数量。

---

## 5. Draw Call 处理与状态机

### 5.1 Draw Call 的处理路径

```
CPU 调用 glDraw*() 或 vkCmdDraw*()
      ↓
Driver（CPU 代码）将参数打包到 Push Buffer：

Push Buffer 结构：
┌─────────────────────────────────────────┐
│  Header（Token）: DRAW_INDEXED_COMMAND  │
│  Param: index_count = 5000             │
│  Param: instance_count = 1             │
│  Param: first_index = 0                │
│  Param: vertex_offset = 0              │
│  Param: first_instance = 0             │
│  State: pipeline state, descriptors... │
└─────────────────────────────────────────┘
      ↓
Kernel 将 Push Buffer 指针提交给 GPU
      ↓
GPU Front End 通过 PCIe 读取命令块（高延迟首包）
      ↓
Front End 解析 Token → 触发工作分发
```

### 5.2 状态变更的 GPU 代价

状态变更不仅有 CPU 代价，在 GPU 端也有处理成本：

| 状态类型 | GPU 处理代价 |
|---------|------------|
| 简单状态（视口、混合因子） | 1 周期，可快速过滤 |
| 着色器切换（Shader Switch） | 较高：需解析寄存器数量、输入布局、VS-PS 链接信息等 |
| 冗余状态（与上帧相同） | 1 周期读取 + 判断丢弃 |

**实验数据**：在一个简单的网格渲染测试中，每次 Draw Call 都重复设置颜色状态（冗余绑定），GPU 时间翻倍，而使用现代命令缓冲区的 CPU 时间几乎没有增加。

**目标**：以 100M Draw Calls/秒为目标时，若有 10 个状态变更，每次需 <1 周期，极限约为：

$$\text{最大 Draw Calls/s} = \frac{GPU\_Clock\_Hz}{\text{每 Draw 周期数}} = \frac{1 \times 10^9}{10} = 10^8$$

### 5.3 命令处理器中的状态流水线

状态变更存在一个有趣的时间差问题：

- 某些状态可以立即应用（如视口变换参数）
- 某些状态会在**很久以后**才影响管线的后续阶段（如着色器绑定影响尚在处理中的批次）

命令处理器维护一个状态流水线（State Pipeline），将状态变更请求打包，在实际需要时再应用。

### 5.4 Vulkan 的优化建议

**子渲染通道（Sub-pass）与 Hi-Z**：

```
深度缓冲区生命周期：

不好的用法：
[阴影图] → [深度预渲染] → [主渲染] → [SSR pass]
              ↑切换深度缓冲区↑↑切换深度缓冲区↑  ← 每次切换强制 Hi-Z 同步

好的用法（Vulkan Sub-pass）：
[深度预渲染 sub-pass] → [主渲染 sub-pass]  ← Hi-Z 留在芯片上
                     ↕
          中间可交叉不用深度缓冲的 pass
```

**描述符集绑定继承（Binding Inheritance）**：

若着色器 A 和着色器 B 使用相同的描述符集绑定（同一 slot），Vulkan 允许继承，避免重复绑定命令。

**绑定频率组织原则**：

```
描述符集 0：极少变化（全局 UBO：相机、光照）
描述符集 1：每帧变化（Shadow Map 等）
描述符集 2：每物体变化（材质参数）
描述符集 3：每 Draw Call 变化（World Matrix 等，最好用 Push Constants）
```

---

## 6. GPU 驱动渲染（GPU-Driven Rendering）

### 6.1 Multi-Draw Indirect（MDI）的核心原理

传统渲染流程（CPU 驱动）：

```
CPU                          GPU
─────────────────────────────────────
遍历场景物体
 for each object:
   视锥剔除（CPU）
   if 可见:
     glDraw*()     ──────→  执行
```

GPU 驱动渲染流程：

```
CPU                          GPU
─────────────────────────────────────
生成 DrawIndirectCommand 缓冲区
glMultiDrawIndirect()  ──→  GPU Culling Shader（CS）
                               ↓
                            修改 DrawIndirectCommand 缓冲区
                            （设置 instance_count = 0 表示剔除）
                               ↓
                            执行所有 Indirect Draw
```

**DrawIndirectCommand 结构（OpenGL）**：

```c
// OpenGL: DrawArraysIndirectCommand
struct DrawArraysIndirectCommand {
    uint  count;         // 顶点数
    uint  instanceCount; // 实例数（置 0 = 跳过该批次）
    uint  first;         // 第一个顶点
    uint  baseInstance;  // base instance（可用于索引 per-instance 数据）
};

// OpenGL: DrawElementsIndirectCommand
struct DrawElementsIndirectCommand {
    uint  count;         // 索引数
    uint  instanceCount; // 实例数（置 0 = 跳过该批次）
    uint  firstIndex;    // 第一个索引偏移
    int   baseVertex;    // 顶点偏移
    uint  baseInstance;  // base instance
};
```

### 6.2 GPU 端剔除着色器示例（伪代码）

```glsl
// Compute Shader: Frustum + Occlusion Culling
layout(local_size_x = 64) in;

// 输入：每个物体的包围盒
struct ObjectData {
    vec3  aabb_min;
    vec3  aabb_max;
    uint  draw_cmd_index;
};

layout(std430, binding = 0) readonly buffer Objects {
    ObjectData objects[];
};

// 输出：间接绘制命令缓冲区
layout(std430, binding = 1) buffer DrawCmds {
    DrawElementsIndirectCommand draw_cmds[];
};

// Hi-Z 深度图（上一帧的深度）
layout(binding = 2) uniform sampler2D hiz_texture;

uniform mat4 view_proj;
uniform vec2 screen_size;

bool frustumCull(vec3 aabb_min, vec3 aabb_max) {
    // 将 AABB 8 个角变换到裁剪空间，检查是否全在视锥体外
    // ... 省略实现 ...
    return false; // true 表示被剔除
}

bool occlusionCull(vec3 aabb_min, vec3 aabb_max) {
    // 1. 将 AABB 投影到屏幕空间，获取包围矩形
    // 2. 计算覆盖区域对应的 Hi-Z LOD 层级
    //    mip_level = log2(max(screen_width, screen_height))
    // 3. 从 Hi-Z 采样最大深度
    // 4. 比较 AABB 的最近深度与 Hi-Z 深度
    float aabb_depth = ...; // AABB 最近点的深度
    float hiz_depth  = textureLod(hiz_texture, uv, mip).r;
    return aabb_depth > hiz_depth; // 被遮挡则剔除
}

void main() {
    uint idx = gl_GlobalInvocationID.x;
    if (idx >= objects.length()) return;

    ObjectData obj = objects[idx];
    uint cmd_idx = obj.draw_cmd_index;

    if (frustumCull(obj.aabb_min, obj.aabb_max) ||
        occlusionCull(obj.aabb_min, obj.aabb_max)) {
        // 剔除：将 instanceCount 置 0
        draw_cmds[cmd_idx].instanceCount = 0;
    } else {
        draw_cmds[cmd_idx].instanceCount = 1;
    }
}
```

### 6.3 命令缓冲区压实（Compaction）

GPU 剔除后，命令缓冲区中有大量 `instanceCount = 0` 的空洞，直接执行会产生**管线气泡（Pipeline Bubble）**：

```
未压实的命令缓冲区：
[DrawA: count=1] [DrawB: count=0] [DrawC: count=0] [DrawD: count=1] ...
                                                   ↑ 气泡

压实后的命令缓冲区：
[DrawA: count=1] [DrawD: count=1] [DrawE: count=1] ...
```

**压实方法**：使用 Compute Shader + Atomic Counter 进行 Stream Compaction：

```glsl
layout(std430, binding = 2) buffer CompactedCmds {
    DrawElementsIndirectCommand compacted[];
};

layout(std430, binding = 3) buffer Counter {
    uint draw_count;  // 原子计数器
};

void main() {
    // ... 剔除判断 ...
    if (is_visible) {
        uint slot = atomicAdd(draw_count, 1);
        compacted[slot] = draw_cmds[cmd_idx];
    }
}
```

### 6.4 GPU 端 LOD 决策

使用 MDI 还可以在 GPU 上决定每个物体的 LOD：

```glsl
// 根据投影尺寸选择 LOD
float lod_distance = length(camera_pos - object_center);
float projected_size = object_radius / lod_distance; // 近似屏幕占比

uint lod_level;
if (projected_size > 0.1)      lod_level = 0;  // High LOD
else if (projected_size > 0.02) lod_level = 1;  // Medium LOD
else                            lod_level = 2;  // Low LOD / Point Sprite

// 写入对应 LOD 的 DrawCommand
draw_cmds[cmd_idx] = lod_draw_cmds[object_id][lod_level];
```

### 6.5 与传统遮挡剔除对比

| 方案 | 延迟 | 使用的信息时效 |
|------|------|-------------|
| CPU 读回 Occlusion Query | 高（等 1-2 帧）| 旧帧信息（有鬼影风险） |
| GPU-Driven Occlusion Culling | 无 | 当前帧信息 |

讲师提到：NVIDIA 的 VR 演示（复杂汽车模型）通过 GPU-Driven Occlusion Culling，在 VR 90Hz 下流畅运行，且无传统方案的"鬼影"问题。

---

## 7. 数据传输与内存优化

### 7.1 数据上传策略

**暂存缓冲区 + 分散着色器**：

```
CPU 内存                GPU 内存
─────────                ────────────
[紧凑更新包]  PCI-e→  Staging Buffer
                              ↓
                   Scatter Shader（CS）
                              ↓
                       [目标 GPU 缓冲区]
                    （位置 A, C, G, M...）
```

优点：传输数据量最小（只传变化量），散射由 GPU 完成（接近零 CPU 代价）。

**何时留在 CPU 内存**：若数据每帧只使用一次（如极动态的顶点数据），可不传 GPU，GPU 直接从系统内存读取：

$$\text{传输成本} = \text{PCIe 延迟} + \text{传输时间}$$
$$\text{不传输成本} = \text{PCIe 读取延迟（每次访问）} \times \text{访问次数}$$

若访问次数 = 1，不传输可能更划算。

### 7.2 Vulkan 图像 Tiling 格式

| Tiling 格式 | 适合用途 | GPU 访问性能 |
|-----------|---------|------------|
| `VK_IMAGE_TILING_LINEAR` | 上传（CPU 写入友好）| 差（不适合 GPU 纹理采样） |
| `VK_IMAGE_TILING_OPTIMAL` | GPU 纹理、帧缓冲区 | 好（硬件 Morton 或 Swizzle 排列）|

规则：**帧缓冲区和 GPU 纹理必须使用 `OPTIMAL` 格式；只有作为 Copy 源/目标的中间缓冲区才用 `LINEAR`。**

### 7.3 重新计算 vs 传输

对于矩阵更新，可以只传增量，GPU 重新计算完整矩阵：

```
方案 A（直接传输）：
CPU → GPU: 16×float × 每物体矩阵 = 64 bytes/object × N objects

方案 B（增量 + 重计算）：
CPU → GPU: 变化量（例如旋转四元数 4×float = 16 bytes）
GPU 计算: 从 QQ + Parent Matrix 重建完整矩阵
```

**双精度矩阵（Double Precision）最佳实践**：

大世界（Large World Coordinates）渲染时，需要双精度来避免浮点精度问题（远离原点）：

- **在 CPU 上** 用双精度做矩阵级联（Camera × View × Model）
- **传给 GPU** 时转换为 float（相对于某个参考点的偏移）

```
// 正确做法：CPU 上双精度级联
mat4d mvp_double = camera_proj * camera_view * object_world;
// 转换为 float 后传 GPU
mat4f mvp_float = mat4f(mvp_double);
```

---

## 8. Warp 与线程发散

### 8.1 Warp 基本模型

NVIDIA GPU 以 **Warp** 为最小调度单位，每个 Warp 包含 **32 个线程**：

- 所有线程共享同一 **指令指针（Instruction Pointer）**
- 每个线程有独立的**寄存器文件**
- 所有线程执行同一条指令，但操作各自的数据（SIMT 模型）

```
Warp（32 threads）：
┌─────────────────────────────────────────────────┐
│ PC→  instr: mul r0, r1, r2                       │
│                                                  │
│ T0: r0=1.0 * 2.0=2.0   T8:  r0=1.5 * 3.0=4.5   │
│ T1: r0=3.0 * 1.0=3.0   T9:  ...                 │
│ ...                      ...                      │
│ T31: r0=2.5 * 1.0=2.5                            │
└─────────────────────────────────────────────────┘
```

### 8.2 分支发散（Branch Divergence）

当 Warp 内的线程走不同的分支时，必须**串行执行两个分支**：

```glsl
// 示例：if-else 发散
if (thread_id < 16) {
    // 路径 A：T0-T15 执行，T16-T31 被 mask 掉
    result = expensiveOperationA();
} else {
    // 路径 B：T0-T15 被 mask 掉，T16-T31 执行
    result = expensiveOperationB();
}
// 实际代价 ≈ A 的时间 + B 的时间（不是 max(A,B)）
```

最坏情况：32 个线程走 32 条不同路径 → 利用率 1/32。

### 8.3 循环发散（Loop Divergence）

```glsl
// 不同线程有不同循环次数
int loop_count = dynamic_value[thread_id]; // 各不相同

for (int i = 0; i < loop_count; i++) {
    // 所有线程都要等到循环次数最多的线程完成
    // 已完成的线程被 mask 掉但占用 SM 时间
}
```

**优化策略**：若循环次数在编译时已知，使用 **unroll** 或模板参数展开：

```glsl
// GLSL: 编译时常量循环（可被自动展开）
const int KERNEL_SIZE = 5;
for (int i = 0; i < KERNEL_SIZE; i++) {
    // 编译器知道有 5 次迭代，可进行批量纹理请求等优化
}
```

### 8.4 Warp 洗牌指令（Shuffle Instructions）

在同一 Warp 的线程之间直接交换数据（无需共享内存）：

```glsl
// GLSL: Warp shuffle 示例
#extension GL_NV_shader_thread_shuffle : enable

// 获取同 Warp 中另一个线程的值
float neighbor_value = shuffleNV(my_value, target_lane, 32);

// 广播：把 lane 0 的值广播给所有线程
float broadcast = shuffleNV(my_value, 0, 32);
```

**应用场景**：
- 像素着色器中的 ddx/ddy 偏导计算（访问相邻 Quad 的值）
- 顶点着色器中三角形内顶点数据共享
- Reduction 操作（如 warp-level max/sum）

### 8.5 占用率（Occupancy）与延迟隐藏

SM 同时维护多个 Warp，当一个 Warp 等待内存时切换到另一个：

```
时间轴（SM 执行）：
Warp A: [执行] [等内存...............] [执行]
Warp B:        [执行] [等内存.......] [执行]
Warp C:               [执行] [等]   [执行]

SM 实际利用率 ≈ 100%（延迟被隐藏）
```

**影响占用率的主要因素**：

| 因素 | 影响 |
|------|------|
| 寄存器用量（Register Count） | 越多，同时在飞 Warp 数越少 |
| 共享内存用量（Shared Memory） | 越多，同时在飞 Warp 数越少 |
| 插值数据（Varyings）| 影响片上存储 |
| 顶点输入属性 | L1 缓存占用 |

**关键公式**：

$$\text{可用 Warp 数} = \min\left(\frac{\text{SM 寄存器总数}}{\text{每 Warp 寄存器数}}, \frac{\text{SM 共享内存}}{\text{每 Warp 共享内存}}, \text{硬件 Warp 上限}\right)$$

---

## 9. 着色器优化策略

### 9.1 专用着色器 vs 大型 Uber Shader

**反模式（Uber Shader 内置动态分支）**：

```glsl
// 坏：大型 uber shader + 动态分支
uniform bool use_normal_map;
uniform bool use_shadow;

// 无论是否用法线贴图，都会占用切线空间 varying 的带宽
in vec3 tangent;
in vec3 bitangent;
in vec3 normal;

void main() {
    if (use_normal_map) {
        // 用到 tangent/bitangent
    } else {
        // tangent/bitangent 浪费了
    }
}
```

**最佳实践（专用着色器组合）**：

```glsl
// 好：生成多个专用着色器变体
// 变体 A: 法线贴图版本
in vec3 tangent;
in vec3 bitangent;
// ... 只包含需要的输入和代码

// 变体 B: 无法线贴图版本
// in vec3 tangent;  // 不需要，不占 varying 槽和缓存
```

**收益**：减少 Varying 传递带宽、减少寄存器占用、提高占用率。

### 9.2 重计算 vs 传递插值

对于高多边形场景（大量顶点），Varyings 可能成为片上内存瓶颈：

```glsl
// 方案 A：VS 输出世界空间法线（多一个 varying）
// VS:
out vec3 world_normal;
world_normal = mat3(model_matrix) * object_normal;

// FS:
in vec3 world_normal; // 占用 varying 槽

// 方案 B：FS 中重新计算（节省 varying 槽）
// VS:
out vec3 object_normal; // 保持对象空间

// FS:
in vec3 object_normal;
vec3 world_normal = mat3(model_matrix) * object_normal; // 重新计算
// 代价：多几条 ALU 指令
// 收益：节省 varying 槽 → 更高占用率
```

选择依据：当 varying 带宽是瓶颈时，重计算更好；当 ALU 是瓶颈时，直接传递更好。

### 9.3 计算着色器 vs 图形（小工作量）

对于**少量线程**的工作（如更新几个矩阵）：

```
方案 A：Compute Shader
  - 需要图形→计算→图形的 Pipeline 切换开销
  - 有 Dispatch Overhead

方案 B：禁用光栅化的图形 Pass
  // VS 承担 Compute 的作用
  void main() {
      // 根据 vertex_id 决定处理哪个工作项
      uint work_id = gl_VertexID;
      // ... 处理逻辑 ...
      gl_Position = vec4(0.0); // 点渲染，光栅化被丢弃
  }
  // 调用：glDrawArrays(GL_POINTS, 0, work_count);
```

**选择规则**：
- 极少线程（几个到几百个）→ 用图形（渲染 Points，禁用光栅化）
- 大量线程（几千以上）→ 用 Compute
- 两者切换本身也有开销，需要权衡

### 9.4 编译期优化

```glsl
// 坏：动态分支阻止编译器批量纹理请求
for (int i = 0; i < dynamic_count; i++) {
    result += texture(samp, uv[i]); // 编译器不知道有几次，无法批处理
}

// 好：编译期常量循环
const int SAMPLE_COUNT = 9; // 编译期已知
for (int i = 0; i < SAMPLE_COUNT; i++) {
    // 编译器可以：
    // 1. 将 9 次纹理请求批量发出（隐藏延迟）
    // 2. 展开循环（unroll）
    result += texture(samp, uv[i]);
}
```

---

## 10. 内存缓冲区类型选择

### 10.1 三种主要缓冲区对比

| 缓冲区类型 | 适用场景 | 优点 | 缺点 |
|-----------|---------|------|------|
| Uniform Buffer（UBO）| 同一 Warp 内所有线程访问相同数据 | 极快（广播访问） | 发散访问慢（走慢速路径） |
| Texture Buffer（TBO）| 发散访问（不同线程访问不同位置） | 利用纹理缓存和硬件地址数学 | 免费格式转换（如 uint8→float）|
| Shader Storage Buffer（SSBO）| 读写、原子操作 | 灵活（可写入）、支持大尺寸 | 地址计算开销、64 位地址数学 |

### 10.2 选择决策树

```
需要写入？
├─ 是 → SSBO（唯一选择）
│        注意：不要开 Robust Buffer Access（除非必要）
│        因为额外的边界检查会增加大量指令
└─ 否 → 访问模式？
         ├─ Uniform（同 Warp 内访问相同位置）
         │   → UBO（最快）
         │   注意：蒙皮动画（不同顶点不同骨骼矩阵）= 发散访问
         │   → 不适合 UBO！
         └─ 发散（不同线程访问不同位置）
             → TBO（更好）
             注意：大量 TBO 会使纹理单元成为瓶颈
             → 可与 SSBO 混搭平衡
```

**蒙皮动画示例**（发散访问典型案例）：

```glsl
// 坏：蒙皮矩阵放在 UBO 中（发散访问）
layout(std140) uniform BoneUBO {
    mat4 bones[256];
};

// 同 Warp 内不同顶点访问不同骨骼 → 发散 → UBO 慢路径
mat4 bone_matrix = bones[bone_indices[0]];

// 好：蒙皮矩阵放在 TBO 中
layout(binding = 0) uniform samplerBuffer bone_tbo;

// 利用纹理缓存处理发散访问
mat4 bone_matrix = mat4(
    texelFetch(bone_tbo, bone_indices[0] * 4 + 0),
    texelFetch(bone_tbo, bone_indices[0] * 4 + 1),
    texelFetch(bone_tbo, bone_indices[0] * 4 + 2),
    texelFetch(bone_tbo, bone_indices[0] * 4 + 3)
);
```

### 10.3 Vulkan Robust Buffer Access

在 Vulkan 中，如果没有明确需要，**不要启用 `VkPhysicalDeviceFeatures::robustBufferAccess`**：

- 启用后，驱动/硬件会在每次 SSBO 访问时插入边界检查
- 可能大幅增加着色器指令数
- 仅在调试或需要安全性的场景下启用

---

## 11. 遮挡剔除与 LOD

### 11.1 Hi-Z Occlusion Culling 原理

Hi-Z（Hierarchical Z）是一种基于深度缓冲区 Mipmap 的遮挡剔除技术：

```
深度缓冲区 Hi-Z 层级：

Mip 0 (全分辨率):  ┌──┬──┬──┬──┐  逐像素深度
                   └──┴──┴──┴──┘
Mip 1 (1/2):      ┌──┬──┐        每个像素 = 2×2 区域最大深度
                  └──┴──┘
Mip 2 (1/4):      ┌──┐            每个像素 = 4×4 区域最大深度
                  └──┘
...
```

**物体 AABB 测试步骤**：

1. 将 AABB 投影到屏幕空间，计算包围矩形
2. 选择 Mip 级别：$\text{mip} = \lceil \log_2(\max(w_{screen}, h_{screen})) \rceil$（确保采样覆盖整个包围矩形）
3. 采样 Hi-Z 获得区域内最大深度 $d_{hiz}$
4. 计算 AABB 离相机最近点的深度 $d_{near}$
5. 若 $d_{near} > d_{hiz}$，则物体完全被遮挡 → 剔除

```
深度判断（NDC 空间，深度范围 [0,1]，1 = 远平面）：

  d_near < d_hiz  → AABB 最近点比 Hi-Z 存储的最远深度更近
                 → 物体可能可见（不能剔除）

  d_near > d_hiz  → AABB 最近点比区域内所有像素都更远
                 → 物体一定被遮挡（安全剔除）
```

### 11.2 Hi-Z 生成

```glsl
// Compute Shader: 生成 Hi-Z Mipmap
// 每次从上一级 Mip 的 4 个像素取最大值

layout(binding = 0) uniform sampler2D prev_mip;
layout(binding = 1, r32f) writeonly uniform image2D curr_mip;

void main() {
    ivec2 coord = ivec2(gl_GlobalInvocationID.xy);
    ivec2 src = coord * 2;

    float d0 = texelFetch(prev_mip, src + ivec2(0,0), 0).r;
    float d1 = texelFetch(prev_mip, src + ivec2(1,0), 0).r;
    float d2 = texelFetch(prev_mip, src + ivec2(0,1), 0).r;
    float d3 = texelFetch(prev_mip, src + ivec2(1,1), 0).r;

    // 取最大深度（最远）→ 保守剔除（不会错误剔除可见物体）
    float max_depth = max(max(d0, d1), max(d2, d3));
    imageStore(curr_mip, coord, vec4(max_depth));
}
```

### 11.3 GPU-Driven LOD 选择

```glsl
// 在 GPU Culling Shader 中计算 LOD 并写入对应 DrawCommand
float projected_radius = (object_radius / distance) * half_screen_height / tan(fov * 0.5);

uint lod = 0;
if (projected_radius < 8.0)  lod = 3;  // 极远：点精灵
else if (projected_radius < 32.0) lod = 2;  // 较远：低模
else if (projected_radius < 128.0) lod = 1; // 中等：中模
// else lod = 0;                              // 近处：高模

// 写入对应 LOD 的绘制命令
draw_cmds[cmd_idx] = lod_templates[object_type][lod];
draw_cmds[cmd_idx].baseInstance = object_id; // 用于索引 per-instance 数据
```

---

## 12. 几何着色器 vs 细分着色器

### 12.1 细分着色器（Tessellation Shader）的效率

细分着色器由两个阶段组成：

1. **Hull Shader（TCS）**：决定每个面片（Patch）的细分级别
2. **Domain Shader（TES）**：计算细分后每个顶点的位置

**硬件高效性原因**：

```
Hull Shader 输出细分级别（如：12×12）
             ↓
固定功能细分单元（PGE：Primitive Generator）
  动态生成 144 个子三角形
  这些三角形和数据直接在芯片上（L1/L2 Cache）产生和消费
             ↓
Domain Shader 计算每个新顶点的位置
             ↓
光栅化
```

细分产生的数据**直接在片上传递**，不经过 DRAM，效率极高。

### 12.2 几何着色器（Geometry Shader）的效率问题

几何着色器在需要**动态扩展**（如 1 个三角形 → N 个三角形）时效率很差：

```
GPU 无法知道 GS 会输出多少数据
→ 必须预先分配最大可能输出（max_vertices）
→ 大量内存可能浪费（绝大多数情况输出少于最大值）
→ 数据必须写入 DRAM 再读回（不能像 Tessellation 那样在片上流转）
```

**GS 合适的用途**：
- `GL_NV_geometry_shader_passthrough`（快速 GS）：允许以极低代价将同一原语发送到多个视图（Cube Map 渲染、Stereo VR）
- 简单的面级别剔除（背面剔除、视锥体剔除单个三角形）

### 12.3 程序化顶点生成（替代 GS）

使用顶点 ID 手动生成几何体（无需 GS）：

```glsl
// 用一个 DrawArrays 渲染程序化几何体
// 例如：每 6 个顶点 ID 生成一个 Quad（2 个三角形）

void main() {
    uint quad_id = gl_VertexID / 6;       // 第几个 Quad
    uint local_id = gl_VertexID % 6;      // Quad 内部的顶点索引

    // 从缓冲区读取 Quad 的位置/数据
    vec4 quad_data = texelFetch(quads_buffer, int(quad_id));

    // 根据 local_id 决定这是 Quad 的哪个顶点
    vec2 offsets[6] = vec2[6](
        vec2(0,0), vec2(1,0), vec2(0,1),   // 第一个三角形
        vec2(1,0), vec2(1,1), vec2(0,1)    // 第二个三角形
    );
    vec2 offset = offsets[local_id];

    gl_Position = /* 根据 quad_data 和 offset 计算 */;
}
```

**Warp Shuffle 在顶点间共享**：

```glsl
// 顶点着色器中，同一三角形的 3 个顶点在同一 Warp 内
// 可以通过 shuffle 相互访问数据

float vertex_data = computeVertexData();

// 三角形的另外两个顶点也在同一 Warp
// （前提：原语分发时三角形的顶点被分配到连续 lane）
float neighbor_data = shuffleNV(vertex_data, neighbor_lane, 32);
```

### 12.4 像素着色器实现几何效果

用像素着色器 + discard 代替几何体：

```glsl
// 像素着色器：绘制圆形点精灵
void main() {
    vec2 uv = gl_PointCoord * 2.0 - 1.0; // [-1, 1]
    float dist = length(uv);

    if (dist > 1.0) discard; // 圆形外丢弃

    // 手动 MSAA 覆盖率计算（因为不是三角形边缘）
    float coverage = 1.0 - smoothstep(0.9, 1.0, dist);
    // 或者用 gl_SampleMask 精确控制 sample coverage

    out_color = vec4(circle_color, coverage);
}
```

**注意**：基于像素着色器的形状需要手动计算 MSAA 覆盖率（三角形边缘由硬件自动处理，但 discard 后的形状没有这个自动处理）。

---

## 13. 实践建议汇总

### 13.1 全局架构层面

| 建议 | 说明 |
|------|------|
| 将渲染组织为有限数量的"政权" | 分析每个政权的瓶颈单元，针对性优化 |
| 最小化全局屏障（Wait GPU Idle） | 避免 Ramp Up/Down 双重代价 |
| 使用 Vulkan Sub-pass | 允许 Hi-Z 留在片上，减少深度缓冲区切换代价 |
| 使用 GPU-Driven Culling（MDI） | 消除 CPU-GPU 往返延迟，使用当帧信息 |
| 压实 Indirect Command Buffer | 消除空 Draw Call 导致的管线气泡 |

### 13.2 着色器层面

| 建议 | 说明 |
|------|------|
| 使用专用着色器变体而非动态分支 | 减少 varying 带宽、提高占用率 |
| 避免 Warp 内分支/循环发散 | 防止线程等待最慢的路径 |
| 动态循环改为编译期循环 | 编译器可批量发出纹理请求 |
| 关注寄存器用量 | 过多寄存器降低占用率，影响延迟隐藏 |
| 合理选择缓冲区类型 | 发散访问用 TBO，均匀访问用 UBO，需要写入用 SSBO |
| 避免不必要的 Robust Buffer Access | 移除 SSBO 边界检查开销 |

### 13.3 数据层面

| 建议 | 说明 |
|------|------|
| 使用暂存缓冲区 + 分散着色器 | 减少 PCIe 传输量 |
| 单次使用数据可留在 CPU 内存 | 避免无意义的传输 + 直接读 |
| Vulkan 图像使用 OPTIMAL tiling | LINEAR 性能很差 |
| 矩阵用双精度级联，float 传 GPU | 大世界精度 + GPU 性能平衡 |
| 重计算 vs 传递插值需要权衡 | Varying 带宽 vs ALU 代价 |

### 13.4 关键性能指标参考

```
优化目标：
- 目标 Draw Calls/s: 100M+（使用现代 API）
- 每个 Draw Call 的状态变更 < 10 条命令（以保持前端非瓶颈）
- Warp 占用率 > 50%（通过控制寄存器/共享内存用量）
- 纹理缓存命中率 > 90%（热点数据应该放 TBO/常用纹理）
- 消除所有不必要的 glWaitSync / VkPipelineBarrier
```

---

## 附录：关键 API 参考

### OpenGL Multi-Draw Indirect

```c
// 设置间接缓冲区
glBindBuffer(GL_DRAW_INDIRECT_BUFFER, indirect_buffer);

// 执行多个间接绘制
glMultiDrawElementsIndirect(
    GL_TRIANGLES,               // 图元类型
    GL_UNSIGNED_INT,            // 索引类型
    (const void*)0,             // 缓冲区偏移
    draw_count,                 // 最大绘制数
    sizeof(DrawElementsIndirectCommand) // 步长
);
```

### Vulkan 间接绘制

```c
// 填充 VkDrawIndexedIndirectCommand
VkDrawIndexedIndirectCommand cmd = {
    .indexCount    = index_count,
    .instanceCount = 1,         // GPU Culling 时可置 0
    .firstIndex    = 0,
    .vertexOffset  = 0,
    .firstInstance = object_id  // 用于索引 per-instance 数据
};

// 提交间接绘制
vkCmdDrawIndexedIndirect(
    cmd_buf,
    indirect_buffer,
    offset,
    draw_count,
    stride
);
```

### GPU 端修改 Draw Command（Vulkan/OpenGL）

```glsl
// Compute Shader 直接写入间接绘制缓冲区
layout(std430, binding = 0) buffer IndirectCmds {
    DrawElementsIndirectCommand commands[];
};

void main() {
    uint id = gl_GlobalInvocationID.x;
    bool visible = /* 剔除判断 */;
    commands[id].instanceCount = visible ? 1u : 0u;
}
```

---

> 本笔记根据 NVIDIA GTC 2016《GPU-Driven Rendering》讲座字幕综合整理，内容涵盖该讲座的全部核心技术点，适合作为 GPU 架构理解和 GPU 驱动渲染实现的参考资料。
