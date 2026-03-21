# Adria 技术分析：Render Graph 与渲染系统

## 项目概述

Adria 是一个现代化的 DirectX 12 渲染引擎，专注于实时候娟渲染和图形研究。代码质量高，架构清晰，非常适合学习 Render Graph 的基本实现。

**官方资源：**
- GitHub Repository: [https://github.com/mateeeeeee/Adria](https://github.com/mateeeeeee/Adria)
- 支持：仅 DirectX 12

---

## 1. Render Graph 编译

### 架构 / 实现

Adria 的 Render Graph 编译流程相对简洁，分为以下步骤：

**源码位置：** `Adria/RenderGraph/RenderGraph.cpp:107-L139` [mateeeeeee/Adria → Adria/RenderGraph/RenderGraph.cpp]

```cpp
void RenderGraph::Compile()
{
    ZoneScopedN("RenderGraph::Compile");
    BuildAdjacencyLists();
    TopologicalSort();
    if (g_UseDependencyLevels)
    {
        BuildDependencyLevels();
    }
    CullPasses();
    ResolveAsync();
    ResolveEvents();
    CalculateResourcesLifetime();
    for (DependencyLevel& dependency_level : dependency_levels)
    {
        dependency_level.Setup();
    }
}
```

### 编译步骤详解

1. **构建邻接表 (`BuildAdjacencyLists`)** - 查找 pass 间的读写依赖，建立依赖图
   - 对于每对 pass (i, j), i < j，如果 i 写入了 j 读取的资源，则添加边 i → j

2. **拓扑排序 (`TopologicalSort`)** - DFS 拓扑排序保证依赖顺序

3. **构建依赖级别 (`BuildDependencyLevels`)** - 按照最长路径将 pass 分组到不同级别，同一级别可以并行（但当前实现仍是顺序执行）

4. **Pass 剔除 (`CullPasses`)** - 基于引用计数剔除无用 passes
   - 使用反向迭代，从无引用的资源开始，逐级剔除未使用的 passes

5. **异步解析 (`ResolveAsync`)** - 处理 AsyncCompute pass 的跨队列同步点

6. **事件解析 (`ResolveEvents`)** - 处理 GPU 性能事件区间管理

7. **计算资源生命周期 (`CalculateResourcesLifetime`)** - 确定每个资源在哪一个 pass 之后可以释放回池

### 关键特性

- **基于依赖级别的分组** - 同一依赖级别内的 passes 之间没有依赖，理论上可以并行执行
- **即时 Pass 剔除** - 减少无用工作，节省 GPU 时间
- **资源生命周期管理** - 启用池分配，避免重复分配

---

## 2. Barrier 处理

### 架构 / 实现

Adria 在每个 **DependencyLevel** 执行前处理所有 Barrier，按照 DependencyLevel 批处理。

**源码位置：** `Adria/RenderGraph/RenderGraph.cpp:1399-L1494` [mateeeeeee/Adria → Adria/RenderGraph/RenderGraph.cpp]

```cpp
void RenderGraph::DependencyLevel::PreExecute(GfxCommandList* cmd_list)
{
    // 创建资源（如果不是导入外部资源）
    for (RGTextureId tex_id : texture_creates) { /* ... */ }
    for (RGBufferId buf_id : buffer_creates) { /* ... */ }

    // 处理纹理屏障
    for (auto const& [tex_id, state] : texture_state_map) {
        RGTexture* rg_texture = rg.GetRGTexture(tex_id);
        GfxTexture* texture = rg_texture->resource;
        if (texture_creates.contains(tex_id)) {
            if (!HasFlag(texture->GetDesc().initial_state, state)) {
                cmd_list->TextureBarrier(*texture, texture->GetDesc().initial_state, state);
            }
        }
        else {
            // 向前查找上一个依赖级别中最后的状态
            for (Int32 j = (Int32)level_index - 1; j >= 0; --j) {
                auto& prev_dependency_level = rg.dependency_levels[j];
                if (prev_dependency_level.texture_state_map.contains(tex_id)) {
                    GfxResourceState prev_state = prev_dependency_level.texture_state_map[tex_id];
                    if (prev_state != state) {
                        cmd_list->TextureBarrier(*texture, prev_state, state);
                    }
                    break;
                }
            }
        }
        // 处理导入外部资源的初始状态转换
        // ...
    }

    // 同样处理缓冲屏障
    // ...
    cmd_list->FlushBarriers();
}
```

### 关键设计选择

1. **按依赖级别批处理** - 同一个级别所有屏障一次性提交，减少 GPU 命令数量

2. **状态追踪** - 每个 pass 根据读写操作标记资源目标状态

3. **向前查找** - 只有和上一个状态不同才插入屏障，避免冗余

4. **缓存所有 barriers 最后一次性 flush** - 使用 D3D12 多屏障提交优化

### 优缺点

| 优点 | 缺点 |
|------|------|
| 实现简单，容易理解 | 只能按依赖级别排序，无法在同一个队列内重排序 |
| 较少冗余屏障 | 不支持分裂屏障优化 |
| 代码量小 | 跨队列屏障处理较为简单 |

---

## 3. 同步点管理与 Async Compute 实现

### 架构 / 实现

Adria 支持基础的 Async Compute，通过 ResolveAsync 分析并添加同步点。

**源码位置：** `Adria/RenderGraph/RenderGraph.cpp:489-L626` [mateeeeeee/Adria → Adria/RenderGraph/RenderGraph.cpp]

```cpp
void RenderGraph::ResolveAsync()
{
#if GFX_ASYNC_COMPUTE
    if (!RGAsyncCompute.Get())
        return;

    for (RGPassType 类型 = Graphics / Compute / AsyncCompute / Copy) {
        // 查找 AsyncCompute pass 前后需要同步的 graphics pass
        // 对每个读取的资源，向前查找是否 graphics pass 写过
        // 对每个写入的资源，向后查找是否 graphics pass 读过
        // 记录需要同步的点，分配 fence value
    }
}
```

在执行阶段，DependencyLevel 执行时：

- AsyncCompute passes 在 compute 命令队列执行
- Graphics passes 在 graphics 命令队列执行
- 需要同步处，通过 fence 信号 + 等待实现跨队列同步

**源码位置：** `Adria/RenderGraph/RenderGraphPass.h:7-L13` [mateeeeeee/Adria → Adria/RenderGraph/RenderGraphPass.h]

```cpp
enum class RGPassType : Uint8
{
    Graphics,
    Compute,
    AsyncCompute,  // ← 专门标记异步计算 pass
    Copy
};
```

### 执行流程

**源码位置：** `Adria/RenderGraph/RenderGraph.cpp:141-L149` [mateeeeeee/Adria → Adria/RenderGraph/RenderGraph.cpp]

```cpp
void RenderGraph::Execute()
{
    ZoneScopedN("RenderGraph::Execute");
#if RG_MULTITHREADED
    Execute_Multithreaded(); // 尚未实现
#else
    Execute_Singlethreaded(); // CPU 侧单线程执行
#endif
}

void RenderGraph::Execute_Singlethreaded()
{
    pool.Tick();
    RenderGraphExecutionContext exec_ctx{};
    exec_ctx.graphics_cmd_list = gfx->GetGraphicsCommandList();
    exec_ctx.compute_cmd_list = gfx->GetComputeCommandList();

    for (auto& level : dependency_levels) {
        level.Execute(exec_ctx); // 按级别顺序执行，内部处理队列同步
    }
}
```

### 关键特性

- **用户标记** - 需要用户明确将 pass 标记为 `AsyncCompute` 类型
- **简单同步** - 基于读写依赖自动发现需要同步的点，添加 fence 信号/等待
- **复用 DX12 原生命令队列** - GPU 原生异步，CPU 端仍然按顺序提交

### 局限性

- CPU 端仍然是单线程提交命令
- 多线程 CPU 命令生成尚未实现
- 没有高级同步优化（如 SSIS），可能产生冗余同步

---

## 4. RHI (Render Hardware Interface)

### 架构 / 实现

由于 Adria **仅支持 D3D12**，RHI 层相对简洁，是对 D3D12 概念的轻量级面向对象封装。

**源码位置：** `Adria/Graphics/GfxDevice.h:83-L247` [mateeeeeee/Adria → Adria/Graphics/GfxDevice.h]

```cpp
class GfxDevice
{
public:
    virtual GfxCommandQueue* GetCommandQueue(GfxCommandListType type) const = 0;
    virtual GfxFence& GetFence(GfxCommandListType type) = 0;

    // 分离三个队列：Graphics / Compute / Copy
    GfxCommandQueue* GetGraphicsCommandQueue() const;
    GfxCommandQueue* GetComputeCommandQueue() const;
    GfxCommandQueue* GetCopyCommandQueue() const;

    // 每个队列对应一个命令列表池和fence
    // ...
};
```

### 核心抽象

| 抽象层 | 说明 |
|--------|------|
| `GfxDevice` | 设备，管理队列、命令列表分配、资源创建 |
| `GfxCommandList` | 命令列表，支持三种类型 (Graphics/Compute/Copy) |
| `GfxTexture` / `GfxBuffer` | 资源抽象 |
| `GfxPipelineState` | 管线状态对象 |
| `GfxDescriptor` | 描述符句柄 |

### D3D12 具体实现

**源码位置：** `Adria/Graphics/D3D12/D3D12Device.cpp` (69966 行，完整实现 D3D12 设备) [mateeeeeee/Adria → Adria/Graphics/D3D12/D3D12Device.cpp]

- 直接基于 D3D12 原生 API
- 使用描述符堆分配 CPU/GPU 描述符
- 支持动态分配器（线性分配器、环形分配器）

### 设计特点

- **轻量级封装** - 没有过度抽象，直接映射 D3D12 概念
- **多命令队列原生支持** - Graphics + Compute + Copy 三个独立队列
- **基于头文件的接口设计** - 方便扩展

---

## 5. 场景管理

### 架构 / 实现

Adria 使用 **EnTT ECS** 进行场景管理，这是现代 C++ 游戏引擎常用方案。

**源码位置：** `Adria/Rendering/Components.h` [mateeeeeee/Adria → Adria/Rendering/Components.h]

场景组织：
- 每个物体是 ECS 实体
- 材质、网格、变换等作为组件

### 渲染流程中的场景数据处理

**源码位置：** `Adria/Rendering/Renderer.h:92-L108` [mateeeeeee/Adria → Adria/Rendering/Renderer.h]

```cpp
enum class SceneBufferType
{
    SceneBuffer_Light,
    SceneBuffer_Mesh,
    SceneBuffer_Material,
    SceneBuffer_Instance,
    SceneBuffer_Count
};
struct SceneBuffer
{
    std::unique_ptr<GfxBuffer>  buffer;
    GfxDescriptor                buffer_srv;
    Uint32                        buffer_srv_gpu_index;
};
std::array<SceneBuffer, SceneBuffer_Count> scene_buffers;
```

每帧更新 GPU 场景缓冲区：
- 将光源、网格、材质、实例数据上传到 GPU 常量缓冲
- GPU 侧通过索引访问这些数据

### GPU 驱动绘制 (GPUDrivenGBufferPass)

Adria 支持 GPU 驱动的渲染：

- 在 GPU 完成截锥剔除
- 实例化绘制，减少 CPU 开销

**源码位置：** `Adria/Rendering/GPUDrivenGBufferPass.cpp` (40KB) [mateeeeeee/Adria → Adria/Rendering/GPUDrivenGBufferPass.cpp]

### 场景加载

**源码位置：** `Adria/Rendering/SceneLoader.h/cpp` [mateeeeeee/Adria → Adria/Rendering/SceneLoader.cpp] (41KB)

- 支持加载 glTF 场景
- 处理网格、材质、节点转换

---

## 6. 材质系统

### 架构 / 实现

Adria 材质系统相对简单，材质数据存储在 GPU 结构化缓冲区中。

**源码位置：** `Adria/Rendering/ShaderStructs.h` [mateeeeeee/Adria → Adria/Rendering/ShaderStructs.h]

```hlsl
struct MaterialGPU
{
    float4 baseColor;
    float metallic;
    float roughness;
    float ior;
    float transmission;
    int32 baseColorTexIndex;
    int32 normalTexIndex;
    // ... 其他属性
};
```

### 设计要点

- 每个材质对应一个 GPU 侧结构体
- 所有材质存储在一个大的结构化缓冲区
- 通过索引在着色器中访问
- 纹理句柄通过索引查找

### 特点

- **简单直接** - 满足现代延迟渲染需求
- **GPU 访问友好** - 连续内存存储
- **没有复杂材质分层** - 不够灵活但满足当前需求

---

## 7. 后处理系统

### 架构 / 实现

Adria 后处理系统基于 **Render Graph 中的多个 Pass** 实现，每个后处理效果是独立的 Render Pass。

**源码位置：** `Adria/Rendering/Postprocessor.h/cpp` [mateeeeeee/Adria → Adria/Rendering/Postprocessor.h]

```cpp
class Postprocessor
{
    // ...
    void AddPass(IPostEffect* effect);
    void Process(RenderGraph& rg);
private:
    std::vector<IPostEffect*> effects;
};
```

### 支持的后处理效果

从目录看，Adria 支持非常丰富的后处理和画面优化：

**源码目录：** `Adria/Rendering/`

| 效果 | 文件名 | 说明 |
|------|--------|------|
| 自动曝光 | `AutoExposurePass.cpp` | 基于直方图计算 |
| Bloom | `BloomPass.cpp` |  bloom 泛光 |
| 景深 | `DepthOfFieldPass.cpp` / `FFXDepthOfFieldPass.cpp` | 自定义 + FidelityFX 两种实现 |
| TAA / FXAA | `TAAPass.cpp` / `FXAAPass.cpp` | 时间抗锯齿 + 快速近似抗锯齿 |
| MotionBlur | `MotionBlurPass.cpp` | 运动模糊 |
| ToneMap | `ToneMapPass.cpp` | 色调映射 |
| FSR 2/3 | `FSR2Pass.cpp` / `FSR3Pass.cpp` | AMD 超级分辨率 |
| XeSS | `XeSS2Pass.cpp` | Intel Xe 超级采样 |
| DLSS 3 | `DLSS3Pass.cpp` | NVIDIA DLSS 3 |
| 体积雾 | `VolumetricFogManager.cpp` | 体积雾 |
| 体积云 | `VolumetricCloudsPass.cpp` | 体积云 |
| SSR | `SSRPass.cpp` | 屏幕空间反射 |
| SSAO / HBAO / FFX CACAO | 多种 | 屏幕空间环境 occlusion |

### 设计特点

- **每个效果独立** - 容易添加/移除效果
- **完全基于 Render Graph** - 自动处理依赖和资源生命周期
- **集成 FidelityFX 套件** - 使用 AMD 开源高质量后处理
- **支持多种 upscaling 技术** - FSR 2/3, XeSS, DLSS 3

---

## 架构总结

| 功能模块 | 实现方式 | 源码位置 | 优点 |
|----------|----------|----------|------|
| Render Graph 编译 | 拓扑排序 + 依赖级别分组 | `RenderGraph/RenderGraph.cpp` | 简洁易理解 |
| Barrier 处理 | 按依赖级别批量处理 | `RenderGraph/RenderGraph.cpp:PreExecute` | 简单、少冗余 |
| 同步点管理 | 基于读写依赖发现同步点 | `RenderGraph/RenderGraph.cpp:ResolveAsync`  | 正确工作，实现简单 |
| Async Compute | GPU 异步，CPU 顺序提交 | `RenderGraph/RenderGraphPass.h:RGPassType::AsyncCompute` | 支持异步计算 |
| RHI | D3D12 轻量级封装 | `Graphics/GfxDevice.h`, `Graphics/D3D12/*` | 直接映射 D3D12 |
| 场景管理 | EnTT ECS + GPU 缓冲 | `Rendering/Components.h`, `Rendering/Renderer.h` | 现代 ECS 方案 |
| 材质系统 | GPU 结构化缓冲 | `Rendering/ShaderStructs.h` | 简单高效 |
| 后处理 | Render Graph Pass 链 | `Rendering/Postprocessor.h`, `Rendering/*Pass.cpp` | 丰富效果，易于扩展 |

## 总结

Adria 是一个**非常适合学习**的现代 D3D12 渲染引擎：

- ✅ **代码质量高** - 清晰的命名和架构
- ✅ **Render Graph 实现标准** - 可以作为学习参考
- ✅ **支持基础 Async Compute** - 展示了跨队列同步的基本方法
- ✅ **完整渲染管线** - 从 GBuffer 到后期处理齐全
- ✅ 集成了很多现代图形技术 (DDGI, ReSTIR, FSR3 等)

适合学习 Render Graph 基础原理，但不适合需要高级多队列优化的生产环境直接使用。
