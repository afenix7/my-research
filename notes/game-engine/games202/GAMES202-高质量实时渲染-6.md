# GAMES202 第6讲：实时环境映射与预计算辐射传输（PRT）

> 本讲介绍如何处理环境光照下的完整着色（含阴影），核心工具是球谐函数（SH）和预计算辐射传输（PRT）。

---

## 1. 从 IBL 到完整的实时环境光照

### 1.1 遗留问题

上讲（第5讲）Split Sum 解决了环境光照下的 **shading（不含阴影）**，Visibility 项被完全忽略。

### 1.2 两种思路及其困境

| 思路 | 方法 | 问题 |
|------|------|------|
| Many Light | 将环境光离散为 $N$ 个点光源 | $O(N)$ 个 Shadow Map，不可接受 |
| 采样 + Visibility | 重要性采样光照方向 | Visibility 未知，无法预测最优采样方向 |

**结论**：实时渲染中，完整的环境光照阴影**无精确解**，只能近似。

---

## 2. Ambient Occlusion（AO，环境光遮蔽）

### 2.1 定义

AO 衡量一个着色点能看到多少"天空"（未被遮挡的上半球比例）：

$$k_A(x) = \frac{1}{\pi} \int_{\Omega^+} V(x, \omega) \cdot \cos\theta \, d\omega$$

其中 $V(x, \omega) = 1$ 表示方向 $\omega$ 未被遮挡，$= 0$ 表示被遮挡。

AO 值在 $[0, 1]$ 之间，1 表示完全无遮挡（开放空间），0 表示完全被遮挡。

### 2.2 AO 的物理意义

在均匀白色环境光 $L_i(\omega) = 1$ 下，漫反射着色点的出射 radiance 为：

$$L_o(x) \approx \frac{\rho}{\pi} \cdot \pi \cdot k_A(x) \cdot L_i = \rho \cdot k_A(x)$$

即 AO 直接乘以 albedo 即可近似环境光着色（粗略近似）。

### 2.3 AO 的限制

- **假设环境光均匀**：真实环境光非均匀时误差大
- **忽略颜色偏转**：遮挡方向可能有高亮区域，AO 认为一律遮挡

---

## 3. 球谐函数（Spherical Harmonics，SH）

### 3.1 什么是球谐函数

球谐函数是定义在单位球面上的一组**正交基函数**，类比于频域中的傅里叶基：

$$Y_l^m(\theta, \phi), \quad l = 0, 1, 2, \ldots, \quad m = -l, \ldots, l$$

- $l$：阶数（order），对应频率
- $m$：次数（degree），同一阶内的不同分量
- 共 $(l+1)^2$ 个基函数到第 $l$ 阶

### 3.2 前几阶 SH 基函数

$$Y_0^0 = \frac{1}{2}\sqrt{\frac{1}{\pi}} \quad \text{（0阶，1个，DC项）}$$

$$Y_1^{-1} = \frac{1}{2}\sqrt{\frac{3}{\pi}} \sin\theta\sin\phi, \quad Y_1^0 = \frac{1}{2}\sqrt{\frac{3}{\pi}} \cos\theta, \quad Y_1^1 = \frac{1}{2}\sqrt{\frac{3}{\pi}} \sin\theta\cos\phi$$

### 3.3 SH 展开

任何球面函数 $f(\omega)$ 可以用 SH 基展开：

$$f(\omega) \approx \sum_{l=0}^{L} \sum_{m=-l}^{l} c_l^m \cdot Y_l^m(\omega)$$

其中系数（投影）：

$$c_l^m = \int_{S^2} f(\omega) \cdot Y_l^m(\omega) \, d\omega$$

### 3.4 SH 乘积积分（极其重要！）

$$\int_{S^2} f(\omega) g(\omega) \, d\omega = \sum_{l,m} c_l^m[f] \cdot c_l^m[g]$$

即 SH 展开系数的**内积**等于原函数的**球面积分**。

### 3.5 SH 的低频近似

- 低阶 SH（前 $L=3$ 阶，即 9 个系数）可以很好地表示**低频球面函数**
- **漫反射 BRDF** 是低频的，用前 3 阶 SH 误差 < 1%
- **Glossy BRDF** 是高频的，需要更多 SH 阶或其他方法

---

## 4. PRT（Precomputed Radiance Transfer）

### 4.1 核心思想

