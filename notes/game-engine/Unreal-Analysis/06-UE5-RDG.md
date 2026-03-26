# UE5.1 RDG（Render Dependency Graph）源码分析

> B 站系列第 6 集：UE5.1 C++ 引擎源码分析 — RDG（渲染依赖图）
> 时长：约 1 小时 12 分钟

---

## 概述

**RDG（Render Dependency Graph，渲染依赖图）** 是 Unreal Engine 5 中的一个核心渲染优化模块。它的本质是一个**延迟执行 + 依赖分析**的框架，允许引擎在实际执行渲染指令之前，对所有 Pass 进行全局分析，从而自动完成以下优化：

1. **Pass Culling（剔除）**：自动识别并丢弃对最终画面没有贡献的 Pass，避免无效的 GPU 计算。
2. **Pass Merging（合并）**：将相邻且状态完全一致的 Pass 合并，消除冗余的 RenderPass Begin/End 和 Barrier 调用。
3. **资源生命周期管理**：RDG 资源（Texture/Buffer）在注册时不立即分配 RHI 资源，只在 Compile 阶段确认 Pass 不被剔除后才真正分配，节省显存。
4. **Async Compute 支持**：通过 Pipeline 类型区分（Graphics vs Compute），支持异步计算队列的调度与同步点管理。

官方文档对 RDG 有完整介绍，强烈建议结合官方文档阅读本笔记和源码。

---

## 目录

