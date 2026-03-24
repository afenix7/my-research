# GAMES202 第1讲：课程介绍与实时渲染概述

> 讲师：闫令琪（Lingqi Yan），UCSB 教授
> 课程定位：高质量实时渲染（Real-Time High Quality Rendering）
> 前置课程：GAMES101（计算机图形学基础）

---

## 1. 什么是实时渲染

### 1.1 实时（Real-Time）的定义

**实时渲染**要求渲染速度达到或超过 **30 FPS（帧每秒）**，即每秒生成至少 30 幅图像。

| 速度级别 | FPS 范围 | 说明 |
|---------|---------|------|
| Real-Time | ≥ 30 FPS | 游戏、交互应用 |
| Interactive | 几帧/秒 ~ 30 FPS | 可以交互但略卡顿 |
| Offline | 分钟/帧 ~ 小时/帧 | 电影、高质量离线渲染 |

特殊场景（如 VR/AR）对实时要求更高，通常需要达到 **90 FPS**。

### 1.2 高质量（High Quality）的含义

**高质量**意味着渲染结果在物理上是正确或近似正确的，追求**以假乱真**（photorealism）。
实时渲染的核心挑战：在速度与质量之间取得最优 Trade-off，理想目标是"**全都要**"。

Artifact（渲染瑕疵）在动态帧序列中更明显（每秒 30 次重复出现），因此实时渲染对 artifact 容忍度更低。

### 1.3 渲染（Rendering）的本质

渲染是**模拟光线传播**的过程：

$$L_o(x, \omega_o) = \int_{\Omega} f_r(x, \omega_i, \omega_o) \cdot L_i(x, \omega_i) \cdot (\omega_i \cdot \mathbf{n}) \, d\omega_i$$

从三维场景出发，模拟光源发射的光线如何在场景中弹射，最终进入虚拟摄像机（人眼），输出二维图像。

---

## 2. 课程内容概览

本课程分为四大板块：

### 2.1 实时阴影（Real-Time Shadows）

- **Shadow Mapping** 及其改进变体
- **PCF**（Percentage Closer Filtering）— 软阴影滤波
- **PCSS**（Percentage Closer Soft Shadows）— 自适应软阴影
- **VSSM**（Variance Soft Shadow Maps）— 方差软阴影
- **Distance Field Shadows** — 基于有向距离场的阴影
- 环境光照下的阴影（球谐函数 SH）

### 2.2 全局光照（Global Illumination）

分为 Interactive（非严格实时）和实时两类：

- **RSM**（Reflective Shadow Maps）— 反射阴影图
- **LPV**（Light Propagation Volumes）— 光传播体积
- **VXGI**（Voxel Global Illumination）— 体素化全局光照
- 屏幕空间方法：**SSAO**、**SSDO**、**SSR**

### 2.3 基于物理的着色（PBR Materials）

- 渲染方程（Rendering Equation）及 BRDF
- 微表面模型（Microfacet Model）
- 迪士尼 Principled BRDF
- 非真实感渲染（NPR / Toon Shading）

### 2.4 实时光线追踪（Real-Time Ray Tracing）

- NVIDIA RTX 硬件加速光线追踪
- **时间性降噪**（Temporal Denoising）
- **空间-时间复用**（Spatial-Temporal Sample Reuse）

### 2.5 其他高级话题

- **TAA**（Temporal Anti-Aliasing）时间抗锯齿
- **DLSS**（Deep Learning Super Sampling）深度学习超采样
- 散射介质（Participating Media）渲染
- 屏幕空间反射（SSR）

---

## 3. 实时渲染的驱动力：游戏

实时渲染领域 90% 以上的进步由游戏需求驱动。

典型案例：
- **UE5（虚幻引擎5）**：Nanite 虚拟几何系统 + Lumen 全局光照系统
- **《最后生还者 Part II》**：高质量角色渲染
- **《原神》**：非真实感渲染（NPR）的代表作

> "游戏引擎背后的**科学**（算法）并不特别难，真正难的是**技术**（工程实现的效率）。"

---

## 4. 实时渲染管线回顾

实时渲染基于**光栅化管线**，与离线路径追踪完全不同：

```
顶点数据
  → 顶点着色器（MVP变换）
  → 光栅化（三角形 → 像素/片段）
  → 深度测试（Z-Buffer）
  → 片段着色器（着色 = BRDF计算）
  → 输出合并
  → 最终图像
```

光栅化管线的局限性：
- 对直接光照处理良好
- 全局效果（阴影、间接光照、光线多次弹射）处理困难
- 这正是本课程要解决的核心问题

---

## 5. 关键术语表

| 术语 | 全称 / 说明 |
|------|------------|
| **FPS** | Frames Per Second，帧每秒 |
| **Real-Time** | ≥30 FPS 的渲染速度 |
| **Interactive** | 几帧/秒，可交互但非流畅 |
| **PBR** | Physically Based Rendering，基于物理的渲染 |
| **BRDF** | Bidirectional Reflectance Distribution Function |
| **GI** | Global Illumination，全局光照（含间接光照） |
| **Artifact** | 渲染瑕疵，非预期的视觉错误 |
| **Shadow Map** | 阴影贴图，实时阴影的基础方法 |
| **TAA** | Temporal Anti-Aliasing，时域抗锯齿 |
| **DLSS** | Deep Learning Super Sampling，深度学习超采样 |
| **NPR** | Non-Photorealistic Rendering，非真实感渲染 |
| **SH** | Spherical Harmonics，球谐函数 |
| **SDF** | Signed Distance Function，有向距离场 |

---

## 总结

1. 实时渲染的标准是 ≥30 FPS，核心挑战是在极短时间内生成高质量图像。
2. 本课程围绕**阴影、全局光照、PBR材质、实时光追**四大模块展开。
3. 实时渲染的本质是在**物理正确性**与**计算效率**之间做聪明的近似与权衡。
4. 游戏工业是实时渲染最主要的驱动力，引擎技术展示了学术算法的工程化落地。
5. 本课程知识点更分散，以专题研讨形式展开，每个话题相对独立。
