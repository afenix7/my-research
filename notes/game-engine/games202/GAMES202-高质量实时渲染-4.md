# GAMES202 第4讲：PCF、PCSS、VSSM 与矩阴影

> 本讲深入讲解软阴影的实时实现方法，从 PCF 到 PCSS 到 VSSM，并引入 Moment Shadow Mapping。

---

## 1. Shadow Map 回顾与问题

Shadow Map 的基本判断：

$$\text{visibility}(x) = \chi^+\!\left(z_{\text{light}}(x) - d_{\text{shadow}}(x)\right)$$

其中 $\chi^+$ 为阶跃函数（正数返回 1，负数返回 0），$d_{\text{shadow}}(x)$ 为 shadow map 中存储的最近深度。

**问题**：
- 产生**硬阴影**（锐利边缘），不真实
- 存在自遮挡（shadow acne）和悬浮阴影（peter panning）

---

## 2. PCF（Percentage Closer Filtering）

### 2.1 核心思想

PCF **不是**对 Shadow Map 的深度值做滤波，而是对**比较结果**（0/1）做滤波。

对着色点 $x$，其 shadow map 投影坐标为 $p$，对 $p$ 周围的邻域 $\mathcal{N}(p)$ 内所有采样点 $q$ 进行比较并加权平均：

$$V(x) = \sum_{q \in \mathcal{N}(p)} w(p, q) \cdot \chi^+\!\left(z_{\text{light}}(x) - d_{\text{shadow}}(q)\right)$$

其中 $w(p, q)$ 为权重函数（如高斯权重）。

### 2.2 PCF 与卷积

PCF 等价于对可见性（二值函数）做卷积（加权平均）：

$$V(x) = (w * f)(p), \quad f(q) = \chi^+\!\left(z_{\text{light}}(x) - d_{\text{shadow}}(q)\right)$$

> **注意**：这与对 Shadow Map 深度值做卷积再比较是**不等价**的（深度比较是非线性操作，不能交换顺序）。

### 2.3 PCF 的效果与问题

- 滤波核越大 → 阴影越模糊（软阴影效果）
- 滤波核越小 → 阴影越硬（接近硬阴影）
- **问题**：固定大小的滤波核无法模拟真实的软阴影（真实软阴影的模糊程度随遮挡距离变化）

---

## 3. PCSS（Percentage Closer Soft Shadows）

### 3.1 物理直觉：半影宽度公式

真实软阴影的核心——**半影（Penumbra）**的宽度：

$$w_{\text{penumbra}} = \frac{(d_{\text{receiver}} - d_{\text{blocker}}) \cdot w_{\text{light}}}{d_{\text{blocker}}}$$

其中：
- $w_{\text{light}}$：光源尺寸
- $d_{\text{blocker}}$：遮挡物到光源的平均距离
- $d_{\text{receiver}}$：接收者到光源的距离

遮挡物**越近**于光源 → 半影**越宽**（越软）
遮挡物**越近**于接收者 → 半影**越窄**（越硬）

### 3.2 PCSS 算法步骤

**Step 1：Blocker Search（遮挡物搜索）**

在 Shadow Map 上，以 $p$ 为中心，搜索半径为 $r_{\text{search}}$ 的区域，只平均真正遮挡了当前点的 Shadow Map texel 的深度：

$$d_{\text{avg\_blocker}}(x) = \frac{1}{|\{q : d_{\text{shadow}}(q) < z_{\text{light}}(x)\}|} \sum_{\substack{q \in \mathcal{N}(p) \\ d_{\text{shadow}}(q) < z_{\text{light}}(x)}} d_{\text{shadow}}(q)$$

**Step 2：Penumbra Estimation（半影估计）**

$$w_{\text{filter}} = w_{\text{light}} \cdot \frac{d_{\text{receiver}} - d_{\text{avg\_blocker}}}{d_{\text{avg\_blocker}}}$$

**Step 3：PCF（使用自适应滤波核）**

用第二步得到的 $w_{\text{filter}}$ 作为 PCF 的滤波核大小，执行 PCF。

### 3.3 PCSS 的代价

- Step 1（Blocker Search）和 Step 3（PCF）都需要大范围采样
- 当 $w_{\text{filter}}$ 很大时（距离光源近的遮挡物），需要采样极多样本
- 这催生了更高效的 VSSM 方法

---

## 4. VSSM（Variance Soft Shadow Maps）

### 4.1 核心思想

用**统计方法**近似 PCSS 中的两个耗时步骤，避免大量采样。

关键洞察：PCSS 中需要知道"Shadow Map 上某区域内有多少 texel 的深度 < $d$"，这本质上是一个**CDF（累积分布函数）**查询问题。

利用**切比雪夫不等式（Chebyshev's Inequality）**近似 CDF：

$$P(x \geq t) \leq \frac{\sigma^2}{\sigma^2 + (t - \mu)^2}$$

