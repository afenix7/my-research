# UE5.1 C++ 源码分析：渲染管线 RHI 资源

> **来源**：B 站 UE5.1 C++ 引擎源码分析系列第 1 集——渲染管线 RHI 资源
> **引擎版本**：Unreal Engine 5.1
> **核心主题**：RHI（Render Hardware Interface）资源的抽象设计与跨平台封装

---

## 目录

1. [RHI 概述](#1-rhi-概述)
2. [GPU 渲染管线基础回顾](#2-gpu-渲染管线基础回顾)
3. [D3D12 渲染流程示例](#3-d3d12-渲染流程示例)
4. [RHI 的设计目标与封装思路](#4-rhi-的设计目标与封装思路)
5. [FRHIResource：所有资源的抽象基类](#5-frhiresource所有资源的抽象基类)
6. [FRHIUniformBuffer：Uniform Buffer 资源](#6-frhiuniformbuffer-uniform-buffer-资源)
7. [FRHITexture：纹理资源](#7-frhitexture-纹理资源)
8. [FDynamicRHI：RHI 操作接口层](#8-fdynamicrhi-rhi-操作接口层)
9. [跨平台继承体系总览](#9-跨平台继承体系总览)
10. [上层逻辑的使用方式（UTexture 案例）](#10-上层逻辑的使用方式utexture-案例)
11. [本讲小结](#11-本讲小结)

---

## 1. RHI 概述

**RHI**（Render Hardware Interface）是 Unreal Engine 中图形渲染层的核心抽象层。它的核心职责是：

> **将 DirectX 11 / DirectX 12 / OpenGL / Metal / Vulkan 等不同图形 API 的差异，统一封装成一套跨平台的接口。**

UE5 的渲染代码无需关心底层是哪种图形 API，只需调用 RHI 层的统一接口即可。编译时根据目标平台选择对应的 RHI 实现，做到「编写一次，到处运行」。

RHI 层解决的三个核心问题：

| 问题 | RHI 中的对应概念 |
|------|-----------------|
| GPU 执行什么代码？| Shader 对象（`FRHIVertexShader` / `FRHIPixelShader` 等）+ `FRHIGraphicsPipelineState` |
| 代码的输入参数格式是什么？| Root Signature / Uniform Buffer Layout |
| 实际的数据（资源）在哪里？| `FRHIResource` 及其子类（Buffer、Texture、Sampler 等） |

---

## 2. GPU 渲染管线基础回顾

一次完整的 Draw Call（绘制调用）要经历如下固定的 GPU 管线阶段：

```
顶点输入
    │
    ▼
[顶点着色器 Vertex Shader]  ← 可编程 (绿色)
    │
    ▼
[曲面细分 Tessellation]      ← 可编程 (可选)
    │
    ▼
  裁剪 (Clipping)            ← GPU 固定 (红色，不可控)
    │
    ▼
  光栅化 (Rasterization)     ← GPU 固定 (红色，不可控)
    │
    ▼
[像素着色器 Pixel Shader]    ← 可编程 (绿色)
    │
    ▼
  深度/模板测试 + 抗锯齿
    │
    ▼
[后期处理 Post Processing]   ← 可编程
    │
    ▼
  输出到 RenderTarget / 屏幕
```

**关键要点**：
- **红色阶段**（裁剪、光栅化）由 GPU 硬件固定实现，开发者无法干预。
- **绿色阶段**（VS、PS、后处理等）由开发者通过 HLSL/GLSL/MSL 等着色器语言编写代码，上传到 GPU 执行。

对于每一次 Draw Call，需要向 GPU 提供**三件事**：
1. **着色器代码**（已编译的 bytecode）
2. **参数输入格式**（告诉 GPU 代码期望什么格式的输入，即 Root Signature / Descriptor Layout）
3. **实际的数据**（顶点缓冲区、纹理、常量缓冲区等真正的显存数据）

---

## 3. D3D12 渲染流程示例

以「龙书」（Frank D. Luna 的 *Introduction to 3D Game Programming with DirectX 12*）的示例代码为基础，理解 D3D12 渲染的完整流程。

### 3.1 着色器代码

一个典型的着色器文件（HLSL）包含：

```hlsl
// 全局参数（cbuffer）
cbuffer cbPerObject : register(b0) { ... }
cbuffer cbPass      : register(b1) { ... }
cbuffer cbMaterial  : register(b2) { ... }

Texture2D gDiffuseMap : register(t0);
SamplerState gSampler : register(s0);

// 顶点着色器 VS
VertexOut VS(VertexIn vin) { ... }

// 像素着色器 PS
float4 PS(VertexOut pin) : SV_Target { ... }
```

着色器引用的参数：`t0`（Texture）、`b0/b1/b2`（Constant Buffer）、`s0`（Sampler）。

### 3.2 Pipeline State Object (PSO)

PSO 是 D3D12 中表示**整个渲染管线状态**的对象，包含着色器代码 + 参数格式 + 各种渲染状态：

```cpp
D3D12_GRAPHICS_PIPELINE_STATE_DESC psoDesc = {};

// 绑定已编译的着色器 bytecode
psoDesc.VS = { vsBlob->GetBufferPointer(), vsBlob->GetBufferSize() };
psoDesc.PS = { psBlob->GetBufferPointer(), psBlob->GetBufferSize() };

// 绑定 Root Signature（参数格式）
psoDesc.pRootSignature = mRootSignature.Get();

// 各种渲染状态设置
psoDesc.RasterizerState = CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);
psoDesc.BlendState      = CD3DX12_BLEND_DESC(D3D12_DEFAULT);
psoDesc.DepthStencilState = CD3DX12_DEPTH_STENCIL_DESC(D3D12_DEFAULT);
psoDesc.InputLayout     = { mInputLayout.data(), (UINT)mInputLayout.size() };
// ...

// 创建 PSO
device->CreateGraphicsPipelineState(&psoDesc, IID_PPV_ARGS(&mPSO));
```

### 3.3 Root Signature（根签名）

Root Signature 描述着色器的**参数格式布局**，并非真正的参数值。对应上面着色器中的 `t0/b0/b1/b2/s0`：

```cpp
// 4 个参数（t0 + b0 + b1 + b2），Sampler 单独设置
CD3DX12_ROOT_PARAMETER slotRootParameter[4];

// t0: Descriptor Table (SRV for texture)
CD3DX12_DESCRIPTOR_RANGE texTable;
texTable.Init(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 0);
slotRootParameter[0].InitAsDescriptorTable(1, &texTable);

// b0, b1, b2: Constant Buffer Views
slotRootParameter[1].InitAsConstantBufferView(0);
slotRootParameter[2].InitAsConstantBufferView(1);
slotRootParameter[3].InitAsConstantBufferView(2);

// 构建根签名描述符
CD3DX12_ROOT_SIGNATURE_DESC rootSigDesc(4, slotRootParameter, ...);

// 序列化并创建根签名
ID3DBlob* serializedRootSig = nullptr;
D3D12SerializeRootSignature(&rootSigDesc, D3D_ROOT_SIGNATURE_VERSION_1,
                            &serializedRootSig, nullptr);
device->CreateRootSignature(0, serializedRootSig->GetBufferPointer(),
                            serializedRootSig->GetBufferSize(),
                            IID_PPV_ARGS(&mRootSignature));
```

### 3.4 每帧渲染（Draw Call 执行流程）

```cpp
// 1. 绑定 PSO（告诉 GPU 要用哪套代码和状态）
cmdList->SetPipelineState(mPSO.Get());

// 2. 绑定 Root Signature（告诉 GPU 参数格式）
cmdList->SetGraphicsRootSignature(mRootSignature.Get());

// 3. 传入实际数据
// 传入贴图（t0）
cmdList->SetGraphicsRootDescriptorTable(0, tex->GetGPUSRV());
// 传入常量缓冲区（b0/b1/b2）
cmdList->SetGraphicsRootConstantBufferView(1, objCBAddress);
cmdList->SetGraphicsRootConstantBufferView(2, passCBAddress);
cmdList->SetGraphicsRootConstantBufferView(3, matCBAddress);

// 4. 绑定顶点缓冲区与索引缓冲区
cmdList->IASetVertexBuffers(0, 1, &vbView);
cmdList->IASetIndexBuffer(&ibView);
cmdList->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);

// 5. 发出 Draw Call（驱动 GPU 执行）
cmdList->DrawIndexedInstanced(indexCount, 1, startIndex, baseVertex, 0);
```

**核心要点**：所有传入 GPU 的数据（贴图、常量缓冲区、顶点数据）在底层本质上都是一段**显存**（VRAM），在 D3D12 中统一抽象为 `ID3D12Resource`，在 OpenGL 中则是一个**无符号整数**（资源 ID）。

---

## 4. RHI 的设计目标与封装思路

UE5 需要支持多种图形 API：
- DirectX 11 (`D3D11`)
- DirectX 12 (`D3D12`)
- OpenGL (`OpenGL`)
- Metal (`Metal`)
- Vulkan (`Vulkan`)

UE5 的策略是 **「定义抽象基类（接口类）+ 平台子类实现」**，用标准的 C++ 多态实现跨平台封装：

```
RHI 层：定义抽象基类（FRHIResource、FDynamicRHI 等）
         ↓
平台层：各平台（D3D12、OpenGL 等）继承抽象基类，实现具体逻辑
         ↓
上层逻辑：只与抽象基类交互，不感知底层 API
```

编译时通过平台宏或构建配置，决定链接哪套平台实现。上层代码无需改动，即可在不同平台运行。

---

## 5. FRHIResource：所有资源的抽象基类

所有 RHI 资源类型都继承自 `FRHIResource`，它是整个资源体系的根节点。

### 5.1 类定义概览

`FRHIResource` 定义在 `Engine/Source/Runtime/RHI/Public/RHIResources.h` 中，结构极为精简：

```cpp
class FRHIResource
{
public:
    // 引用计数相关（AddRef / Release）
    void AddRef() const;
    void Release() const;

    // 返回资源类型枚举
    FORCEINLINE ERHIResourceType GetType() const { return ResourceType; }

protected:
    // 原子引用计数（支持多线程安全）
    mutable FThreadSafeCounter NumRefs;

    // 资源类型标记
    ERHIResourceType ResourceType;

    // 一些 mask/状态数据（用于内部管理）
    // ...
};
```

**关键特征**：
- 基类几乎不包含任何业务实现，只做引用计数管理和类型标记。
- 不绑定任何具体平台（与 D3D12 / OpenGL 无关）。
- 通过 `ERHIResourceType` 枚举区分资源类型。

### 5.2 ERHIResourceType 资源类型枚举

```cpp
enum ERHIResourceType : uint8
{
    RRT_None,
    RRT_SamplerState,
    RRT_RasterizerState,
    RRT_DepthStencilState,
    RRT_BlendState,
    RRT_VertexDeclaration,
    RRT_VertexShader,
    RRT_HullShader,
    RRT_DomainShader,
    RRT_PixelShader,
    RRT_GeometryShader,
    RRT_ComputeShader,
    RRT_IndexBuffer,
    RRT_VertexBuffer,
    RRT_StructuredBuffer,
    RRT_Texture,
    RRT_Texture2D,
    RRT_Texture2DArray,
    RRT_Texture3D,
    RRT_TextureCube,
    RRT_TextureReference,
    RRT_TimestampCalibrationQuery,
    RRT_GPUFence,
    RRT_UniformBuffer,
    RRT_GraphicsPipelineState,
    RRT_ComputePipelineState,
    // ...
};
```

枚举中的每一项都对应 RHI 层一个独立的资源子类，涵盖着色器、缓冲区、纹理、状态对象、管线状态等所有 GPU 资源类型。

### 5.3 FRHIResource 的继承树（精简版）

```
FRHIResource
├── FRHISamplerState
├── FRHIRasterizerState
├── FRHIDepthStencilState
├── FRHIBlendState
├── FRHIVertexDeclaration
├── FRHIShader（着色器基类）
│   ├── FRHIVertexShader
│   ├── FRHIPixelShader
│   ├── FRHIHullShader
│   ├── FRHIDomainShader
│   ├── FRHIGeometryShader
│   └── FRHIComputeShader
├── FRHIIndexBuffer
├── FRHIVertexBuffer
├── FRHIStructuredBuffer
├── FRHIUniformBuffer          ← 常量缓冲区
├── FRHITextureBase
│   └── FRHITexture            ← 纹理
│       ├── FRHITexture2D
│       ├── FRHITexture2DArray
│       ├── FRHITexture3D
│       └── FRHITextureCube
├── FRHIGraphicsPipelineState
└── FRHIComputePipelineState
```

---

## 6. FRHIUniformBuffer: Uniform Buffer 资源

`FRHIUniformBuffer` 对应 D3D12 的 `Constant Buffer（CBV）`，OpenGL 的 `Uniform Buffer Object（UBO）`，本质是一段传递给着色器的参数数据。

### 6.1 抽象层定义

```cpp
// Engine/Source/Runtime/RHI/Public/RHIResources.h

class FRHIUniformBuffer : public FRHIResource
{
public:
    /** 释放资源 */
    virtual void Release() = 0;

    /** 获取这段 buffer 的字节大小 */
    uint32 GetSize() const { return LayoutConstantBufferSize; }

    /** 获取 layout 描述（成员变量的格式信息） */
    const FRHIUniformBufferLayout& GetLayout() const { return *Layout; }

protected:
    const FRHIUniformBufferLayout* Layout;
    uint32 LayoutConstantBufferSize;
};
```

**要点**：这个类只定义接口，没有任何平台相关的实现，不包含任何 `ID3D12Resource` 或 OpenGL 的东西。

### 6.2 D3D12 实现：FD3D12UniformBuffer

```cpp
// Engine/Source/Runtime/D3D12RHI/Private/D3D12Resources.h

class FD3D12UniformBuffer : public FRHIUniformBuffer, public FD3D12LinkedAdapterObject<FD3D12UniformBuffer>
{
public:
    // 实际的 D3D12 资源存储在 ResourceLocation 中
    FD3D12ResourceLocation ResourceLocation;

    // 预缓存的 GPU Virtual Address（频繁使用时避免重复查询）
    D3D12_GPU_VIRTUAL_ADDRESS GPUVirtualAddress;

    // UAV（Unordered Access View），某些情况下需要
    // 对应的 Descriptor Heap 信息
    // ...
};
```

#### FD3D12ResourceLocation 结构

```
FD3D12ResourceLocation
├── FD3D12Resource* UnderlyingResource    ← 真正的 ID3D12Resource* 指针
├── D3D12_GPU_VIRTUAL_ADDRESS GPUAddress  ← GPU 虚拟地址
├── FD3D12Heap* Heap                      ← 所在 Heap
└── uint64 OffsetFromBaseOfResource       ← 在 Resource 内的偏移
```

`FD3D12Resource` 中持有真正的 `ID3D12Resource` COM 指针，这才是 D3D12 显存中的那段数据。

```
FD3D12UniformBuffer
└── ResourceLocation: FD3D12ResourceLocation
    └── UnderlyingResource: FD3D12Resource
        └── Resource: TRefCountPtr<ID3D12Resource>  ← 真正的 D3D12 资源
```

### 6.3 OpenGL 实现：FOpenGLUniformBuffer

OpenGL 中一切资源都用无符号整数（`GLuint`）表示：

```cpp
// Engine/Source/Runtime/OpenGLDrv/Private/OpenGLResources.h

class FOpenGLUniformBuffer : public FRHIUniformBuffer
{
public:
    // OpenGL 资源 ID（通过 glGenBuffers 创建后返回的 uint）
    GLuint Resource;

    // 其他 OpenGL 相关信息
    uint32 AllocatedSize;
    // ...
};
```

使用时只需将 `Resource`（`GLuint`）传给任何需要该 UBO 的 `gl*` 函数调用即可。

### 6.4 UBO 的类层次对比

```
FRHIUniformBuffer（抽象接口）
├── FD3D12UniformBuffer
│   └── 内含: FD3D12ResourceLocation → FD3D12Resource → ID3D12Resource*
└── FOpenGLUniformBuffer
    └── 内含: GLuint Resource（OpenGL 资源 ID）
```

---

## 7. FRHITexture：纹理资源

贴图（Texture）是渲染中最常见的资源类型之一。

### 7.1 抽象层定义

```cpp
// Engine/Source/Runtime/RHI/Public/RHIResources.h

class FRHITexture : public FRHITextureBase
{
public:
    /** 获取纹理描述（格式、尺寸、MipLevel 数等） */
    virtual FRHITextureDesc GetDesc() const = 0;

    /** 直接获取底层平台原生资源指针（如 ID3D12Resource*） */
    virtual void* GetNativeResource() const { return nullptr; }

    /** 获取纹理尺寸 */
    virtual FIntVector GetSizeXYZ() const = 0;

    /** 获取最大 Mip 维度 */
    virtual uint32 GetNumMips() const = 0;

    /** 获取像素格式 */
    virtual EPixelFormat GetFormat() const = 0;

    /** 获取默认视图（Shader Resource View） */
    virtual FRHIShaderResourceView* GetDefaultView() const { return nullptr; }

    // 获取名称（调试用）
    FName GetName() const { return TextureName; }

protected:
    FName TextureName;
};
```

### 7.2 D3D12 实现：FD3D12Texture

```cpp
class FD3D12Texture : public FRHITexture,
                      public FD3D12BaseShaderResource,
                      public FD3D12LinkedAdapterObject<FD3D12Texture>
{
public:
    // 同 UniformBuffer 一样，核心数据存在 ResourceLocation 中
    FD3D12ResourceLocation ResourceLocation;

    // Render Target View / Depth Stencil View（作为 RT 使用时需要）
    TRefCountPtr<FD3D12RenderTargetView>   RTView;
    TRefCountPtr<FD3D12DepthStencilView>   DSView;

    // Shader Resource View（作为着色器输入使用时需要）
    TRefCountPtr<FD3D12ShaderResourceView> SRView;

    // 实现 FRHITexture 接口
    virtual void* GetNativeResource() const override
    {
        return ResourceLocation.GetResource()->GetResource(); // 返回 ID3D12Resource*
    }
    // ...
};
```

### 7.3 OpenGL 实现：FOpenGLTexture

```cpp
class FOpenGLTexture : public FRHITexture, public FOpenGLTextureBase
{
public:
    // OpenGL 纹理对象 ID
    GLuint Resource;

    // OpenGL 纹理类型（GL_TEXTURE_2D / GL_TEXTURE_3D 等）
    GLenum Target;

    // 实现接口
    virtual FRHITextureDesc GetDesc() const override { ... }
    virtual FIntVector GetSizeXYZ() const override { ... }
    // ...
};
```

### 7.4 纹理资源类层次

```
FRHIResource
└── FRHITextureBase
    └── FRHITexture（抽象纹理接口）
        ├── FRHITexture2D
        ├── FRHITexture3D
        ├── FRHITextureCube
        │
        ├── FD3D12Texture（D3D12 平台实现）
        │   ├── Inherits: FRHITexture + FD3D12BaseShaderResource
        │   └── Members: FD3D12ResourceLocation（含真正的 ID3D12Resource*）
        │
        └── FOpenGLTexture（OpenGL 平台实现）
            ├── Inherits: FRHITexture + FOpenGLTextureBase
            └── Members: GLuint Resource（GL 纹理 ID）
```

---

## 8. FDynamicRHI：RHI 操作接口层

`FRHIResource` 及其子类只是**资源数据结构**，不包含操作逻辑。所有对 GPU 的**操作**（创建资源、更新资源、创建管线状态等）都定义在 `FDynamicRHI` 中。

### 8.1 定位与作用

`FDynamicRHI` 是 RHI 层另一个极其重要的抽象类，它定义了图形渲染所需的全部操作接口，包括：
- 创建/销毁各类资源
- 更新资源数据
- 创建 Pipeline State
- 创建 Shader
- 绑定资源到 Command List

### 8.2 主要接口概览

```cpp
// Engine/Source/Runtime/RHI/Public/DynamicRHI.h

class FDynamicRHI
{
public:
    // ---- 资源创建 ----
    virtual FRHIUniformBuffer* CreateUniformBuffer(
        const void* Contents, const FRHIUniformBufferLayout* Layout,
        EUniformBufferUsage Usage, EUniformBufferValidation Validation) = 0;

    virtual FRHITexture* CreateTexture(
        const FRHITextureCreateInfo& CreateInfo,
        const FRHITextureInitialData* InitialData = nullptr) = 0;

    virtual FRHISamplerState* CreateSamplerState(
        const FSamplerStateInitializerRHI& Initializer) = 0;

    virtual FRHIRasterizerState* CreateRasterizerState(
        const FRasterizerStateInitializerRHI& Initializer) = 0;

    virtual FRHIDepthStencilState* CreateDepthStencilState(
        const FDepthStencilStateInitializerRHI& Initializer) = 0;

    virtual FRHIBlendState* CreateBlendState(
        const FBlendStateInitializerRHI& Initializer) = 0;

    virtual FRHIVertexShader* CreateVertexShader(
        const TArray<uint8>& Code, const FSHAHash& Hash) = 0;

    virtual FRHIPixelShader* CreatePixelShader(
        const TArray<uint8>& Code, const FSHAHash& Hash) = 0;

    virtual FRHIComputeShader* CreateComputeShader(
        const TArray<uint8>& Code, const FSHAHash& Hash) = 0;

    virtual FRHIGraphicsPipelineState* CreateGraphicsPipelineState(
        const FGraphicsPipelineStateInitializer& Initializer) = 0;

    virtual FRHIComputePipelineState* CreateComputePipelineState(
        FRHIComputeShader* ComputeShader) = 0;

    // ---- 资源更新 ----
    virtual void UpdateTexture2D(
        FRHICommandListBase& RHICmdList,
        FRHITexture2D* Texture,
        uint32 MipIndex,
        const struct FUpdateTextureRegion2D& UpdateRegion,
        uint32 SourcePitch,
        const uint8* SourceData) = 0;

    virtual void* LockBuffer(
        FRHICommandListBase& RHICmdList,
        FRHIBuffer* Buffer,
        uint32 Offset, uint32 Size,
        EResourceLockMode LockMode) = 0;

    virtual void UnlockBuffer(
        FRHICommandListBase& RHICmdList,
        FRHIBuffer* Buffer) = 0;

    // ---- 查询 ----
    virtual FRHITimestampCalibrationQuery* CreateTimestampCalibrationQuery() = 0;

    // ... 数百个其他接口
};
```

**注意**：`FDynamicRHI` 中所有方法都没有实现（纯虚函数或留有 `unimplemented()`），真正的实现在各平台子类中。

### 8.3 D3D12 实现：FD3D12DynamicRHI

```cpp
// Engine/Source/Runtime/D3D12RHI/Private/D3D12RHI.h

class FD3D12DynamicRHI : public FDynamicRHI
{
public:
    virtual void UpdateTexture2D(
        FRHICommandListBase& RHICmdList,
        FRHITexture2D* TextureRHI,
        uint32 MipIndex,
        const FUpdateTextureRegion2D& UpdateRegion,
        uint32 SourcePitch,
        const uint8* SourceData) override
    {
        // 最终调用 D3D12 的 CopyTextureRegion
        CommandContext->CopyTextureRegion(
            &DestLocation,    // 目标 D3D12 资源位置
            DstX, DstY, 0,
            &SrcLocation,     // 源资源位置（上传堆）
            &SrcBox
        );
        // ...
    }

    virtual FRHIUniformBuffer* CreateUniformBuffer(...) override
    {
        // 使用 D3D12 创建资源，返回 FD3D12UniformBuffer
        FD3D12UniformBuffer* NewBuffer = new FD3D12UniformBuffer(...);
        // ... 分配显存、上传数据
        return NewBuffer;
    }
};
```

调用链示意（UpdateTexture2D）：

```
UTexture::UpdateResource()
    → ENQUEUE_RENDER_COMMAND
    → RHIUpdateTexture2D(...)
    → FDynamicRHI::UpdateTexture2D(...)     ← 抽象接口
    → FD3D12DynamicRHI::UpdateTexture2D(...) ← D3D12 实现
    → CommandContext->CopyTextureRegion(...)  ← D3D12 原生 API
```

### 8.4 OpenGL 实现：FOpenGLDynamicRHI

```cpp
class FOpenGLDynamicRHI : public FDynamicRHI /* 中间还有多层继承 */
{
public:
    virtual void UpdateTexture2D(
        FRHICommandListBase& RHICmdList,
        FRHITexture2D* TextureRHI,
        uint32 MipIndex,
        const FUpdateTextureRegion2D& UpdateRegion,
        uint32 SourcePitch,
        const uint8* SourceData) override
    {
        FOpenGLTexture* Texture = ResourceCast(TextureRHI);

        // 调用 OpenGL 原生 API（gl 开头的函数）
        glBindTexture(Texture->Target, Texture->Resource);
        glTexSubImage2D(
            Texture->Target, MipIndex,
            UpdateRegion.DestX, UpdateRegion.DestY,
            UpdateRegion.Width, UpdateRegion.Height,
            GL_RGBA, GL_UNSIGNED_BYTE, SourceData
        );
        // ...
    }
};
```

### 8.5 FDynamicRHI 的平台继承树

```
FDynamicRHI（纯虚接口类）
├── FD3D12DynamicRHI              ← DirectX 12 实现
├── FD3D11DynamicRHI              ← DirectX 11 实现
├── FOpenGLDynamicRHI             ← OpenGL 实现（内部有多层中间继承）
├── FMetalDynamicRHI              ← Metal 实现（iOS/macOS）
└── FVulkanDynamicRHI             ← Vulkan 实现
```

全局有一个 `GDynamicRHI` 指针指向当前平台的 `FDynamicRHI` 实例，上层代码通过此指针调用 RHI 操作：

```cpp
// Engine/Source/Runtime/RHI/Public/RHI.h
extern RHI_API FDynamicRHI* GDynamicRHI;
```

---

## 9. 跨平台继承体系总览

将资源类型和操作接口放在一起，完整的 RHI 跨平台体系如下：

### 9.1 资源侧（FRHIResource 体系）

```
FRHIResource（抽象）
├── FRHIUniformBuffer（抽象）
│   ├── FD3D12UniformBuffer       → 内含 ID3D12Resource*（通过 ResourceLocation）
│   └── FOpenGLUniformBuffer      → 内含 GLuint Resource
│
├── FRHITexture（抽象）
│   ├── FD3D12Texture             → 内含 ID3D12Resource*（通过 ResourceLocation）
│   └── FOpenGLTexture            → 内含 GLuint Resource
│
├── FRHIVertexBuffer（抽象）
│   ├── FD3D12VertexBuffer        → ...
│   └── FOpenGLVertexBuffer       → ...
│
├── FRHIShader（抽象）
│   ├── FD3D12VertexShader
│   └── FOpenGLVertexShader
│
└── FRHIGraphicsPipelineState（抽象）
    ├── FD3D12GraphicsPipelineState
    └── FOpenGLGraphicsPipelineState
```

### 9.2 操作侧（FDynamicRHI 体系）

```
FDynamicRHI（抽象）
    定义: CreateTexture / UpdateTexture / CreateUniformBuffer /
          CreateShader / CreatePipelineState / ...
      │
      ├── FD3D12DynamicRHI
      │     实现: 调用 D3D12 API（ID3D12Device、ID3D12GraphicsCommandList 等）
      │
      ├── FOpenGLDynamicRHI
      │     实现: 调用 OpenGL API（glCreateTextures、glTexSubImage2D 等）
      │
      └── FVulkanDynamicRHI
            实现: 调用 Vulkan API（vkCreateImage、vkCmdCopyImage 等）
```

### 9.3 跨平台选择机制

UE5 在构建时通过模块系统决定加载哪个 RHI 模块：

- Windows 平台：加载 `D3D12RHI.dll`，创建 `FD3D12DynamicRHI` 实例
- Android / Linux：加载 `OpenGLDrv.dll` 或 `VulkanRHI.dll`
- iOS / macOS：加载 `MetalRHI.dll`

```cpp
// 运行时初始化时（简化示意）
GDynamicRHI = new FD3D12DynamicRHI(...);   // Windows D3D12
// 或
GDynamicRHI = new FOpenGLDynamicRHI(...); // OpenGL
```

上层代码始终通过 `GDynamicRHI->CreateTexture(...)` 等方式调用，无需感知底层实现。

---

## 10. 上层逻辑的使用方式：UTexture 案例

以引擎中的 `UTexture` 为例，说明上层代码如何通过 RHI 接口操作纹理资源：

```cpp
// Engine/Source/Runtime/Engine/Classes/Engine/Texture.h

class UTexture : public UObject
{
public:
    // 持有 RHI 层纹理句柄（FRHITexture* 的引用包装）
    FTextureRHIRef TextureRHI;

    // 更新纹理内容
    void UpdateTexture(int32 MipIndex, const FUpdateTextureRegion2D& Region,
                       int32 SrcPitch, const uint8* SrcData)
    {
        // 将操作提交到渲染线程
        ENQUEUE_RENDER_COMMAND(UpdateTextureCmd)(
            [this, MipIndex, Region, SrcPitch, SrcData](FRHICommandListImmediate& RHICmdList)
            {
                // 调用 RHI 抽象接口——自动走对应平台实现
                RHICmdList.UpdateTexture2D(
                    TextureRHI,   // FRHITexture*（内含 D3D12 或 OpenGL 资源）
                    MipIndex,
                    Region,
                    SrcPitch,
                    SrcData
                );
            }
        );
    }
};
```

上层逻辑的规范：
- **正确做法**：通过 `RHICmdList.UpdateTexture2D(...)` 等 RHI 接口操作资源。
- **错误做法**：在上层逻辑中直接使用 `cmdList->CopyTextureRegion(...)` 等 D3D12/OpenGL 原生 API。后者会导致代码无法跨平台。

---

## 11. 本讲小结

### RHI 封装思路一句话总结

> **定义抽象基类（FRHIResource / FDynamicRHI），在不同平台的子类中实现真正的 API 调用，上层逻辑只与抽象接口交互。**

### 关键类速查表

| 类名 | 所在层 | 作用 |
|------|--------|------|
| `FRHIResource` | RHI 抽象层 | 所有 GPU 资源的根基类，管理引用计数 |
| `ERHIResourceType` | RHI 抽象层 | 资源类型枚举 |
| `FRHIUniformBuffer` | RHI 抽象层 | Constant/Uniform Buffer 抽象接口 |
| `FRHITexture` | RHI 抽象层 | Texture 抽象接口 |
| `FRHIVertexBuffer` | RHI 抽象层 | Vertex Buffer 抽象接口 |
| `FRHIShader` | RHI 抽象层 | Shader 抽象基类 |
| `FRHIGraphicsPipelineState` | RHI 抽象层 | 图形管线状态对象（含 PSO、Root Signature） |
| `FDynamicRHI` | RHI 抽象层 | 所有 GPU 操作的抽象接口（创建/更新资源等） |
| `FD3D12UniformBuffer` | D3D12 平台层 | UBO 的 D3D12 实现，内含 `ID3D12Resource*` |
| `FD3D12Texture` | D3D12 平台层 | Texture 的 D3D12 实现 |
| `FD3D12ResourceLocation` | D3D12 平台层 | D3D12 资源位置信息（Resource + GPU 地址 + Heap） |
| `FD3D12DynamicRHI` | D3D12 平台层 | D3D12 所有 GPU 操作的实现 |
| `FOpenGLUniformBuffer` | OpenGL 平台层 | UBO 的 OpenGL 实现，内含 `GLuint` |
| `FOpenGLTexture` | OpenGL 平台层 | Texture 的 OpenGL 实现，内含 `GLuint` |
| `FOpenGLDynamicRHI` | OpenGL 平台层 | OpenGL 所有 GPU 操作的实现 |
| `UTexture` | 引擎上层 | 蓝图可用的纹理资源，内含 `FTextureRHIRef` |

### 后续系列预告

- **第 2 讲**：RHI Command List（命令列表）的执行机制
- **第 3 讲**：Shader 代码的具体细节

---

*笔记整理自 B 站 UE5.1 C++ 引擎源码分析系列。类名/函数名均为 UE5.1 源码中的真实命名。*