**PRT** 将"**动态光照 + 静态场景**"的渲染方程分解为**光照函数**与**传输函数**：

$$L_o(x, \omega_o) = \int_\Omega L_i(\omega_i) \cdot T(x, \omega_i, \omega_o) \, d\omega_i$$

**传输函数（Transport Function）** $T$ 包含：
- Visibility（阴影与自遮挡）
- BRDF
- 余弦项 $\cos\theta_i$

$T$ 与光照无关，可以在**离线预计算**。

### 4.2 漫反射 PRT

对 Diffuse 材质，传输函数简化为：

$$T(x, \omega_i) = V(x, \omega_i) \cdot \cos\theta_i \cdot \frac{\rho}{\pi}$$

用 SH 展开光照和传输函数：

$$L_i(\omega_i) \approx \sum_j l_j Y_j(\omega_i), \quad T(x, \omega_i) \approx \sum_j t_j^x Y_j(\omega_i)$$

出射 radiance：

$$L_o(x) = \int T \cdot L_i \, d\omega \approx \sum_j l_j \cdot t_j^x = \mathbf{l}^T \mathbf{t}^x$$

即光照向量 $\mathbf{l}$ 与传输向量 $\mathbf{t}^x$ 的**点积**！

**实时计算代价**：$O((L+1)^2)$ 次乘加 per 顶点，$L=3$ 时仅 9 次！

### 4.3 Glossy PRT

对 Glossy 材质，BRDF 依赖于 $\omega_i$ 和 $\omega_o$，传输函数为矩阵：

$$L_o(x, \omega_o) \approx \mathbf{l}^T \mathbf{M}^x \mathbf{b}(\omega_o)$$

其中 $\mathbf{M}^x$ 为每顶点的传输**矩阵**（预计算），$\mathbf{b}(\omega_o)$ 为输出方向的 SH 向量。

### 4.4 PRT 算法流程

```
预计算阶段（离线，场景静态）：
  对每个顶点 x：
    对每个半球方向 ω：
      计算 T(x, ω) = V(x, ω) · cos θ · f_r
    将 T(x, ·) 投影到 SH 系数 t^x

实时渲染阶段：
  1. 采样/更新环境光照 L_i(ω)
  2. 将 L_i 投影到 SH 系数 l
  3. 对每个顶点 x：
       L_o(x) = dot(l, t^x)  // 9维点积
  4. 渲染场景
```

### 4.5 PRT 的优缺点

| 优点 | 局限 |
|------|------|
| 包含 Visibility（阴影和 interreflection） | 场景必须静态（不支持动态物体） |
| 实时计算仅需点积 | 仅支持低频光照（SH 截断） |
| 支持任意旋转的环境光照 | 只适合 Diffuse 或有限 Glossy |

---

## 5. 关键术语表

| 术语 | 说明 |
|------|------|
| **PRT** | Precomputed Radiance Transfer，预计算辐射传输 |
| **SH** | Spherical Harmonics，球谐函数 |
| **Transport Function** | 传输函数，含 BRDF + Visibility + cos θ |
| **Projection** | 将球面函数投影到 SH 基系数 |
| **Reconstruction** | 用 SH 系数近似重建球面函数 |
| **AO** | Ambient Occlusion，环境光遮蔽 |
| **Low-Frequency Lighting** | 低频光照，可用低阶 SH 近似 |
| **Diffuse PRT** | 漫反射 PRT，传输函数为向量，运行时点积 |
| **Glossy PRT** | 镜面 PRT，传输函数为矩阵，存储代价大 |
| **SH Rotation** | 旋转环境光照时的 SH 系数快速旋转 |
| **Interreflection** | 光线多次弹射（间接光照），PRT 可在预计算中包含 |

---

## 总结

1. 环境光照下的完整着色（含阴影）是实时渲染的难点，**Many Light** 和直接采样均不可接受。
2. **AO（环境光遮蔽）** 是一种粗糙近似，假设环境光均匀，仅适合估计局部遮挡效果。
3. **球谐函数（SH）** 是球面函数的正交基，低阶 SH 高效表示低频信号，乘积积分变为点积。
4. **PRT** 通过将传输函数（含阴影、BRDF、cos θ）预计算并投影到 SH，实现运行时 $O(n^2)$ 的高效全局光照（含阴影）。
5. PRT 对**静态场景**极其高效，是连接预计算与实时渲染的经典框架，与实时光线追踪结合是未来方向。