其中 $\mu$ 和 $\sigma^2$ 分别为该区域深度值的**均值**和**方差**。

### 4.2 均值和方差的高效计算

**均值 $\mu$**：通过 MIP-map 或 **SAT（Summed Area Table，积分图）** 在 $O(1)$ 时间查询任意矩形区域的均值。

**方差 $\sigma^2$**：

$$\sigma^2 = E[z^2] - (E[z])^2 = \mu_{z^2} - \mu_z^2$$

需要额外存储 $z^2$ 的积分图（在 Shadow Map 中额外存储深度值的**平方**）。

### 4.3 VSSM 估计可见性

对着色点 $x$，设其在光源空间的深度为 $t = z_{\text{light}}(x)$，Shadow Map 某区域的均值和方差为 $\mu, \sigma^2$：

$$V(x) \approx P(z_{\text{shadow}} > t) \leq \frac{\sigma^2}{\sigma^2 + (t - \mu)^2}$$

> **注意**：切比雪夫不等式给出的是上界，直接将其作为可见性的近似。

### 4.4 VSSM 估计平均遮挡深度

设整个区域中 $N$ 个深度值，$N_1$ 个遮挡（$z < t$），$N_2$ 个不遮挡（$z \geq t$）：

$$\mu = \frac{N_1}{N} \mu_1 + \frac{N_2}{N} \mu_2$$

假设 $\mu_2 \approx t$（非遮挡部分深度接近 $t$），由切比雪夫不等式估计 $\frac{N_1}{N}$，进而估计 $\mu_1$（即 $d_{\text{avg\_blocker}}$）。

### 4.5 VSSM 的问题

- **漏光（Light Leaking）**：当深度分布不符合假设（双峰分布）时，切比雪夫不等式估计偏差大，导致不该有光的地方出现光照。

---

## 5. Moment Shadow Mapping（矩阴影映射）

### 5.1 动机

VSSM 仅用一阶矩和二阶矩来近似深度分布，精度有限（导致漏光）。
**Moment Shadow Mapping** 使用更高阶的矩来更精确地表示深度 CDF。

### 5.2 基本思想

存储深度的前 $m$ 个幂次矩：

$$\{E[z], E[z^2], E[z^3], \ldots, E[z^m]\}$$

用这 $m$ 个矩重建 CDF $P(z \leq t)$，从而估计可见性。

通常使用 **4 阶矩**（$m=4$），精度明显优于 VSSM（2 阶矩）。

### 5.3 代价

- 需要额外存储多个通道（4 个浮点数 per texel）
- 矩重建 CDF 需要求解多项式方程，有额外计算开销
- 但整体仍比 PCSS 的大范围采样高效

---

## 6. Distance Field Shadows 简介

利用 **SDF（有向距离场）** 可以快速估计某点沿特定方向看去的"安全锥角"，从而近似软阴影的 visibility。

优点：
- 无自遮挡和悬浮阴影问题
- 可以达到复杂几何软阴影效果

局限：
- 需要为场景预计算并存储三维 SDF，**存储代价大**
- 不支持形变物体

---

## 7. 关键术语表

| 术语 | 说明 |
|------|------|
| **Shadow Map** | 从光源视角记录深度的纹理 |
| **PCF** | Percentage Closer Filtering，对比较结果做滤波 |
| **PCSS** | Percentage Closer Soft Shadows，自适应软阴影 |
| **Penumbra** | 半影，软阴影的模糊过渡区域 |
| **Blocker Search** | PCSS 第一步，搜索遮挡当前点的遮挡物 |
| **VSSM** | Variance Soft Shadow Maps，方差软阴影 |
| **Chebyshev's Inequality** | 切比雪夫不等式，用于估计概率上界 |
| **SAT** | Summed Area Table，积分图，用于 $O(1)$ 均值查询 |
| **Moment Shadow Mapping** | 矩阴影映射，使用高阶矩改善 VSSM 的漏光 |
| **Light Leaking** | 漏光，VSSM 中由分布假设偏差导致的错误光照 |
| **SDF** | Signed Distance Function/Field，有向距离场 |

---

## 总结

1. **PCF** 通过对 Shadow Map 区域内的比较结果做加权平均实现软阴影，滤波核越大越软。
2. **PCSS** 通过自适应滤波核大小（基于遮挡物距离估计）实现物理正确的软阴影，但采样代价高。
3. **VSSM** 用切比雪夫不等式 + 均值/方差近似 PCSS，避免大量采样，但存在漏光问题。
4. 核心公式：$\sigma^2 = E[z^2] - (E[z])^2$，通过双通道 Shadow Map 存储 $z$ 和 $z^2$ 实现 $O(1)$ 方差查询。
5. **Moment Shadow Mapping** 进一步提高精度，代价是更多存储和计算。
