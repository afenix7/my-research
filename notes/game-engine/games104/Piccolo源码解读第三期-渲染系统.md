# Piccolo 源码解读第三期：渲染系统

> 来源：Games104 官方 Piccolo 引擎源码解读系列
> 代码版本：v0.0.9（在前两期基础上继续扩展）
> 主讲：Piccolo 主要开发者

---

## 目录

1. [前置知识要求](#前置知识要求)
2. [渲染系统概览](#渲染系统概览)
3. [RenderSystem 的初始化](#rendersystem-的初始化)
4. [每帧渲染流程详解](#每帧渲染流程详解)
5. [RenderPass 基类结构](#renderpass-基类结构)
6. [Sub-pass 与 Vulkan Render Pass](#sub-pass-与-vulkan-render-pass)
7. [Color Grading Pass 完整分析](#color-grading-pass-完整分析)
8. [Color Grading Shader 实现](#color-grading-shader-实现)
9. [使用 RenderDoc 调试渲染问题](#使用-renderdoc-调试渲染问题)
10. [实战：添加暗角（Vignette）Pass](#实战添加暗角vignette-pass)
11. [关键术语表](#关键术语表)
12. [总结](#总结)

---

## 前置知识要求

本期内容需要具备：

1. 对 **Vulkan API** 有一定了解
2. 能编写简单的 **GLSL Shader**（vertex shader / fragment shader）
3. 推荐工具：**RenderDoc**（图形调试工具，可抓帧查看每个 pass 的输入输出）

---

## 渲染系统概览

Piccolo 的渲染系统名为 `RenderSystem`，整体设计思路：

```
渲染系统
  └── RenderPipeline（渲染管线）
        └── MainCameraPass（主相机 Pass）
              ├── Sub-pass 0: DirectionalLightShadowPass
              ├── Sub-pass 1: PointLightShadowPass
              ├── Sub-pass 2: GBufferPass（延迟渲染）
              ├── Sub-pass 3: DeferredLightingPass
              ├── Sub-pass 4: ForwardLightingPass
              ├── Sub-pass 5: ToneMappingPass
              ├── Sub-pass 6（新增）: ColorGradingPass  ← 本期讲解
              ├── Sub-pass 7（新增）: VignettePass      ← 本期添加
              ├── Sub-pass 8: UIPass
              └── Sub-pass 9: CombineUIPass
```

---

## RenderSystem 的初始化

```
start_systems() → RenderSystem::initialize()
  ├── RenderResource 初始化
  │     └── 全局贴图（如默认纹理）
  ├── RenderCamera 初始化
  ├── RenderScene 初始化
  │     └── 场景光照信息
  └── RenderPipeline 初始化
        └── 调用各个 pass 的 initialize() 函数
```

---

## 每帧渲染流程详解

每帧在 `render_tick()` 中执行，流程如下：

### Step 1：process_swap_data()

从逻辑层获取需要更新的数据，数据结构为 `RenderSwapData`：

```cpp
struct RenderSwapData {
    // 关卡级别的资源更新
    std::optional<LevelResourceDesc> level_resource_desc;
    //   └── 新的天空盒贴图
    //   └── Color Grading 的 LUT 贴图

    // 游戏对象的增删
    std::optional<std::vector<GameObjectResourceDesc>> game_object_resource;
    std::optional<std::vector<GameObjectID>>           game_object_to_delete;

    // 相机参数更新
    std::optional<RenderCameraSwapData> camera_swap_data;

    // 粒子系统相关
    std::optional<std::vector<ParticleEmitterDesc>> particle_emitter_to_create;
    std::optional<std::vector<ParticleEmitterID>>   particle_emitter_to_tick;
    std::optional<std::vector<ParticleEmitterTransform>> particle_emitter_transforms;
};
```

`process_swap_data()` 根据上述结构体的内容进行对应的更新（增删游戏对象、更新相机等）。

> 注：这里的 "swap" 并不准确，实际上只是**渲染层从逻辑层拉取数据**，并非双向交换。

### Step 2：prepare_context()

调用图形 API 进行渲染准备工作（如 begin command buffer、begin render pass 等 Vulkan 操作）。

### Step 3：准备每帧 Pass 共用的数据

设置帧级别的 uniform buffer 等共享资源。

### Step 4：update_visible_objects()

为各个 Pass 筛选各自所需的具体数据（可见物体列表、光源等），填充 `visible_nodes`。

### Step 5：prepare_pass_data()

调用各个 pass 的 `prepare_pass_data()` 函数，进行数据准备和上传。

### Step 6：执行渲染

```cpp
// 判断使用前向渲染或延迟渲染
if (use_forward) {
    forward_render(rhi);
} else {
    deferred_render(rhi);
}
```

**前向渲染（Forward）：**

```
forward_render()
  ↓ 获取渲染功能对象
  ↓ main_camera_pass.draw_forward()
      ↓ 依次调用各个 sub-pass 的 draw() 函数
```

**延迟渲染（Deferred）：**

```
deferred_render()
  ↓ main_camera_pass.draw()
      ↓ draw_g_buffer()         ← 第一遍：将几何信息写入 G-Buffer
      ↓ deferred_lighting()     ← 利用 G-Buffer 进行光照计算
      ↓ forward_lighting()      ← 处理透明物体等需要前向渲染的部分
      ↓ tone_mapping()
      ↓ color_grading()
      ↓ vignette()              ← 新增
      ↓ ui / combine_ui
```

---

## RenderPass 基类结构

所有 Pass（包括 `ColorGradingPass`）都继承自 `RenderPass` 基类：

```cpp
class RenderPass {
public:
    virtual void initialize(const RenderPassInitInfo& init_info) = 0;
    virtual void draw() = 0;

protected:
    // 全局资源（如全局 UBO、IBL 贴图等）
    GlobalRenderResource* m_global_render_resource { nullptr };

    // Shader 中输入输出资源的描述符布局
    // 对应 Vulkan VkDescriptorSetLayout
    DescriptorInfo m_descriptor_info;

    // 执行管线的信息（包含 pipeline state object）
    std::vector<RenderPipeline> m_render_pipelines;

    // 该 Pass 可见的物体（从 update_visible_objects() 填充）
    VisibleNodes m_visible_nodes;
};
```

---

## Sub-pass 与 Vulkan Render Pass

### Sub-pass 概念（Vulkan 特有）

Vulkan 的 `VkRenderPass` 对象可以包含多个**串行执行**的 sub-pass：

```
VkRenderPass (main_camera_pass)
  ├── sub-pass 0 (g_buffer_pass)
  │     output ──────────────────┐
  ├── sub-pass 1 (deferred_lighting_pass)  ← input 来自 sub-pass 0
  │     output ──────────────────┐
  ├── sub-pass 2 (tone_mapping_pass)       ← input 来自 sub-pass 1
  │     output ──────────────────┐
  ├── sub-pass 3 (color_grading_pass)      ← input 来自 sub-pass 2
  │     output ──────────────────┐
  └── sub-pass 4 (vignette_pass)           ← input 来自 sub-pass 3（新增）
```

前一个 sub-pass 的输出**直接作为**后一个 sub-pass 的输入，在 Vulkan 中这可以避免 GPU 回读（render-to-texture）的带宽开销。

### Sub-pass 间的缓冲区（odd/even buffer）

Sub-pass 之间通过 `odd_buffer` / `even_buffer` 交替传递渲染结果（ping-pong buffer 设计）：

```
sub-pass N 写入 odd_buffer
  → sub-pass N+1 读取 odd_buffer，写入 even_buffer
  → sub-pass N+2 读取 even_buffer，写入 odd_buffer
  → ...
```

添加新 sub-pass 时需要正确维护 odd/even 的对应关系。

### Sub-pass dependency

每增加一个 sub-pass，需要在 `VkSubpassDependency` 数组中添加对应的 dependency，并将数组大小更新（如从 8 改为 9）。

---

## Color Grading Pass 完整分析

### 定义

```cpp
// color_grading_pass.h
class ColorGradingPass : public RenderPass {
public:
    void initialize(const ColorGradingPassInitInfo& init_info) override;
    void draw() override;
    void update_after_framebuffer_recreate();

private:
    void setup_descriptor_set_layout();
    void setup_pipelines();
    void setup_descriptor_set();
};
```

### initialize() 四步流程

#### Step 1：setup_descriptor_set_layout()

设置 Shader 输入资源的**描述符布局**（Vulkan `VkDescriptorSetLayout`）：

```
Binding 0: tone mapping pass 的输出贴图（input attachment）
Binding 1: Color Grading 的 LUT（Look Up Table）贴图（combined image sampler）
```

#### Step 2：setup_pipelines()

创建 **Graphics Pipeline**（图形管线），配置：

| 配置项 | 说明 |
|--------|------|
| Vertex Shader | `post_process.vert`（后处理通用顶点着色器） |
| Fragment Shader | `color_grading.frag`（Color Grading 片段着色器） |
| Viewport / Scissor | 视口和裁剪范围 |
| Rasterization State | 面朝向、剔除模式等 |
| Blend State | 混合模式（Color Grading 无需混合） |
| Depth Stencil State | 深度/模板设置 |

`setup_descriptor_set_layout()` 的结果也用于 pipeline 创建（`VkPipelineLayout`）。

#### Step 3：setup_descriptor_set()

分配并绑定**实际使用的资源**（`VkDescriptorSet`），将具体的贴图 handle 与描述符布局中的 binding 对应起来。

> `descriptor_set` = 资源 handle 的集合，是描述符布局的具体实例

#### Step 4：update_after_framebuffer_recreate()

窗口大小变化时（framebuffer recreate），需要更新与帧缓冲尺寸相关的资源绑定。

### draw() 函数

提交绘制命令（`vkCmdDraw`），执行全屏三角形（或两个三角形）的绘制，触发 fragment shader 对每个像素进行 color grading。

---

## Color Grading Shader 实现

### LUT（Look Up Table）的结构

Color Grading LUT 是一张特殊排布的贴图：

```
贴图尺寸：1024 × 32 像素
结构：由 32 张 32×32 的小贴图横向排列组成

3D 可视化：
  这 32 张小贴图可以看作一个 32×32×32 的立方体
  X 轴 = R 通道（每小块内横向）
  Y 轴 = G 通道（每小块内纵向）
  Z 轴 = B 通道（由哪张小块决定）
```

Color grading 的本质：把原始 RGB 颜色坐标映射到 LUT 立方体中，取出目标颜色。

### Fragment Shader 实现（`color_grading.frag`）

```glsl
// color_grading.fragment（伪代码+注释）

// 输入
uniform sampler2D in_color;          // tone mapping pass 的输出
uniform sampler2D color_grading_lut; // LUT 贴图

void main() {
    vec3 color = texture(in_color, uv).rgb;

    // 1. 根据 B 通道找到需要采样的两张小贴图的 index
    float lut_height = textureSize(color_grading_lut, 0).y;  // = 32
    float blue_index = color.b * (lut_height - 1.0);
    int   blue_index_floor = int(floor(blue_index));   // 下界 tile index
    int   blue_index_ceil  = int(ceil(blue_index));    // 上界 tile index

    // 2. 换算出在 LUT 贴图中的 UV 坐标
    //    每个 tile 宽 = lut_height，贴图总宽 = lut_height * lut_height
    float tile_size = lut_height;
    float total_width = tile_size * lut_height;  // = 1024

    // 在 floor tile 中采样
    vec2 uv_floor;
    uv_floor.x = (float(blue_index_floor) * tile_size + color.r * (tile_size - 1.0)) / total_width;
    uv_floor.y = color.g;
    vec3 color_floor = texture(color_grading_lut, uv_floor).rgb;

    // 在 ceil tile 中采样
    vec2 uv_ceil;
    uv_ceil.x = (float(blue_index_ceil) * tile_size + color.r * (tile_size - 1.0)) / total_width;
    uv_ceil.y = color.g;
    vec3 color_ceil = texture(color_grading_lut, uv_ceil).rgb;

    // 3. 在两次采样结果之间插值
    float mix_factor = blue_index - float(blue_index_floor);
    out_color = vec4(mix(color_floor, color_ceil, mix_factor), 1.0);
}
```

> **常见错误**：只采样一次（只用 floor 或 ceil），会导致 B 通道方向出现插值错误。

### 调试问题：Mip Map 导致的线条

**现象**：运行后画面出现奇怪的横线条。

**原因**：Color Grading LUT 贴图默认生成了 mip map，导致 LUT 精度不足。

**修复**：将 LUT 贴图的 `mip_levels` 从默认值 0（自动计算）改为 1（只有一层）：

```cpp
// 找到 LUT 贴图创建的地方
VkImageCreateInfo image_create_info = {};
image_create_info.mipLevels = 1;  // 改为 1，禁用 mip map
```

---

## 使用 RenderDoc 调试渲染问题

### 基本使用流程

1. 打开 RenderDoc
2. 在 Launch 中选择 `piccolo_editor` 可执行文件
3. 启动后按 **F2** 抓取当前帧
4. 在左侧命令列表中找到目标 pass（如 `color_grading`）
5. 查看该 pass 的 **Input** 和 **Output** 贴图

通过 RenderDoc 可以直观确认：
- 每个 pass 的输入贴图是否正确（是否来自上一个 pass 的输出）
- 贴图内容、mip level 是否符合预期
- 缓冲区的 odd/even 是否传递正确

---

## 实战：添加暗角（Vignette）Pass

暗角效果：屏幕边缘变暗，中心正常，常用于营造电影感。

### Step 1：创建 Pass 代码文件

复制 `color_grading_pass.h/.cpp`，重命名为 `vignette_pass.h/.cpp`，然后批量将文件内所有 `color_grading` 替换为 `vignette`（`ColorGrading` 替换为 `Vignette`）。

### Step 2：在 Sub-pass 枚举中注册

```cpp
// main_camera_pass.h
enum class MainCameraSubPassType {
    // ...
    COLOR_GRADING_PASS,
    VIGNETTE_PASS,   // 新增，序号为 6（紧接 color grading 后）
    UI_PASS,
    COMBINE_UI_PASS,
};
```

### Step 3：维护 Sub-pass Dependency

```cpp
// 原来：8 个 dependency
// 新增 vignette 后：需要 9 个 dependency
std::array<VkSubpassDependency, 9> dependencies;
// 在 color grading dependency 之后添加 vignette dependency
```

### Step 4：创建 Vignette Shader

#### Vignette Fragment Shader（`vignette.frag`）

```glsl
// vignette.fragment
layout(input_attachment_index = 0, set = 0, binding = 0) uniform subpassInput in_color;
layout(location = 0) in  vec2 in_uv;   // 需要额外的 UV 输入
layout(location = 0) out vec4 out_color;

// 暗角参数
const float vignette_radius    = 0.75;  // 暗角开始的距离（从中心）
const float vignette_smoothness = 0.3;  // 过渡的柔和程度

void main() {
    vec3 color = subpassLoad(in_color).rgb;

    // 计算 UV 到屏幕中心的距离
    vec2 center = vec2(0.5, 0.5);
    float dist  = length(in_uv - center);

    // 用 smoothstep 计算暗角强度
    float vignette = smoothstep(vignette_radius, vignette_radius - vignette_smoothness, dist);

    out_color = vec4(color * vignette, 1.0);
}
```

#### Vignette Vertex Shader（`vignette.vert`）

Color Grading 使用通用的 `post_process.vert`，但 Vignette 需要 UV 坐标，所以需要创建专用的顶点着色器 `vignette.vert`：

```glsl
// vignette.vert（在 post_process.vert 基础上添加 UV 输出）
layout(location = 0) out vec2 out_uv;

void main() {
    // 生成全屏三角形
    vec2 positions[3] = vec2[](
        vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0)
    );
    vec2 uvs[3] = vec2[](
        vec2(0.0, 0.0), vec2(2.0, 0.0), vec2(0.0, 2.0)
    );
    gl_Position = vec4(positions[gl_VertexIndex], 0.0, 1.0);
    out_uv = uvs[gl_VertexIndex];
}
```

### Step 5：修改 VignettePass 的 setup_pipelines()

```cpp
// 使用 vignette 专用的顶点和片段着色器
pipeline_info.vertex_shader   = "vignette.vert.h";
pipeline_info.fragment_shader = "vignette.frag.h";
```

### Step 6：修改 descriptor set layout

Vignette Pass **不需要 LUT 贴图**，只需要上一个 pass 的输出作为输入：

```cpp
// 只保留 binding 0（上一 pass 的 color 输出）
// 删除 binding 1（LUT 贴图）
```

### Step 7：修复 odd/even buffer 传递

调试时可能发现 VignettePass 的输入不是 ColorGradingPass 的输出，而是更早的贴图。需要检查并修正 odd/even 缓冲区的对应关系，确保链式传递正确。

### 验证结果

编译运行后，画面边缘出现黑色渐变（暗角效果），说明新 Pass 已成功添加并生效。

---

## 关键术语表

| 术语 | 说明 |
|------|------|
| `RenderSystem` | Piccolo 的渲染系统，在 RuntimeGlobalContext 中初始化和 tick |
| `RenderPipeline` | 渲染管线，持有所有 Pass，负责组织每帧的渲染流程 |
| `RenderPass` | 所有渲染 Pass 的基类，定义 initialize 和 draw 接口 |
| `MainCameraPass` | 主相机 Pass，是整个场景渲染的核心，包含多个 sub-pass |
| Sub-pass | Vulkan 特有概念，VkRenderPass 内的串行渲染步骤，可高效传递前一步的输出 |
| `RenderSwapData` | 渲染层从逻辑层获取的每帧更新数据结构 |
| `process_swap_data()` | 处理逻辑层传来的数据（增删对象、更新相机等） |
| `update_visible_objects()` | 为各 Pass 筛选可见物体和资源 |
| `prepare_pass_data()` | 各 Pass 进行数据上传和准备 |
| Forward Rendering | 前向渲染：每个物体直接计算所有光照 |
| Deferred Rendering | 延迟渲染：先将几何信息存入 G-Buffer，再统一进行光照计算 |
| G-Buffer | Geometry Buffer，存储延迟渲染所需的几何信息（法线、深度、Albedo 等） |
| `draw_g_buffer()` | 延迟渲染的第一遍，将场景几何信息写入 G-Buffer |
| `descriptor_set_layout` | Vulkan 中描述 Shader 如何使用资源（资源类型和绑定位置）的布局对象 |
| `descriptor_set` | 资源 handle 的集合，是 descriptor_set_layout 的具体实例 |
| `VkPipeline` | Vulkan 的管线状态对象，包含 Shader、视口、混合等所有渲染状态 |
| `update_after_framebuffer_recreate()` | 窗口大小变化时更新与帧缓冲相关的资源绑定 |
| Color Grading | 调色/颜色分级，将原始颜色映射到目标色彩空间 |
| LUT（Look Up Table） | 颜色查找表，Color Grading 使用 1024×32 的特殊贴图 |
| Tone Mapping | 色调映射，将 HDR 颜色映射到 LDR 显示范围（Color Grading 的上一个 pass） |
| `mip_levels` | 贴图 mip 层级数，LUT 需要设为 1 以避免采样精度损失 |
| odd/even buffer | sub-pass 间交替传递渲染结果的 ping-pong 缓冲区 |
| Vignette | 暗角效果，屏幕边缘渐变变暗 |
| RenderDoc | 图形调试工具，可抓帧并查看每个 pass 的 input/output |
| `subpassLoad()` | GLSL 内置函数，读取 input attachment（即上一个 sub-pass 的输出） |
| `smoothstep()` | GLSL 内置函数，平滑插值，常用于实现渐变效果 |
| GLSL | OpenGL Shading Language，Vulkan 使用的着色器语言（编译为 SPIR-V） |

---

## 总结

### 渲染系统架构要点

Piccolo 的渲染系统围绕 **Pass** 的概念组织：

1. `RenderSystem` 初始化时创建 `RenderPipeline`，Pipeline 初始化所有 Pass
2. 每帧先从逻辑层同步数据（`process_swap_data`），再筛选可见物体，最后调用各 Pass 绘制
3. 所有 Pass 都是 `MainCameraPass` 的 sub-pass，利用 Vulkan sub-pass 机制高效传递数据
4. Pass 间通过 odd/even buffer 交替传递渲染结果

### 添加新 Pass 的完整流程

```
1. 创建 PassName.h / PassName.cpp（仿照 ColorGradingPass）
2. 在 MainCameraSubPassType 枚举中添加新 Pass 序号
3. 在 dependency 数组中添加新的 subpass dependency，数组大小加 1
4. 创建对应的 .vert 和 .frag shader 文件
5. 在 CMake 构建中添加新文件（触发 shader 编译和代码引入）
6. 修正 odd/even buffer 传递关系
7. 根据 Pass 的具体需求调整 descriptor_set_layout（去掉不需要的 binding）
```

### 当前设计的不足与思考题

来自视频末尾的思考题：

1. **添加 Pass 太繁琐**：目前手工添加需要修改多处（枚举、dependency 数组、odd/even buffer 等），能否设计更自动化的框架？
2. **Shader 硬编码**：当前 Shader 在 CMake 构建时编译并硬编码进各 Pass。如何将 Shader 设计为一种可以在运行时加载的资产？（类似 Unreal 的 Material 系统）
