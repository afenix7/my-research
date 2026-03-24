# GAMES202 第2讲：渲染管线回顾与 OpenGL 基础

> 本讲是对 GAMES101 渲染管线的系统回顾，并引入 OpenGL/GLSL 编程模型，为后续实时渲染作业奠定基础。

---

## 1. 渲染管线（Rendering Pipeline）回顾

### 1.1 整体流程

```
三维几何数据（顶点 + 三角形）
  ↓
顶点处理（Vertex Processing）：MVP 变换
  ↓
光栅化（Rasterization）：三角形 → 片段（Fragment）
  ↓
片段处理（Fragment Processing）：着色 + 纹理
  ↓
输出合并（Output Merging）：深度测试、混合
  ↓
帧缓冲（Framebuffer）→ 屏幕显示
```

### 1.2 顶点处理：MVP 变换

对每个顶点依次应用：
1. **Model 矩阵**：物体空间 → 世界空间
2. **View 矩阵**：世界空间 → 相机空间
3. **Projection 矩阵**：相机空间 → 裁剪空间（NDC）

变换后，三角形从三维坐标映射到屏幕平面。

### 1.3 光栅化（Rasterization）

将连续的三角形**离散化**为屏幕上的像素（片段）：

$$\text{Fragment} = \{(x, y) \in \mathbb{Z}^2 \mid (x, y) \text{ 在三角形内}\}$$

- 使用**重心坐标（Barycentric Coordinates）**插值三角形内部属性（颜色、法线、UV 等）

对于三角形三顶点 $A, B, C$，内部点 $P$ 满足：
$$P = \alpha A + \beta B + \gamma C, \quad \alpha + \beta + \gamma = 1, \quad \alpha, \beta, \gamma \geq 0$$

### 1.4 深度测试（Z-Buffer）

维护一个与帧缓冲等大的深度缓存（**Z-Buffer**），对每个片段：

```
if z_fragment < z_buffer[x, y]:
    z_buffer[x, y] = z_fragment  // 更新最小深度
    color_buffer[x, y] = shade(fragment)  // 着色
```

正确处理遮挡关系（前面的物体遮挡后面的物体）。

### 1.5 Blinn-Phong 着色模型

经验式着色模型，将光照分为三项：

$$L = L_a + L_d + L_s$$

$$L_a = k_a \cdot I_a$$

$$L_d = k_d \cdot \frac{I}{r^2} \cdot \max(0, \mathbf{n} \cdot \mathbf{l})$$

$$L_s = k_s \cdot \frac{I}{r^2} \cdot \max(0, \mathbf{n} \cdot \mathbf{h})^p$$

其中：
- $L_a$：环境光（Ambient）— 近似间接光照
- $L_d$：漫反射（Diffuse） — 与视角无关
- $L_s$：高光（Specular）— 与视角相关，$\mathbf{h} = \text{normalize}(\mathbf{l} + \mathbf{v})$ 为半程向量
- $p$：高光指数（shininess），越大高光越集中

局限：环境光项是常数近似，无法正确模拟**全局光照**和**间接光照**。

### 1.6 纹理映射（Texture Mapping）

通过 **UV 坐标**将 2D 纹理贴图映射到 3D 物体表面：
- 顶点上定义 UV 坐标
- 使用重心坐标插值得到片段的 UV
- 在纹理中查询对应颜色值

---

## 2. GPU 与并行计算

GPU 运算速度快的原因：**极高的并行度**——不是每个核心多快，而是拥有极多核心同时工作。

OpenGL 管线本质上在 GPU 上并行执行片段着色器，每个片段独立计算。

---

## 3. OpenGL 编程模型

### 3.1 OpenGL 是什么

**OpenGL** 是一套在 CPU 端执行的图形 API，用于控制 GPU 执行渲染管线。

- CPU 端调用 OpenGL API，**调度 GPU** 完成渲染
- 跨平台（Windows / Linux / macOS）
- 与 DirectX 相比版本更平滑连续

### 3.2 OpenGL vs DirectX

| 特性 | OpenGL | DirectX |
|------|--------|---------|
| 平台 | 跨平台 | 仅 Windows |
| 版本策略 | 平滑演进 | 明显代际（DX9/DX10/DX11/DX12） |
| API 风格 | C 风格（无面向对象） | 更现代 |
| 现代替代 | Vulkan | DX12 |

### 3.3 OpenGL 渲染流程（CPU 端）

