# UE5.1 源码分析：Shader 根签名（Root Signature）创建

> B 站 UE5 C++ 引擎源码分析系列 · 第 3 集
> 本集是第 2 集（Shader 基本实现）的补充，聚焦于 Shader 编译创建流程、Root Signature 的构建，以及它们与 D3D12 Pipeline State Object（PSO）的协同关系。

---

## 目录

1. [概述](#1-概述)
2. [什么是根签名（Root Signature）](#2-什么是根签名root-signature)
3. [D3D12 根签名结构](#3-d3d12-根签名结构)
4. [UE5 中 Shader 的创建流程](#4-ue5-中-shader-的创建流程)
   - 4.1 [GlobalShaderMap 与两种初始化模式](#41-globalshadermap-与两种初始化模式)
   - 4.2 [Shader 创建的 RHI 调用链](#42-shader-创建的-rhi-调用链)
   - 4.3 [FShaderResourceCounts：Shader 资源数量统计](#43-fshaderresourcecounts：shader-资源数量统计)
5. [HLSL 编译与 D3D 反射技术](#5-hlsl-编译与-d3d-反射技术)
   - 5.1 [DXC vs FXC 编译器](#51-dxc-vs-fxc-编译器)
   - 5.2 [ID3D12ShaderReflection：从编译结果中提取反射信息](#52-id3d12shaderreflection：从编译结果中提取反射信息)
6. [根签名创建流程详解](#6-根签名创建流程详解)
   - 6.1 [FD3D12RootSignature 封装类](#61-fd3d12rootsignature-封装类)
   - 6.2 [Root Parameter 的两种类型](#62-root-parameter-的两种类型)
   - 6.3 [从 Shader 资源信息构建 Root Parameter](#63-从-shader-资源信息构建-root-parameter)
7. [FD3D12BoundShaderState 与多 Shader 绑定](#7-fd3d12boundshaderstate-与多-shader-绑定)
8. [关键数据结构汇总](#8-关键数据结构汇总)
9. [完整调用链分析](#9-完整调用链分析)
10. [总结](#10-总结)

---

## 1. 概述

本集补充了上一集 Shader 基本实现的几个关键细节：

| 主题 | 核心问题 |
|------|----------|
| Shader 编译流程 | Shader 参数（SRV/CBV/Sampler/UAV 数量）是如何从 HLSL 源码中提取的？ |
| Root Signature 创建 | UE5 如何利用 Shader 参数信息构建 D3D12 Root Signature？ |
| Pipeline State | 整条渲染管线（VS + PS + ...）的 Shader 信息如何汇聚成一个 Root Signature？ |

流程的核心思路是：**编译期**通过 D3D 反射 API 提取每个 Shader 的资源使用数量，**运行时**汇总整条管线所有 Shader 的资源信息，最终驱动 D3D12 原生 Root Signature 的创建。

---

## 2. 什么是根签名（Root Signature）

Root Signature 是 D3D12 的核心机制，它定义了 GPU 管线能够访问哪些资源，以及这些资源以何种方式绑定到着色器寄存器上。

**类比理解**：如果 Shader 是一个函数，Root Signature 就是这个函数的"参数列表声明"——它告诉 GPU 驱动：这个管线需要哪些 Descriptor Table、哪些内联 CBV、哪些 Static Sampler。

**关键特性**：
- 一个 Root Signature 对应整条图形管线（不是单个 Shader）
- 它必须覆盖所有绑定阶段（VS、PS、GS、HS、DS、MS、AS）所需的资源
- Root Signature 在 D3D12 中是显式的，程序员必须手动描述

---

## 3. D3D12 根签名结构

D3D12 原生 Root Signature 由以下三种 Root Parameter 类型组成：

```
D3D12_ROOT_SIGNATURE_DESC
├── NumParameters
├── pParameters[]  (Root Parameters)
│   ├── D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE
│   │   └── D3D12_DESCRIPTOR_RANGE[]
│   │       ├── RangeType: SRV / UAV / CBV / SAMPLER
│   │       ├── NumDescriptors
│   │       └── BaseShaderRegister
│   ├── D3D12_ROOT_PARAMETER_TYPE_CBV  (内联 CBV，直接嵌入根参数)
│   ├── D3D12_ROOT_PARAMETER_TYPE_SRV  (内联 SRV)
│   └── D3D12_ROOT_PARAMETER_TYPE_UAV  (内联 UAV)
├── NumStaticSamplers
└── pStaticSamplers[]
```

在 UE5 中，只使用其中**两种** Root Parameter 类型：
1. **Descriptor Table**：用于 SRV（纹理/Buffer）、UAV、Sampler
2. **内联 CBV（Constant Buffer View）**：用于 Constant Buffer

---

## 4. UE5 中 Shader 的创建流程

### 4.1 GlobalShaderMap 与两种初始化模式

UE5 用一个全局变量 `GGlobalShaderMap` 管理所有 Global Shader 的实例。引擎初始化时调用 `CompileGlobalShaderMap()` 函数，该函数内部支持两种模式：

**模式一：立即全量创建（预编译模式）**

```
引擎启动
  └── CompileGlobalShaderMap()
        └── [配置了立即创建标志]
              └── for each shader type → Get/Create all shaders
```

**模式二：延迟创建（默认模式）**

```
渲染命令需要某个 Shader
  └── GetGlobalShader<TShaderClass>()
        └── 发现缓存中没有该 Shader
              └── 触发创建流程
```

无论哪种模式，最终都会走到同一个 `Get` 函数。该函数的语义是：有则直接返回，无则创建再返回。

### 4.2 Shader 创建的 RHI 调用链

```
GetShader()
  └── 判断是否已创建
        └── [未创建] → 进入 Shader 创建流程
              └── FShaderType::CreateShader()
                    └── [根据 Shader 类型]
                          ├── RHICreateVertexShader()
                          ├── RHICreatePixelShader()
                          ├── RHICreateComputeShader()
                          └── ...
                                └── FD3D12DynamicRHI::RHICreateVertexShader()
                                      └── D3D12 实际创建逻辑
```

`FD3D12DynamicRHI` 是 D3D12 平台的 RHI 实现，`RHICreateXxxShader()` 是平台无关的 RHI 虚函数接口，在 D3D12 后端具体执行 D3D12 的 Shader 对象创建。

### 4.3 FShaderResourceCounts：Shader 资源数量统计

在 `FShaderData`（所有 Shader 的基类，包含 bytecode 和元数据）中，有一个关键成员变量 `FShaderResourceCounts`：

```cpp
// 概念性结构（非完整源码）
struct FShaderResourceCounts
{
    uint8 NumSamplers;          // Sampler 数量
    uint8 NumSRVs;              // Shader Resource View 数量（纹理、Buffer）
    uint8 NumCBs;               // Constant Buffer 数量
    uint8 NumUAVs;              // Unordered Access View 数量（可读写资源）
};

class FShaderData
{
    // ...
    TArray<uint8> Code;                     // 编译后的 Shader 字节码 + Optional Data
    FShaderResourceCounts ResourceCounts;   // 该 Shader 使用的各类资源数量
    // ...
};
```

**这个结构是后续创建 Root Signature 的核心输入**。

---

## 5. HLSL 编译与 D3D 反射技术

### 5.1 DXC vs FXC 编译器

UE5.1 及以上版本默认使用 **DXC**（DirectX Shader Compiler）编译 HLSL 到 DXIL（DirectX Intermediate Language）。较老版本使用 **FXC**（以 `FF` 前缀标识的编译路径）。

在源码中对应两条编译路径：
- `CompileShaderDXC()`（UE5.1+ 的 DXC 路径）
- `CompileShaderFXC()`（旧路径，兼容 D3D11 / SM5 等）

### 5.2 ID3D12ShaderReflection：从编译结果中提取反射信息

这是本集的核心技术点。D3D 编译器在编译 HLSL 时，会在编译产物中**附带完整的反射元数据**，不仅仅是可执行的 GPU 字节码。

**反射信息包含**：
- 每个输入/输出变量的类型与语义
- 绑定的资源列表（纹理、Buffer、Sampler、CBV）
- 每种资源类型的数量
- Constant Buffer 的布局与字段信息

UE5 在 `D3D12Shader.cpp` 的编译函数中，通过以下流程提取反射信息：

```cpp
// 概念性伪代码，展示反射提取流程
void ExtractShaderReflection(IDxcBlob* ShaderBlob, FShaderResourceCounts& OutCounts)
{
    // 1. 从编译产物中获取反射接口
    CComPtr<ID3D12ShaderReflection> Reflection;
    DxcUtils->CreateReflection(&ReflectionData, IID_PPV_ARGS(&Reflection));

    // 2. 获取整体描述
    D3D12_SHADER_DESC ShaderDesc;
    Reflection->GetDesc(&ShaderDesc);

    // 3. 遍历所有绑定资源（for 循环）
    for (uint32 i = 0; i < ShaderDesc.BoundResources; ++i)
    {
        D3D12_SHADER_INPUT_BIND_DESC BindDesc;
        Reflection->GetResourceBindingDesc(i, &BindDesc);

        // 根据资源类型分类统计
        switch (BindDesc.Type)
        {
            case D3D_SIT_TEXTURE:
            case D3D_SIT_STRUCTURED:
            case D3D_SIT_BYTEADDRESS:
                OutCounts.NumSRVs++;
                break;
            case D3D_SIT_SAMPLER:
                OutCounts.NumSamplers++;
                break;
            case D3D_SIT_CBUFFER:
                OutCounts.NumCBs++;
                break;
            case D3D_SIT_UAV_RWTYPED:
            case D3D_SIT_UAV_RWSTRUCTURED:
                OutCounts.NumUAVs++;
                break;
        }
    }
}
```

提取完毕后，`FShaderResourceCounts` 会被**序列化为 Optional Data 附加到 Code 字节数组末尾**，随 `Code` 一起传入 `RHICreateXxxShader()`。在 D3D12 端创建 Shader 对象时，从 `Code` 中解析出这段 Optional Data，将 `FShaderResourceCounts` 存入 `FShaderData` 成员变量，完成持久化。

---

## 6. 根签名创建流程详解

### 6.1 FD3D12RootSignature 封装类

UE5 在 `D3D12RootSignature.h/.cpp` 中定义了 `FD3D12RootSignature` 类，它封装了 D3D12 原生的 `ID3D12RootSignature` 对象。

```cpp
// 概念性结构
class FD3D12RootSignature
{
public:
    // 构造函数接收整条管线所有 Shader 的绑定信息
    FD3D12RootSignature(FD3D12Adapter* Adapter,
                        const FD3D12QuantizedBoundShaderState& QBSS);

private:
    CComPtr<ID3D12RootSignature> RootSignature;  // D3D12 原生根签名对象
    // ...
};
```

构造函数的核心参数 `FD3D12QuantizedBoundShaderState`（以下简称 QBSS）包含了整条图形管线（VS + PS + ...）所有 Shader 的 `FShaderResourceCounts` 汇总信息。

### 6.2 Root Parameter 的两种类型

UE5 在构建 Root Signature 时，将 D3D12 的三种 Root Parameter 类型简化为两种：

| UE5 类型 | 对应 D3D12 类型 | 包含资源 |
|----------|----------------|----------|
| Descriptor Table | `D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE` | SRV、UAV、Sampler |
| 内联 CBV | `D3D12_ROOT_PARAMETER_TYPE_CBV` | Constant Buffer |

**两种类型的取舍原因**：
- **Descriptor Table** 适合数量多但变化频率低的资源，一次绑定覆盖多个描述符
- **内联 CBV** 适合数量少但需要频繁更新的 Constant Buffer（每帧变化的矩阵等）

### 6.3 从 Shader 资源信息构建 Root Parameter

在 `FD3D12RootSignature` 的构造函数中，有一个 for 循环遍历所有 Shader 阶段（VS、PS、CS 等），为每个阶段的每种资源类型生成对应的 Root Parameter：

```cpp
// 概念性伪代码，展示 Root Parameter 构建过程
void FD3D12RootSignature::Init(const FD3D12QuantizedBoundShaderState& QBSS)
{
    TArray<D3D12_ROOT_PARAMETER> RootParameters;
    TArray<D3D12_DESCRIPTOR_RANGE> DescriptorRanges;

    // 遍历每个 Shader 阶段
    for (uint32 ShaderStage = 0; ShaderStage < SF_NumFrequencies; ++ShaderStage)
    {
        const FShaderResourceCounts& Counts = QBSS.RegisterCounts[ShaderStage];
        D3D12_SHADER_VISIBILITY Visibility = GetShaderVisibility(ShaderStage);

        // 1. 为 SRV 创建 Descriptor Table
        if (Counts.NumSRVs > 0)
        {
            D3D12_DESCRIPTOR_RANGE Range = {};
            Range.RangeType          = D3D12_DESCRIPTOR_RANGE_TYPE_SRV;
            Range.NumDescriptors     = Counts.NumSRVs;
            Range.BaseShaderRegister = 0;
            DescriptorRanges.Add(Range);

            D3D12_ROOT_PARAMETER Param = {};
            Param.ParameterType                       = D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;
            Param.DescriptorTable.NumDescriptorRanges = 1;
            Param.DescriptorTable.pDescriptorRanges   = &DescriptorRanges.Last();
            Param.ShaderVisibility                    = Visibility;
            RootParameters.Add(Param);
        }

        // 2. 为 Sampler 创建 Descriptor Table
        if (Counts.NumSamplers > 0)
        {
            // ... 类似 SRV，Range.RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_SAMPLER
        }

        // 3. 为 CBV 创建内联 Root Parameter
        if (Counts.NumCBs > 0)
        {
            D3D12_ROOT_PARAMETER Param = {};
            Param.ParameterType             = D3D12_ROOT_PARAMETER_TYPE_CBV;
            Param.Descriptor.ShaderRegister = 0;
            Param.ShaderVisibility          = Visibility;
            RootParameters.Add(Param);
        }

        // UAV 类似处理...
    }

    // 构建 Root Signature Desc
    D3D12_ROOT_SIGNATURE_DESC Desc = {};
    Desc.NumParameters = RootParameters.Num();
    Desc.pParameters   = RootParameters.GetData();
    Desc.Flags         = D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;

    // 序列化
    CComPtr<ID3DBlob> SignatureBlob;
    CComPtr<ID3DBlob> ErrorBlob;
    D3D12SerializeRootSignature(&Desc, D3D_ROOT_SIGNATURE_VERSION_1, &SignatureBlob, &ErrorBlob);

    // 最终调用 D3D12 原始 API 创建根签名
    Device->CreateRootSignature(
        0,
        SignatureBlob->GetBufferPointer(),
        SignatureBlob->GetBufferSize(),
        IID_PPV_ARGS(&RootSignature)
    );
}
```

---

## 7. FD3D12BoundShaderState 与多 Shader 绑定

Root Signature 对应的不是单个 Shader，而是**整条图形管线**的所有 Shader。UE5 通过 `FD3D12BoundShaderState` 类（及其 Key 结构 `FD3D12QuantizedBoundShaderState`）来汇聚管线中所有 Shader 的资源信息。

**继承关系**：所有具体 Shader 类型都继承自 `FShaderData`：

```
FShaderData                  ← 基类（含 Code、FShaderResourceCounts）
  ├── FVertexShaderRHIRef     ← 顶点着色器
  ├── FPixelShaderRHIRef      ← 像素着色器
  ├── FMeshShaderRHIRef       ← Mesh Shader（网格着色器）
  ├── FAmplificationShaderRHIRef  ← Amplification Shader（放大着色器）
  └── FComputeShaderRHIRef    ← 计算着色器
```

**Pipeline State 创建时的信息汇聚流程**：

```cpp
// 概念性伪代码
FD3D12QuantizedBoundShaderState BuildQBSS(const FGraphicsPipelineStateInitializer& Init)
{
    FD3D12QuantizedBoundShaderState QBSS = {};

    // 从 Pipeline 初始化信息中取出每个 Shader
    // 每个 Shader 都是 FShaderData 的子类，都有 ResourceCounts 成员
    if (Init.BoundShaderState.VertexShaderRHI)
    {
        FShaderData* VS = static_cast<FShaderData*>(Init.BoundShaderState.VertexShaderRHI);
        QBSS.RegisterCounts[SF_Vertex] = VS->ResourceCounts;
    }
    if (Init.BoundShaderState.PixelShaderRHI)
    {
        FShaderData* PS = static_cast<FShaderData*>(Init.BoundShaderState.PixelShaderRHI);
        QBSS.RegisterCounts[SF_Pixel] = PS->ResourceCounts;
    }
    // Mesh Shader、Amplification Shader 类似...

    return QBSS;
}
```

此后，`QBSS` 被传入 `FD3D12RootSignature` 的构造函数，一次性涵盖整条管线所有阶段的资源绑定需求。

---

## 8. 关键数据结构汇总

| 数据结构 | 所在模块 | 职责 |
|----------|---------|------|
| `FShaderResourceCounts` | `ShaderCore.h` | 记录单个 Shader 使用的 Sampler/SRV/CBV/UAV 数量 |
| `FShaderData` | `ShaderCore.h` | Shader 基类，持有 bytecode (`Code`) 和 `FShaderResourceCounts` |
| `FD3D12QuantizedBoundShaderState` (QBSS) | `D3D12Util.h` | 汇聚整条管线所有 Shader 的 `FShaderResourceCounts`，是创建 Root Signature 的直接输入 |
| `FD3D12BoundShaderState` | `D3D12StateCachePrivate.h` | 封装绑定到管线的所有 Shader 对象，持有对应的 Root Signature 引用 |
| `FD3D12RootSignature` | `D3D12RootSignature.h` | 封装 D3D12 原生 `ID3D12RootSignature`，由 QBSS 驱动创建 |
| `FGlobalShaderMap` | `GlobalShader.h` | 全局 Shader Map，管理所有 Global Shader 实例 |
| `ID3D12ShaderReflection` | D3D12 SDK | D3D 反射接口，用于从编译产物中提取资源绑定信息 |

---

## 9. 完整调用链分析

### 链路一：Shader 编译 → 资源信息入库

```
[编译阶段]
CompileShaderDXC()  (或 CompileShaderFXC())
  └── DXC 编译 HLSL → DXIL 字节码 + 反射元数据
        └── CreateReflection() → ID3D12ShaderReflection
              └── for (BoundResources) → GetResourceBindingDesc()
                    └── 统计 NumSRVs / NumSamplers / NumCBs / NumUAVs
                          └── 序列化为 FShaderResourceCounts
                                └── 附加到 Code（Optional Data）
                                      └── 作为编译结果返回

[运行时 Shader 对象创建]
RHICreateVertexShader(Code)
  └── FD3D12DynamicRHI::RHICreateVertexShader()
        └── 从 Code 中解析 Optional Data → FShaderResourceCounts
              └── 存入 FShaderData::ResourceCounts
```

### 链路二：PSO 创建 → Root Signature 构建

```
RHICreateGraphicsPipelineState(Initializer)
  └── FD3D12DynamicRHI::RHICreateGraphicsPipelineState()
        └── BuildQBSS(Initializer)
              └── for each ShaderStage (VS/MS/AS/PS/...)
                    └── FShaderData::ResourceCounts → QBSS.RegisterCounts[stage]

        └── GetRootSignature(QBSS)
              └── 查 Root Signature 缓存（按 QBSS hash）
                    └── [Cache Miss] → FD3D12RootSignature(Device, QBSS)
                          └── for each ShaderStage:
                                └── 构建 D3D12_ROOT_PARAMETER (DescriptorTable / CBV)
                          └── 构建 D3D12_ROOT_SIGNATURE_DESC
                          └── D3D12SerializeRootSignature()  → Blob
                          └── ID3D12Device::CreateRootSignature()  ← D3D12 原生 API
```

---

## 10. 总结

本集梳理了从 HLSL 编译到 D3D12 Root Signature 最终创建的完整链路，核心要点如下：

**1. 资源数量信息的来源**
编译阶段利用 D3D 反射 API（`ID3D12ShaderReflection`）自动提取 HLSL 代码绑定的 Sampler/SRV/CBV/UAV 数量，无需开发者手工填写。这些数量以 `FShaderResourceCounts` 的形式附加在编译产物中，随 Shader 对象持久化。

**2. Root Signature 的输入是整条管线**
一个 Root Signature 覆盖图形管线中的所有着色器阶段（VS、PS、Mesh Shader 等）。UE5 通过 `FD3D12QuantizedBoundShaderState` 将各阶段的资源数量汇聚，作为 Root Signature 的构建依据。

**3. UE5 只使用两种 Root Parameter 类型**
UE5 简化了 D3D12 的 Root Parameter 多样性，只使用 Descriptor Table（覆盖 SRV/UAV/Sampler）和内联 CBV，兼顾灵活性与性能。

**4. Shader 创建有两种触发模式**
引擎启动时可预编译全部 Global Shader，或按需延迟创建。两种模式最终走相同的 RHI → D3D12 创建路径。

**后续方向**：掌握这些基础后，即可开始编写实际的渲染命令（Render Command），构建自定义 Render Pass，向 GPU 提交真正的渲染工作。