1. [设计动机与核心思想](#1-设计动机与核心思想)
2. [关键类结构](#2-关键类结构)
   - 2.1 FRDGHandle 与 FRDGRegistry
   - 2.2 FRDGResource / FRDGTexture / FRDGBuffer
   - 2.3 FRDGPass 与 TRDGLambdaPass
   - 2.4 FRDGBuilder（核心入口）
3. [资源的创建与注册](#3-资源的创建与注册)
   - 3.1 CreateTexture / CreateBuffer
   - 3.2 RegisterExternalTexture / RegisterExternalBuffer
   - 3.3 QueueTextureExtraction（资源导出）
4. [Pass 的定义与添加（AddPass）](#4-pass-的定义与添加addpass)
   - 4.1 基本用法
   - 4.2 SetupPassResources（资源收集）
   - 4.3 SetupPassDependencies（依赖关系建立）
5. [编译期（Compile）的工作](#5-编译期compile的工作)
   - 5.1 Pass Culling 算法
   - 5.2 Pass Merging 算法
   - 5.3 RHI 资源的延迟分配
6. [执行期（Execute）的工作](#6-执行期execute的工作)
7. [Async Compute 支持](#7-async-compute-支持)
8. [完整流程图（ASCII）](#8-完整流程图ascii)
9. [关键 API 用法示例（C++）](#9-关键-api-用法示例c)
10. [小结](#10-小结)

---

## 1. 设计动机与核心思想

### 1.1 传统渲染的问题

在没有 RDG 的情况下，一帧的渲染由多个 Pass 顺序组成，每个 Pass 直接调用 RHI 接口。问题在于：

- **无法感知全局**：每个 Pass 不知道其输出是否真正被后续 Pass 消耗，导致无效计算。
- **手动管理 Barrier**：开发者必须在每个 Pass 之间手动插入资源状态转换（Barrier），容易出错且繁琐。
- **无法自动优化**：无法自动合并两个连续 Pass（如它们使用相同的 RenderTarget），导致多余的 Begin/End RenderPass 调用。

### 1.2 RDG 的解法

RDG 引入了**两阶段设计**：

```
阶段一：收集（Recording）          阶段二：编译 + 执行（Compile + Execute）
─────────────────────────          ──────────────────────────────────────
上层代码调用 AddPass()               FRDGBuilder::Execute() 内部触发：
只是「注册」Pass 和资源               1. Compile()  → Culling + Merging + Barrier 计算
Lambda 被保存，不立即执行              2. Execute()  → 按顺序执行 Lambda
资源只是逻辑注册，无 RHI 分配          3. 延迟分配 RHI 资源
```

**核心思想**：先收集所有意图，再全局分析，最后最优执行。

---

## 2. 关键类结构

### 2.1 FRDGHandle 与 FRDGRegistry

```cpp
// FRDGHandle 本质是一个数组下标/索引（类似 Windows HANDLE 的轻量代理）
// 通过 Handle 可以从对应的 Registry（数组）中查找真正的对象
struct FRDGHandle
{
    uint32 Index;  // 指向 Registry 中的下标
};

// FRDGRegistry<T> 本质是一个模板数组
// 存储 Pass、Texture、Buffer 等所有 RDG 对象的指针
template<typename ObjectType>
class FRDGRegistry
{
    TArray<ObjectType*> Array;
};
```

**要点**：
- `FRDGHandle` 是轻量的值类型，可以廉价地复制传递。
- `FRDGRegistry` 是对应对象数组，通过 Handle 的 Index 字段 O(1) 查找对象。
- RDG 内部所有 Pass、资源都通过这套机制统一管理。

### 2.2 FRDGResource / FRDGTexture / FRDGBuffer

```
FRDGResource
    └── FRDGPooledRenderableResource（vable resource）
            ├── FRDGTexture   ← 对应 RHI 层的 FRHITexture
            └── FRDGBuffer    ← 对应 RHI 层的 FRHIBuffer
```

**核心特征：延迟创建（Lazy Creation）**

- 当调用 `FRDGBuilder::CreateTexture()` 时，**不会**立即创建 `FRHITexture`。
- 只是在 RDG 层注册一个 `FRDGTexture` 对象，其内部的 RHI 指针此时为空。
- 只有在 Compile 阶段确认该 Pass 不会被剔除后，才会调用 RHI 接口真正分配 GPU 内存。

这样做的好处：**被剔除的 Pass 所引用的资源根本不需要分配**，节省显存和分配开销。

```
注意：若你拿到了一个 FRDGTexture*，
在 Execute 之前调用 GetRHI() 得到的可能是 nullptr！
```

`FRDGTexture` 内部还记录了 **Producers**（生产者）信息——即哪些 Pass 曾经写入过这张贴图的哪些 subresource，这是建立 Pass 依赖关系的关键数据。

### 2.3 FRDGPass 与 TRDGLambdaPass

```cpp
class FRDGPass
{
    // 基础信息
    const TCHAR*        Name;
    FRDGPassHandle      Handle;         // 自身在 PassRegistry 中的索引
    ERDGPassFlags       Flags;
    ERHIPipeline        Pipeline;       // Graphics 或 AsyncCompute

    // 资源信息（从 Shader Parameter 结构体中解析而来）
    FRDGTextureHandleArray      Textures;
    FRDGBufferHandleArray       Buffers;
    // ...（UniformBuffers 等）

    // 依赖关系
    FRDGPassHandleArray         Producers;  // 当前 Pass 所依赖的其他 Pass 列表

    // 剔除标志（默认为 true = 可被剔除）
    uint8 bCulled : 1;

    // 合并相关标志
    uint8 bSkipRenderPassBegin : 1;
    uint8 bSkipRenderPassEnd   : 1;

    // 纯虚函数，子类实现
    virtual void Execute(FRHIComputeCommandList& RHICmdList) = 0;
};

// 最常用的子类：将 Lambda 存储下来
template<typename LambdaType>
class TRDGLambdaPass : public FRDGPass
{
    LambdaType Lambda;  // 保存渲染 Lambda

    void Execute(FRHIComputeCommandList& RHICmdList) override
    {
        Lambda(RHICmdList);  // 真正执行时才调用 Lambda
    }
};
```

**Pass 的两个核心字段**：
- `Producers`：记录"我依赖了哪些其他 Pass"。
- `bCulled`：标记我是否被剔除（默认 1 = 可剔除，经过 Compile 处理后不可剔除的会变为 0）。

### 2.4 FRDGBuilder（核心入口）

`FRDGBuilder` 是整个 RDG 的入口类，负责：
- 提供 `CreateTexture`、`CreateBuffer`、`RegisterExternal*` 等资源管理 API。
- 提供 `AddPass` API，供上层代码注册 Pass。
- 在 `Execute()` 时内部触发 `Compile()` 和逐 Pass 的执行。

```cpp
class FRDGBuilder
{
    // Pass 注册表（数组）
    FRDGPassRegistry    Passes;

    // 资源注册表
    FRDGTextureRegistry Textures;
    FRDGBufferRegistry  Buffers;

    // 外部输出列表（QueueTextureExtraction 写入这里）
    TArray<FExtractedTexture> ExtractedTextures;

    // 根 Pass 列表（不可被剔除的 Pass 种子集合）
    TArray<FRDGPassHandle>    CullRootPasses;

public:
    // 资源 API
    FRDGTextureRef  CreateTexture(const FRDGTextureDesc&, const TCHAR* Name);
    FRDGBufferRef   CreateBuffer (const FRDGBufferDesc&,  const TCHAR* Name);
    FRDGTextureRef  RegisterExternalTexture(const TRefCountPtr<IPooledRenderTarget>&);
    FRDGBufferRef   RegisterExternalBuffer (const TRefCountPtr<FRDGPooledBuffer>&);
    void            QueueTextureExtraction(FRDGTextureRef, TRefCountPtr<IPooledRenderTarget>*);

    // Pass 注册 API
    template<typename ParameterStructType, typename ExecuteLambdaType>
    FRDGPassRef AddPass(
        FRDGEventName&&              Name,
        const ParameterStructType*   ParameterStruct,
        ERDGPassFlags                Flags,
        ExecuteLambdaType&&          ExecuteLambda);

    // 触发 Compile + Execute（帧末调用一次）
    void Execute();
};
```

---

## 3. 资源的创建与注册

### 3.1 CreateTexture / CreateBuffer

当一个 Pass 需要一张新贴图（该帧之前不存在）时，使用 `CreateTexture`：

```cpp
// 在某个 Pass 构建代码中（渲染线程）
FRDGTextureDesc TexDesc = FRDGTextureDesc::Create2D(
    FIntPoint(1920, 1080),
    PF_FloatRGBA,
    FClearValueBinding::Black,
    TexCreate_RenderTargetable | TexCreate_ShaderResource
);

FRDGTextureRef MyTexture = GraphBuilder.CreateTexture(TexDesc, TEXT("MyTexture"));
// 此时 MyTexture->GetRHI() == nullptr，RHI 资源尚未分配
```

### 3.2 RegisterExternalTexture / RegisterExternalBuffer

当一张贴图来自外部系统（例如上一帧保存的 PooledRenderTarget、引擎提供的 GBuffer 等），需要先注册进 RDG 才能在 Pass 中使用：

```cpp
// 假设 PreviousDepth 是上一帧保存的 IPooledRenderTarget
FRDGTextureRef PreviousDepthRDG = GraphBuilder.RegisterExternalTexture(PreviousDepth);
// RDG 内部标记该资源为 External，不会在 Execute 后释放它
```

`RegisterExternal*` 与 `Create*` 的关键区别：

| 对比项 | Create* | RegisterExternal* |
|--------|---------|-------------------|
| RHI 资源何时分配 | Compile 阶段延迟分配 | 已存在，直接使用 |
| Execute 后是否释放 | 由 RDG 池管理 | **不释放**（外部所有权） |
| 使用场景 | 当帧内新建 | 跨帧或来自外部系统的资源 |

### 3.3 QueueTextureExtraction（资源导出）

`QueueTextureExtraction` 用于将 RDG 管理的贴图"导出"到外部，使其在 Execute 结束后仍然有效：

```cpp
// 典型用例：保存当前帧深度图，供下一帧使用
TRefCountPtr<IPooledRenderTarget> OutDepth;
GraphBuilder.QueueTextureExtraction(SceneDepthTexture, &OutDepth);
// Execute 结束后，OutDepth 指向已完成渲染的深度图
```

**这是 RDG Culling 算法的关键输入**：调用了 `QueueTextureExtraction` 的贴图，其生产 Pass（以及整条依赖链）一定不会被剔除。

---

## 4. Pass 的定义与添加（AddPass）

### 4.1 基本用法

```cpp
// 1. 定义 Shader Parameter 结构体（包含 RDG 资源引用）
BEGIN_SHADER_PARAMETER_STRUCT(FMyPassParameters, )
    SHADER_PARAMETER_RDG_TEXTURE(Texture2D, InputTexture)
    RENDER_TARGET_BINDING_SLOTS()
END_SHADER_PARAMETER_STRUCT()

// 2. 填充参数
FMyPassParameters* PassParameters = GraphBuilder.AllocParameters<FMyPassParameters>();
PassParameters->InputTexture    = MyInputTexture;
PassParameters->RenderTargets[0] = FRenderTargetBinding(MyOutputTexture, ERenderTargetLoadAction::EClear);

// 3. 添加 Pass
GraphBuilder.AddPass(
    RDG_EVENT_NAME("MyRenderPass"),
    PassParameters,
    ERDGPassFlags::Raster,
    [PassParameters, &View](FRHICommandList& RHICmdList)
    {
        // 此处是 Lambda：真正的 RHI 指令，延迟到 Execute 阶段才运行
        RHICmdList.SetViewport(...);
        // DrawPrimitive / Dispatch 等
    }
);
```

**关键点**：Lambda 在 `AddPass` 时只是被保存起来，**不立即执行**。

### 4.2 SetupPassResources（资源收集）

`AddPass` 内部会调用 `SetupPassResources`，利用 UE 的 Shader Parameter 反射系统（宏展开生成的 metadata）遍历 `ParameterStruct` 的所有字段，将其中的 `FRDGTextureRef`、`FRDGBufferRef` 等提取出来，存入 `FRDGPass::Textures` 和 `FRDGPass::Buffers` 数组。

```
ParameterStruct（着色器参数结构体）
         ↓  反射遍历（GetLayout / IterateShaderParameterMembers）
         ↓  根据字段类型判断（是 Texture？Buffer？UniformBuffer？）
         ↓
FRDGPass::Textures[]   ← 所有 RDG Texture 引用
FRDGPass::Buffers[]    ← 所有 RDG Buffer 引用
```

### 4.3 SetupPassDependencies（依赖关系建立）

这是建立 Pass 间依赖图的核心逻辑，仍然在 `AddPass` 内部完成：

```
对于当前 Pass（假设为 PassA）：

  ForEach texture in PassA.Textures:
      ForEach producer in texture.LastProducers:
          if producer 有效 AND pipeline 兼容:
              PassA.Producers.Add(producer.PassHandle)

  ForEach buffer in PassA.Buffers:
      ForEach producer in buffer.LastProducers:
          if producer 有效 AND pipeline 兼容:
              PassA.Producers.Add(producer.PassHandle)
```

`FRDGTexture` 内部维护 `LastProducers` 数组，记录"最近一次写入该贴图的 Pass"（按 subresource 分开记录）。这样，当新 Pass 读取一张贴图时，能准确找到产出该贴图的 Pass，从而建立 `PassA → LastProducerPass` 的依赖边。

---

## 5. 编译期（Compile）的工作

`FRDGBuilder::Execute()` 首先调用内部的 `Compile()` 函数，完成以下工作：

### 5.1 Pass Culling 算法

**目标**：找出所有对最终画面有贡献的 Pass，剔除无贡献的 Pass。

**初始状态**：
- 所有 Pass 的 `bCulled = 1`（默认全部可被剔除）。
- 有少数 Pass 是"根 Pass"（Root Pass），它们会被加入 `CullRootPasses` 种子列表：
  - 调用了 `QueueTextureExtraction` 的 Pass（输出到外部）。
  - 显式设置了 `ERDGPassFlags::NeverCull` 标志的 Pass。
  - 最终 Present Pass（输出到 SwapChain）。

**BFS 逆向传播**：

```
初始：CullRootPasses = [PassFinal]  // 例如最终后处理 Pass

WorkList = [PassFinal]

while WorkList 不为空:
    PassCurrent = WorkList.Pop()
    PassCurrent.bCulled = 0          // 标记为"不可剔除"
    for PassDep in PassCurrent.Producers:
        if PassDep.bCulled == 1:     // 尚未处理过
            WorkList.Push(PassDep)   // 加入待处理队列

// 结束后：
// bCulled == 0  → 有用，保留
// bCulled == 1  → 无用，剔除
```

**实际代码（约 10 行）**：

```cpp
// CullRootPasses 是"种子"队列（已在 AddPass 时填充）
for (int32 i = 0; i < CullRootPasses.Num(); ++i)
{
    FRDGPass* Pass = Passes[CullRootPasses[i]];
    Pass->bCulled = 0;
    for (FRDGPassHandle ProducerHandle : Pass->Producers)
    {
        FRDGPass* Producer = Passes[ProducerHandle];
        if (Producer->bCulled)
            CullRootPasses.Add(ProducerHandle);  // 动态扩展队列
    }
}
```

### 5.2 Pass Merging 算法

**目标**：相邻且使用相同 RenderTarget / DepthStencil / Viewport 的 Pass 可以合并，跳过冗余的 RenderPass Begin/End 调用。

**合并条件（`CanMergeRenderPasses`）**：
1. 两个 Pass 的 Pipeline 类型相同（均为 Raster）。
2. RenderTarget 输出完全一致（Texture 指针相等）。
3. DepthStencil 完全一致。
4. Viewport 等状态完全一致。

**合并效果**（以一组连续可合并的 Pass `B, X1, X2, Y` 为例）：

```
Pass B   → bSkipRenderPassEnd   = true   （不执行 End，直接进入下一个 Pass）
Pass X1  → bSkipRenderPassBegin = true   （跳过 Begin）
           bSkipRenderPassEnd   = true   （跳过 End）
Pass X2  → 同 X1
Pass Y   → bSkipRenderPassBegin = true   （跳过 Begin，但保留 End）
```

每个 Pass 执行时有三步：`RenderPass::Begin → Execute Lambda → RenderPass::End`。合并后，中间的 Pass 跳过 Begin 和 End，只执行真正的渲染指令，极大减少 GPU 驱动开销。

**Commit 机制**：

```
MergeList = []

ForEach Pass（过滤掉已剔除的）:
    if CanMergePrevious(Pass):
        MergeList.Add(Pass)
    else:
        if MergeList.Num() > 1:
            CommitMerge(MergeList)   // 批量设置 bSkipRenderPassBegin/End
        MergeList.Clear()
        MergeList.Add(Pass)         // 新的合并候选起点

// 处理最后一组
if MergeList.Num() > 1:
    CommitMerge(MergeList)
```

### 5.3 RHI 资源的延迟分配

在 Compile 阶段，对所有 `bCulled == 0` 的 Pass，遍历其引用的 `FRDGTexture` / `FRDGBuffer`，若对应的 RHI 资源尚未分配（即不是 External 注册的），则从资源池中分配真正的 `FRHITexture` / `FRHIBuffer`。

同时，此阶段也完成 **Barrier 插入**：分析每对相邻 Pass 对同一资源的读写状态，在必要时插入 `ResourceTransition` 调用。

---

## 6. 执行期（Execute）的工作

`Compile()` 完成后，`Execute()` 按 Pass 注册顺序逐一执行：

```cpp
for (FRDGPass* Pass : Passes)
{
    // 1. 跳过被剔除的 Pass
    if (Pass->bCulled)
        continue;

    // 2. 执行 Barrier（资源状态转换）
    if (!Pass->bSkipRenderPassBegin)
        RHICmdList.BeginRenderPass(Pass->RenderPassInfo, ...);

    // 3. 执行 Lambda（真正的渲染指令）
    Pass->Execute(RHICmdList);

    // 4. 结束 RenderPass
    if (!Pass->bSkipRenderPassEnd)
        RHICmdList.EndRenderPass();
}

// 5. 处理 QueueTextureExtraction：将 RDG 内部资源导出到外部指针
for (auto& Extraction : ExtractedTextures)
{
    *Extraction.Output = Extraction.Texture->PooledRenderTarget;
}
```

---

## 7. Async Compute 支持

在 `FRDGPass` 的 `Pipeline` 字段中区分两种管线：

```cpp
enum class ERHIPipeline
{
    Graphics,     // 图形管线（光栅化 + 像素着色）
    AsyncCompute, // 异步计算管线（纯 Compute Shader）
};
```

在 `SetupPassDependencies` 中，当两个 Pass 的 Pipeline **不同**时，依赖关系的处理有所不同：
- 同管线依赖：直接加入 `Producers` 列表，执行时串行等待。
- 跨管线依赖（例如 AsyncCompute Pass 依赖 Graphics Pass 的输出）：需要在 Compile 阶段插入 GPU Semaphore / Fence，让两个队列在正确的时序上同步。

这使得 RDG 能够自动生成跨队列的同步指令，上层代码只需声明资源依赖，无需手动管理 GPU 信号量。

---

## 8. 完整流程图（ASCII）

```
上层渲染代码（Render Thread）
       │
       ├─ CreateTexture() / CreateBuffer()
       │       └─ 仅注册 FRDGTexture/FRDGBuffer，无 RHI 分配
       │
       ├─ RegisterExternalTexture() / RegisterExternalBuffer()
       │       └─ 包装外部 RHI 资源，标记为 External
       │
       ├─ QueueTextureExtraction()
       │       └─ 记录需要导出的资源（加入剔除算法的"根节点"）
       │
       ├─ AddPass(Name, Parameters, Flags, Lambda)
       │       │
       │       ├─ new TRDGLambdaPass（保存 Lambda）
       │       ├─ SetupPassResources（从 Parameters 提取 Texture/Buffer 列表）
       │       ├─ SetupPassDependencies（遍历资源的 LastProducers，填充 Producers 列表）
       │       └─ 初始化 bCulled = 1（默认可被剔除）
       │
       └─ GraphBuilder.Execute()
               │
               ├── Compile()
               │       │
               │       ├─ [Pass Culling]
               │       │     从 CullRootPasses 出发，BFS 反向遍历 Producers
               │       │     将所有有用的 Pass 标记为 bCulled = 0
               │       │
               │       ├─ [Pass Merging]
               │       │     遍历未剔除的 Pass，判断相邻 Pass 是否可合并
               │       │     设置 bSkipRenderPassBegin / bSkipRenderPassEnd
               │       │
               │       ├─ [RHI 资源分配]
               │       │     对 bCulled == 0 的 Pass，从池中分配 FRHITexture/FRHIBuffer
               │       │
               │       └─ [Barrier 计算]
               │             分析资源读写状态变化，准备 ResourceTransition 调用
               │
               └── Execute()
                       │
                       ├─ ForEach Pass:
                       │     if bCulled → skip
                       │     if !bSkipRenderPassBegin → BeginRenderPass()
                       │     Pass.Lambda(RHICmdList)    ← 真正执行渲染指令
                       │     if !bSkipRenderPassEnd   → EndRenderPass()
                       │
                       └─ 处理 ExtractedTextures（导出资源到外部指针）
```

---

## 9. 关键 API 用法示例（C++）

### 9.1 完整的一个 Pass 添加流程

```cpp
void RenderMyFeature(FRDGBuilder& GraphBuilder,
                     const FViewInfo& View,
                     FRDGTextureRef SceneColor,
                     FRDGTextureRef SceneDepth)
{
    // ── 创建输出贴图 ──────────────────────────────────────
    FRDGTextureDesc OutputDesc = FRDGTextureDesc::Create2D(
        View.ViewRect.Size(), PF_FloatRGBA,
        FClearValueBinding::Transparent,
        TexCreate_RenderTargetable | TexCreate_ShaderResource);
    FRDGTextureRef OutputTexture = GraphBuilder.CreateTexture(OutputDesc, TEXT("MyFeatureOutput"));

    // ── 构建 Shader 参数 ──────────────────────────────────
    FMyShaderCS::FParameters* PassParams = GraphBuilder.AllocParameters<FMyShaderCS::FParameters>();
    PassParams->InputTexture  = SceneColor;
    PassParams->InputDepth    = SceneDepth;
    PassParams->OutputTexture = GraphBuilder.CreateUAV(OutputTexture);

    // ── 添加 Compute Pass ─────────────────────────────────
    TShaderMapRef<FMyShaderCS> ComputeShader(View.ShaderMap);
    GraphBuilder.AddPass(
        RDG_EVENT_NAME("MyFeature"),
        PassParams,
        ERDGPassFlags::Compute,
        [PassParams, ComputeShader, &View](FRHIComputeCommandList& RHICmdList)
        {
            FComputeShaderUtils::Dispatch(RHICmdList, ComputeShader, *PassParams,
                FIntVector(FMath::DivideAndRoundUp(View.ViewRect.Width(), 8),
                           FMath::DivideAndRoundUp(View.ViewRect.Height(), 8), 1));
        }
    );

    // ── 导出结果（若需要跨帧使用） ──────────────────────────
    // GraphBuilder.QueueTextureExtraction(OutputTexture, &View.PreviousFrameOutput);
}
```

### 9.2 注册外部资源

```cpp
// 将上一帧保存的 PooledRenderTarget 注册进当前帧 RDG
FRDGTextureRef PreviousDepthRDG =
    GraphBuilder.RegisterExternalTexture(ViewState->PreviousDepthTarget);

// 在某个 Pass 中将当前深度图导出，供下一帧使用
GraphBuilder.QueueTextureExtraction(SceneDepth, &ViewState->PreviousDepthTarget);
```

### 9.3 Raster Pass（带 RenderTarget）

```cpp
BEGIN_SHADER_PARAMETER_STRUCT(FForwardPassParams, )
    SHADER_PARAMETER_RDG_UNIFORM_BUFFER(FSceneUniformParameters, Scene)
    RENDER_TARGET_BINDING_SLOTS()
END_SHADER_PARAMETER_STRUCT()

FForwardPassParams* Params = GraphBuilder.AllocParameters<FForwardPassParams>();
Params->Scene         = SceneUniformBuffer;
Params->RenderTargets[0] = FRenderTargetBinding(SceneColor, ERenderTargetLoadAction::ELoad);
Params->RenderTargets.DepthStencil =
    FDepthStencilBinding(SceneDepth, ERenderTargetLoadAction::ELoad, ERenderTargetLoadAction::ENoAction,
                         FExclusiveDepthStencil::DepthWrite_StencilNop);

GraphBuilder.AddPass(
    RDG_EVENT_NAME("ForwardBasePass"),
    Params,
    ERDGPassFlags::Raster,
    [Params](FRHICommandList& RHICmdList)
    {
        // 光栅化指令...
    }
);
```

---

## 10. 小结

RDG 的核心思路可以用三个词概括：**延迟、分析、优化**。

| 阶段 | 动作 | 关键 API |
|------|------|---------|
| 收集（Recording） | 注册资源、注册 Pass、建立依赖 | `CreateTexture`, `AddPass`, `QueueTextureExtraction` |
| 编译（Compile） | 剔除无用 Pass、合并相邻 Pass、分配 RHI 资源、计算 Barrier | 内部 `Compile()` |
| 执行（Execute） | 按序执行 Lambda，跳过被剔除的 Pass | 内部 `Execute()` |

**RDG 带来的收益**：
1. 开发者只需声明资源依赖，不需要手动管理 Barrier 和资源状态转换。
2. 无用 Pass（及其资源）自动被剔除，减少 GPU 工作量和显存占用。
3. 相邻兼容 Pass 自动合并，减少驱动层开销。
4. 资源延迟分配，节省被剔除 Pass 的显存。
5. 天然支持 Async Compute 的跨队列同步管理。

**阅读源码建议**（视频中强调）：
- 先通读官方文档，理解 RDG 的设计目标，再看代码事半功倍。
- 核心代码并不多：`FRDGBuilder::AddPass` → `SetupPassResources` → `SetupPassDependencies` → `Compile` → `Execute`，主干逻辑约数百行。
- 重点关注 `FRDGPass::Producers`（依赖关系）和 `bCulled`（剔除标志）这两个成员变量。

**相关源码文件**（UE5 引擎）：
- `Engine/Source/Runtime/RenderCore/Public/RenderGraphDefinitions.h` — 基础类型定义
- `Engine/Source/Runtime/RenderCore/Public/RenderGraphBuilder.h` — `FRDGBuilder` 声明
- `Engine/Source/Runtime/RenderCore/Private/RenderGraphBuilder.cpp` — `AddPass`, `Compile`, `Execute` 实现
- `Engine/Source/Runtime/RenderCore/Public/RenderGraphResources.h` — `FRDGTexture`, `FRDGBuffer` 等资源类
- `Engine/Source/Runtime/RenderCore/Public/RenderGraphPass.h` — `FRDGPass`, `TRDGLambdaPass`