```cpp
// 1. 设置变换矩阵（MVP）
glUniformMatrix4fv(mvp_loc, 1, GL_FALSE, mvp.data());

// 2. 指定顶点缓冲
glBindVertexArray(vao);
glBindBuffer(GL_ARRAY_BUFFER, vbo);

// 3. 绑定纹理
glBindTexture(GL_TEXTURE_2D, texture_id);

// 4. 绑定 Shader Program
glUseProgram(shader_program);

// 5. 执行绘制
glDrawArrays(GL_TRIANGLES, 0, vertex_count);
```

### 3.4 GLSL Shader 编程

**顶点着色器（Vertex Shader）**：对每个顶点执行，完成坐标变换

```glsl
// vertex shader
uniform mat4 uMVP;
attribute vec3 aPosition;
attribute vec2 aTexCoord;
varying vec2 vTexCoord;

void main() {
    gl_Position = uMVP * vec4(aPosition, 1.0);
    vTexCoord = aTexCoord;
}
```

**片段着色器（Fragment Shader）**：对每个片段执行，完成着色

```glsl
// fragment shader
precision mediump float;
uniform sampler2D uTexture;
varying vec2 vTexCoord;

void main() {
    gl_FragColor = texture2D(uTexture, vTexCoord);
}
```

### 3.5 Shadow Map 的 OpenGL 实现

Shadow Map 需要**两趟渲染（Two-Pass）**：

**第一趟（Light Pass）**：从光源视角渲染场景，记录深度到深度纹理

```glsl
// shadow map generation fragment shader
void main() {
    gl_FragColor = vec4(gl_FragCoord.z);
}
```

**第二趟（Camera Pass）**：从摄像机视角渲染，利用 shadow map 判断遮挡

```glsl
// shadow test in fragment shader
float shadow = 0.0;
vec4 shadowCoord = uLightMVP * vec4(fragPos, 1.0);
shadowCoord.xyz /= shadowCoord.w;  // 透视除法
shadowCoord = shadowCoord * 0.5 + 0.5;  // [-1,1] -> [0,1]

float closestDepth = texture2D(uShadowMap, shadowCoord.xy).r;
float currentDepth = shadowCoord.z;
shadow = (currentDepth - bias > closestDepth) ? 0.0 : 1.0;
```

---

## 4. Shadow Map 基础原理

### 4.1 算法思想

```
Pass 1（光源视角）：
  对每个光源，渲染场景，记录每像素最小深度 → Shadow Map

Pass 2（相机视角）：
  对每个着色点 x：
    1. 将 x 变换到光源空间，得到对应 Shadow Map 坐标 (u, v) 和深度 d_x
    2. 查询 Shadow Map 中存储的最小深度 d_min = ShadowMap(u, v)
    3. 若 d_x > d_min + bias → x 在阴影中
       否则 → x 被光源直接照射
```

### 4.2 Shadow Map 的常见问题

1. **自遮挡（Shadow Acne）**：深度精度有限导致物体自身产生错误阴影。解决方案：添加 **bias**（偏移量）。
2. **悬浮阴影（Peter Panning）**：bias 过大时阴影与物体脱离。
3. **锯齿感（Aliasing）**：Shadow Map 分辨率不足时出现像素化阴影边缘。

---

## 5. 关键术语表

| 术语 | 说明 |
|------|------|
| **Fragment** | 片段，光栅化后待着色的基本单元（接近像素） |
| **Z-Buffer** | 深度缓冲，记录每像素最近的深度值 |
| **Barycentric Coordinates** | 重心坐标，三角形内插值用 |
| **Blinn-Phong** | 经验式着色模型，含漫反射、镜面高光、环境光 |
| **GLSL** | OpenGL Shading Language，GPU 着色语言 |
| **Vertex Shader** | 顶点着色器，处理顶点变换 |
| **Fragment Shader** | 片段着色器，处理逐像素着色 |
| **Shadow Map** | 阴影贴图，基于深度比较的实时阴影方法 |
| **Shadow Acne** | 阴影粉刺，自遮挡导致的错误阴影条纹 |
| **Bias** | 深度偏移量，用于消除自遮挡 |
| **Two-Pass Rendering** | 双趟渲染，Shadow Map 需要从光源和相机各渲染一次 |

---

## 总结

1. 实时渲染管线核心步骤：**MVP变换 → 光栅化 → 深度测试 → 着色**。
2. GPU 通过大规模并行实现实时速度，GLSL 是控制 GPU 的着色语言。
3. Blinn-Phong 是经典的经验式着色模型，不能处理全局效果（阴影、间接光照）。
4. Shadow Map 是实时阴影的基础，需要两趟渲染，存在自遮挡和锯齿等问题。
5. OpenGL 作为跨平台图形 API，是本课程实验框架的底层支撑。
