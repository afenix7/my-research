# GAMES202 第5讲：Distance Field Shadows 与 IBL（Image-Based Lighting）

> 本讲包含两个主题：基于 SDF 的软阴影，以及图像照明（IBL）的实时处理方法。

---

## 1. SDF（Signed Distance Field / Function）

### 1.1 基本定义

**有向距离场（SDF）** 为空间中每个点 $p$ 定义一个标量值：

$$\text{SDF}(p) = \min_{q \in \partial \Omega} \|p - q\| \cdot \text{sign}(p)$$

其中 $\partial \Omega$ 为物体表面，$\text{sign}(p)$：
- 物体**外部**：正值（$+$）
- 物体**内部**：负值（$-$）
- 物体**表面**：零（$0$）

### 1.2 SDF 的关键性质

**安全球（Safe Sphere）**：SDF$(p)$ 的值定义了以 $p$ 为中心的"安全半径"，在此半径内**绝对不可能**与任何物体相交：

$$\forall q : \|p - q\| < \text{SDF}(p) \Rightarrow q \notin \partial \Omega$$

**合并操作**：多个物体的 SDF 取最小值：

$$\text{SDF}_{\text{scene}}(p) = \min_i \text{SDF}_{O_i}(p)$$

---

## 2. Ray Marching（光线步进）

### 2.1 Sphere Tracing 算法

```
输入：光线起点 o，方向 d
当前位置 p = o
重复：
    r = SDF(p)         // 查询当前点的安全距离
    if r < ε：         // 接近表面，认为相交
        返回 p 为交点
    if |p - o| > MAX_DIST：  // 超出最大距离，未相交
        返回 "miss"
    p = p + r * d      // 安全步进（最大步长 = 安全半径）
```

每步可以最大化步长（等于 SDF 值），**无需固定小步长**，效率极高。通常只需 64~128 步即可达到高精度。

---

## 3. SDF Soft Shadows

### 3.1 软阴影的核心：可见角度

对光线 $\mathbf{r}(t) = x + t \hat{d}$ 上每个步进点 $p_t = \mathbf{r}(t)$，计算安全角：

$$\theta_t = \arcsin\!\left(\frac{\text{SDF}(p_t)}{t}\right) \approx \frac{\text{SDF}(p_t)}{t} \quad (\text{小角度近似})$$

### 3.2 可见性估计公式

沿光线步进，取所有步进点的最小"安全角"来估计可见性：

$$V(x) = \min_{t \in [t_{\min}, t_{\max}]} \min\!\left(1, \frac{k \cdot \text{SDF}(p_t)}{t}\right)$$

其中 $k$ 为控制软阴影硬度的参数（$k$ 越大阴影越硬，越小越软）。

### 3.3 SDF 的优缺点

| 优点 | 局限 |
|------|------|
| Ray Marching 效率极高 | 需要预计算并存储三维 SDF（存储代价大，约 $O(N^3)$） |
| 无自遮挡和悬浮问题 | 不支持形变物体（变形后 SDF 失效，需重新计算） |
| 多物体合并高效（取 min） | 刚体可以，但仍需变换坐标系 |

---

## 4. IBL（Image-Based Lighting / 环境光照）

### 4.1 环境光照的表示

**IBL** 使用全景图（Cube Map 或 Spherical Map）表示来自四面八方的环境光照，每个方向 $\omega_i$ 对应一个 radiance 值 $L_i(\omega_i)$。

着色点 $x$ 的出射 radiance：

$$L_o(x, \omega_o) = \int_{\Omega} f_r(x, \omega_i, \omega_o) \cdot L_i(\omega_i) \cdot \cos\theta_i \, d\omega_i$$

---

## 5. Split Sum Approximation（分裂求和近似）

将渲染方程中的积分**拆分**为两个独立积分的乘积：

$$L_o(x, \omega_o) \approx \underbrace{\int_{\Omega} L_i(\omega_i) \, D(\omega_i, \omega_o) \, d\omega_i}_{\text{Prefiltered Env Map}} \cdot \underbrace{\int_{\Omega} f_r(\omega_i, \omega_o) \cos\theta_i \, d\omega_i}_{\text{Pre-integrated BRDF}}$$

### 5.1 Part 1：预滤波环境贴图（Prefiltered Environment Map）

$$\tilde{L}(\omega_o, \alpha) = \frac{\int_{\Omega} L_i(\omega_i) \, D(\omega_i, \omega_o, \alpha) \, d\omega_i}{\int_{\Omega} D(\omega_i, \omega_o, \alpha) \, d\omega_i}$$

- 依据不同粗糙度 $\alpha$ 预计算环境贴图的模糊版本（不同 mip level）
- 运行时只需根据反射方向和粗糙度查询对应 mip level

### 5.2 Part 2：预积分 BRDF（Pre-integrated BRDF / BRDF LUT）

$$\int_{\Omega} f_r \cos\theta_i \, d\omega_i = F_0 \cdot \text{Scale}(\mu_o, \alpha) + \text{Bias}(\mu_o, \alpha)$$

这张 **BRDF LUT（Look-Up Table）** 预计算后固定，运行时按坐标查询即可。

### 5.3 Split Sum 的适用范围

| 材质类型 | 适用性 | 原因 |
|---------|--------|------|
| Diffuse | 好 | BRDF 低频，误差小 |
| Glossy | 尚可 | BRDF 集中在小区域，近似合理 |
| Mirror | 最好 | BRDF 极度集中，近乎完美 |
| Glossy + 复杂遮挡 | 差 | 忽略了 Visibility 项 |

---

## 6. 环境光照阴影的困难

环境光照下的阴影问题（All-Frequency Shadow）极为困难：

- **Many Light 方法**：将环境光视为大量点光源，每个生成一个 Shadow Map → 代价 $O(N_{\text{light}})$，不可接受
- **采样方法**：Visibility term 未知，无法做重要性采样

**现实情况**：实时渲染中，环境光照下的精确阴影**目前无法完全实时实现**。近似方法（如 Ambient Occlusion）只能处理局部遮挡。

---

## 7. 关键术语表

| 术语 | 说明 |
|------|------|
| **SDF** | Signed Distance Field/Function，有向距离场 |
| **Ray Marching** | 光线步进，用于 SDF 场景求交 |
| **Sphere Tracing** | 利用 SDF 安全球进行加速 Ray Marching |
| **IBL** | Image-Based Lighting，基于图像的环境光照 |
| **Split Sum** | 将渲染方程积分拆分为两部分的近似方法 |
| **Prefiltered Env Map** | 预滤波环境贴图，按粗糙度存储不同模糊度 |
| **BRDF LUT** | 预积分 BRDF 查找表（2D 纹理） |
| **Many Light** | 将环境光视为多个点光源的思路 |
| **Visibility Term** | 可见性项，表示着色点到光源的遮挡情况 |
| **All-Frequency Shadow** | 全频阴影，环境光照下的精确阴影（极难实时实现） |

---

## 总结

1. **SDF** 通过"安全球"思想实现高效的 Ray Marching，时间复杂度远优于固定步长方法。
2. **SDF Soft Shadows** 通过步进过程中角度的最小值近似估计可见性，参数 $k$ 控制软硬程度。
3. SDF 的主要代价是**存储**（三维体积纹理）和**不支持形变物体**。
4. **IBL 的 Split Sum** 将渲染方程分为预滤波环境贴图 × 预积分 BRDF，实现高效 IBL shading。
5. 环境光照下的精确阴影在实时渲染中**目前没有完美解**，需要结合 AO 等近似方法。
