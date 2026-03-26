# UE5.1 C++ 引擎源码分析 —— 渲染 Shader 系统

> 来源：B 站《UE5.1 C++ 引擎源码分析》系列第 2 集
> 主题：Shader 系统底层架构、类层次、创建流程与反射机制
> 时长：约 44 分钟

---

## 目录

1. [概述](#1-概述)
2. [RHI 层 Shader 类体系](#2-rhi-层-shader-类体系)
   - 2.1 [FRHIShader 基类](#21-frhishader-基类)
   - 2.2 [平台子类继承结构](#22-平台子类继承结构)
3. [Shader 创建流程（RHICreate）](#3-shader-创建流程-rhicreate)
   - 3.1 [接口定义（DynamicRHI）](#31-接口定义-dynamicrhi)
   - 3.2 [OpenGL 实现](#32-opengl-实现)
   - 3.3 [D3D12 实现](#33-d3d12-实现)
4. [Shader 二进制格式与 FShaderCodeReader](#4-shader-二进制格式与-fshadercodereader)
5. [上层 Shader 类体系（FShader 家族）](#5-上层-shader-类体系-fshader-家族)
   - 5.1 [FShader 基类](#51-fshader-基类)
   - 5.2 [FGlobalShader / FMaterialShader / FMeshMaterialShader](#52-fglobalshader--fmaterialshader--fmeshmaterialshader)
6. [Shader Permutation（排列组合编译）](#6-shader-permutation排列组合编译)
7. [Shader 的使用方式（宏接口）](#7-shader-的使用方式宏接口)
8. [FTypeLayout —— Shader 自定义反射机制](#8-ftypelayout--shader-自定义反射机制)
   - 8.1 [为什么需要自定义反射](#81-为什么需要自定义反射)
   - 8.2 [LAYOUT_FIELD 宏展开分析](#82-layout_field-宏展开分析)
   - 8.3 [InternalLinkTime 链式模板结构](#83-internalLinktime-链式模板结构)
9. [Shader 参数收集机制](#9-shader-参数收集机制)
   - 9.1 [BEGIN/END_SHADER_PARAMETER_STRUCT 宏](#91-beginend_shader_parameter_struct-宏)
   - 9.2 [do-while 函数指针链](#92-do-while-函数指针链)
10. [IMPLEMENT_GLOBAL_SHADER 注册流程](#10-implement_global_shader-注册流程)
11. [完整流程总结](#11-完整流程总结)
12. [关键类继承树（ASCII）](#12-关键类继承树ascii)

---

## 1. 概述

UE5 的 Shader 系统分为两个层次：

| 层次 | 代表类 | 职责 |
|------|--------|------|
| **RHI 层（底层）** | `FRHIShader` 及平台子类 | 封装平台 Shader 对象（D3D12 ByteCode、GL program handle 等） |
| **逻辑层（上层）** | `FShader` / `FGlobalShader` 等 | 管理参数、反射、Permutation、与 USF 文件的绑定 |

两层之间通过 `RHICreate*Shader()` 接口连接。上层编译好的字节码通过 `FShaderCode` 传给 RHI 层，RHI 层负责调用平台 API 创建硬件 Shader 对象。

---

## 2. RHI 层 Shader 类体系

### 2.1 FRHIShader 基类

`FRHIShader` 位于 `Engine/Source/Runtime/RHI/Public/RHIResources.h`，是所有 RHI 层 Shader 的根基类。

它遵循 UE RHI 资源封装的统一思路：

- 在 `RHI` 模块定义通用基类
- 在 D3D12、OpenGL、Vulkan 等平台模块中实现平台子类

**FRHIShader 核心成员：**

```cpp
class FRHIShader : public FRHIResource
{
public:
    // Shader 类型枚举（顶点、像素、Compute、Mesh 等）
    EShaderFrequency Frequency;

    // 名字（调试用）
    FString ShaderName;

    // 哈希（用于缓存查找）
    FSHAHash Hash;
};
```

`EShaderFrequency` 枚举定义了 Shader 的类型：

```cpp
enum EShaderFrequency
{
    SF_Vertex   = 0,   // 顶点着色器
    SF_Mesh     = 1,   // Mesh Shader（UE5 新增）
    SF_Amplification = 2,
    SF_Pixel    = 5,   // 像素着色器
    SF_Geometry = 6,
    SF_Compute  = 7,   // Compute Shader
    ...
};
```

### 2.2 平台子类继承结构

在 `FRHIShader` 之上，先有一层 `FRHIGraphicsShader`，然后才是具体的着色器类型：

```
FRHIResource
└── FRHIShader
    ├── FRHIGraphicsShader
    │   ├── FRHIVertexShader
    │   ├── FRHIPixelShader
    │   ├── FRHIMeshShader
    │   └── FRHIGeometryShader
    └── FRHIComputeShader
```

这些类在 RHI 层**非常轻量**，基本没有新增成员变量，只是初始化了父类的 `Frequency` 枚举值。

**平台实现子类示例（D3D12）：**

```
FRHIVertexShader
└── FD3D12VertexShader
        （继承自 FD3D12ShaderData）
```

`FD3D12ShaderData` 是 D3D12 平台 Shader 的核心数据持有者，存储了：
- 编译好的 HLSL bytecode（以 `D3D12_SHADER_BYTECODE` 形式存储）
- Feature Level 等元数据

D3D12 的"创建 Shader"操作非常简单——直接把 bytecode 地址存起来，运行时通过指针转换得到 `D3D12_SHADER_BYTECODE` 即可，无需二次编译。

**平台实现子类示例（OpenGL）：**

```
FRHIVertexShader
└── FOpenGLVertexShader
        （需要在 GL 驱动中实际编译 GLSL）
```

OpenGL 的 Shader 对象用一个 `GLuint`（无符号整数 handle）表示，需要调用 `glShaderSource` + `glCompileShader`。

---

## 3. Shader 创建流程（RHICreate）

### 3.1 接口定义（DynamicRHI）

创建 Shader 的接口定义在 `Engine/Source/Runtime/RHI/Public/DynamicRHI.h`：

```cpp
class FDynamicRHI
{
public:
    virtual FVertexShaderRHIRef RHICreateVertexShader(
        TArrayView<const uint8> Code,
        const FSHAHash& Hash) = 0;

    virtual FPixelShaderRHIRef RHICreatePixelShader(
        TArrayView<const uint8> Code,
        const FSHAHash& Hash) = 0;

    virtual FComputeShaderRHIRef RHICreateComputeShader(
        TArrayView<const uint8> Code,
        const FSHAHash& Hash) = 0;

    // ... 其他类型
};
```

实现由各平台子类（`FD3D12DynamicRHI`、`FOpenGLDynamicRHI` 等）提供。

### 3.2 OpenGL 实现

OpenGL 的 `RHICreateVertexShader` 实现大致步骤：

```cpp
// 伪代码，展示核心流程
FVertexShaderRHIRef FOpenGLDynamicRHI::RHICreateVertexShader(
    TArrayView<const uint8> Code, const FSHAHash& Hash)
{
    // 1. 用 FShaderCodeReader 解析传入的内存块
    //    因为 Code 不只包含着色器代码，还附带了 optional data
    FShaderCodeReader ShaderCode(Code);

    // 2. HLSL -> GLSL 转换（跨平台适配）
    //    使用 mcpp + hlslcc 等工具链做转换
    //    转换过程是 GL 平台特有的，D3D12 不需要
    FAnsiString GLSLCode = ConvertHLSLToGLSL(ShaderCode.GetActualCode());

    // 3. 创建 GL shader 对象
    GLuint Resource = glCreateShader(GL_VERTEX_SHADER);

    // 4. 上传并编译 GLSL 源码
    const char* SourcePtr = *GLSLCode;
    glShaderSource(Resource, 1, &SourcePtr, nullptr);
    glCompileShader(Resource);

    // 5. 检查编译错误
    GLint CompileStatus;
    glGetShaderiv(Resource, GL_COMPILE_STATUS, &CompileStatus);
    if (CompileStatus == GL_FALSE)
    {
        // 错误处理...
    }

    // 6. 返回 RHI 对象
    return new FOpenGLVertexShader(Resource);
}
```

关键点：OpenGL 平台需要经历 HLSL → GLSL 的二次转换（`mcpp` + `H2SCC` 工具链），这是与 D3D12 的最大区别。

### 3.3 D3D12 实现

D3D12 的实现简洁得多——HLSL 编译早在离线阶段（shader cook 时）就已完成，运行时直接把 bytecode 存起来即可：

```cpp
// 伪代码
FVertexShaderRHIRef FD3D12DynamicRHI::RHICreateVertexShader(
    TArrayView<const uint8> Code, const FSHAHash& Hash)
{
    // 解析 optional data
    FShaderCodeReader ShaderCode(Code);

    FD3D12VertexShader* Shader = new FD3D12VertexShader();

    // 读取 optional data 中的各种元数据并赋值
    // ...

    // 核心：直接把代码地址存储为 D3D12_SHADER_BYTECODE
    // 运行时用到时直接转换指针即可，不需要二次编译
    Shader->Code = TArrayView<const uint8>(Code.GetData(), ShaderCode.GetActualCodeSize());

    return Shader;
}
```

---

## 4. Shader 二进制格式与 FShaderCodeReader

UE 传给 `RHICreate*Shader` 的内存块**不是纯粹的 bytecode**，而是一个包含 optional data 的复合内存块：

```
[ Shader Bytecode (N bytes) ][ Optional Data (M bytes) ][ int32: M ]
                                                          ^---- 末尾 4 字节
```

末尾的 `int32` 存储 optional data 的长度 M。通过此值可以推算 bytecode 的长度 = 总长 - M - 4。

**FShaderCodeReader 解析逻辑（伪代码）：**

```cpp
class FShaderCodeReader
{
    TArrayView<const uint8> WholeCode; // 整段内存

public:
    // 获取 optional data 的长度
    int32 GetOptionalDataSize() const
    {
        // 末尾 4 字节强转为 int32
        const uint8* End = WholeCode.GetData() + WholeCode.Num();
        return *reinterpret_cast<const int32*>(End - sizeof(int32));
    }

    // 获取真正 shader bytecode 的长度
    int32 GetActualCodeSize() const
    {
        return WholeCode.Num() - GetOptionalDataSize() - sizeof(int32);
    }

    // 按 key 查找 optional data
    const uint8* FindOptionalData(uint8 InKey, int32& OutSize) const
    {
        int32 OptSize = GetOptionalDataSize();
        const uint8* DataStart = WholeCode.GetData() + GetActualCodeSize();
        const uint8* Cur = DataStart;
        const uint8* End = DataStart + OptSize;

        while (Cur < End)
        {
            uint8 Key = *Cur++;
            int32 Size = *reinterpret_cast<const int32*>(Cur);
            Cur += sizeof(int32);
            if (Key == InKey)
            {
                OutSize = Size;
                return Cur;
            }
            Cur += Size;
        }
        return nullptr;
    }

    // 模板便捷版本：直接转换为指定类型
    template<typename T>
    const T* FindOptionalData(uint8 InKey) const
    {
        int32 Size;
        const uint8* Data = FindOptionalData(InKey, Size);
        return reinterpret_cast<const T*>(Data);
    }
};
```

这个格式设计的好处是：在保持 bytecode 连续存储的同时，可以在同一块内存里附带调试信息、Feature Level、Uniform Buffer 布局等额外数据。

---

## 5. 上层 Shader 类体系（FShader 家族）

### 5.1 FShader 基类

`FShader` 位于 `Engine/Source/Runtime/RenderCore/Public/Shader.h`，是所有上层 Shader 类的基类，不继承 `UObject`。

核心职责：

- 存储 Shader 的 **Type Layout**（自定义反射信息）
- 管理 **Permutation**（排列组合编译变体）
- 提供 `ShouldCompilePermutation()` 等生命周期钩子
- 通过 `GetTypeLayout()` 暴露参数元数据

**FShader 核心接口（简化）：**

```cpp
class FShader
{
public:
    // 子类必须实现：是否需要编译某个 Permutation
    static bool ShouldCompilePermutation(
        const FShaderPermutationParameters& Parameters);

    // 类型标识
    virtual EShaderFrequency GetFrequency() const = 0;

    // 获取此类型的 TypeLayout（收集了所有反射信息）
    static const FTypeLayout& GetTypeLayout();

    // Permutation ID（同一份 USF 不同编译选项的编号）
    int32 PermutationId;
};
```

### 5.2 FGlobalShader / FMaterialShader / FMeshMaterialShader

UE5 的上层 Shader 类按使用场景分为三大类：

| 类名 | 适用场景 | 典型例子 |
|------|----------|----------|
| `FGlobalShader` | 全局 Pass，不依赖材质 | 后处理、Shadow Depth、FullScreen Pass |
| `FMaterialShader` | 依赖材质参数，但不与 Mesh 绑定 | 一些通用材质效果 |
| `FMeshMaterialShader` | 依赖材质 + Mesh 顶点工厂 | 最常见的渲染 Shader |

继承关系：

```
FShader
├── FGlobalShader
├── FMaterialShader
│   └── FMeshMaterialShader
└── （其他）
```

**平时最常用的是 `FGlobalShader`**，例如自定义的全屏后处理效果：

```cpp
class FMyFullscreenVS : public FGlobalShader
{
    DECLARE_GLOBAL_SHADER(FMyFullscreenVS);
    SHADER_USE_PARAMETER_STRUCT(FMyFullscreenVS, FGlobalShader);

    BEGIN_SHADER_PARAMETER_STRUCT(FParameters, )
        SHADER_PARAMETER_STRUCT_REF(FViewUniformShaderParameters, View)
        SHADER_PARAMETER_TEXTURE(Texture2D, SceneColor)
        SHADER_PARAMETER_SAMPLER(SamplerState, SceneColorSampler)
    END_SHADER_PARAMETER_STRUCT()

    static bool ShouldCompilePermutation(
        const FGlobalShaderPermutationParameters& Parameters)
    {
        return IsFeatureLevelSupported(Parameters.Platform, ERHIFeatureLevel::SM5);
    }
};

IMPLEMENT_GLOBAL_SHADER(
    FMyFullscreenVS,                     // C++ 类名
    "/Engine/Private/MyFullscreen.usf",  // USF 文件路径
    "MainVS",                            // 入口函数名
    SF_Vertex                            // Shader 类型
);
```

---

## 6. Shader Permutation（排列组合编译）

USF 文件中经常出现类似 C++ 预处理器的条件编译代码：

```hlsl
// MyShader.usf
void MainPS(...)
{
#if USE_AMBIENT_OCCLUSION
    float AO = SampleAO(UV);
#else
    float AO = 1.0f;
#endif

#if ENABLE_FOG
    Color = ApplyFog(Color, Depth);
#endif
}
```

每种开关组合都会被编译成一个独立的 Shader 二进制——这就是 **Permutation**。

**在 C++ 端声明 Permutation：**

```cpp
class FMyShaderPS : public FGlobalShader
{
public:
    // 声明 bool 类型的 Permutation 维度
    class FUseAmbientOcclusionDim : SHADER_PERMUTATION_BOOL("USE_AMBIENT_OCCLUSION");
    class FEnableFogDim           : SHADER_PERMUTATION_BOOL("ENABLE_FOG");

    using FPermutationDomain = TShaderPermutationDomain<
        FUseAmbientOcclusionDim,
        FEnableFogDim
    >;

    static bool ShouldCompilePermutation(
        const FGlobalShaderPermutationParameters& Parameters)
    {
        // 可以在这里过滤掉不需要的 Permutation 组合
        // 2 个 bool 维度 = 4 种组合，全部编译：
        return true;
    }
};
```

运行时选择 Permutation：

```cpp
FMyShaderPS::FPermutationDomain PermutationVector;
PermutationVector.Set<FMyShaderPS::FUseAmbientOcclusionDim>(bUseAO);
PermutationVector.Set<FMyShaderPS::FEnableFogDim>(bEnableFog);

TShaderMapRef<FMyShaderPS> PixelShader(
    GetGlobalShaderMap(FeatureLevel), PermutationVector);
```

UE 会在 Cook 阶段把所有可能的 Permutation 预编译并缓存；运行时命中缓存直接取用，不重新编译。

---

## 7. Shader 的使用方式（宏接口）

使用 `FGlobalShader` 的完整步骤：

### 步骤 1：继承并声明

```cpp
class FMyShaderVS : public FGlobalShader
{
    // 必须加的两个宏
    DECLARE_GLOBAL_SHADER(FMyShaderVS);
    SHADER_USE_PARAMETER_STRUCT(FMyShaderVS, FGlobalShader);

    // 声明参数结构体
    BEGIN_SHADER_PARAMETER_STRUCT(FParameters, )
        SHADER_PARAMETER_STRUCT_REF(FViewUniformShaderParameters, View)
        SHADER_PARAMETER_TEXTURE(Texture2D, InputTexture)
        SHADER_PARAMETER_SAMPLER(SamplerState, InputSampler)
        RENDER_TARGET_BINDING_SLOTS()
    END_SHADER_PARAMETER_STRUCT()
};
```

### 步骤 2：注册

```cpp
// 在 .cpp 文件中
IMPLEMENT_GLOBAL_SHADER(
    FMyShaderVS,
    "/Engine/Private/MyShader.usf",
    "MainVS",
    SF_Vertex);
```

### 步骤 3：渲染线程中使用

```cpp
void RenderPass(FRHICommandList& RHICmdList, ...)
{
    TShaderMapRef<FMyShaderVS> VertexShader(View.ShaderMap);

    FMyShaderVS::FParameters* PassParameters =
        GraphBuilder.AllocParameters<FMyShaderVS::FParameters>();
    PassParameters->View = View.ViewUniformBuffer;
    PassParameters->InputTexture = InputTextureRHI;
    PassParameters->InputSampler = TStaticSamplerState<SF_Linear>::GetRHI();

    // 绑定 RHI 管线并 Dispatch
    GraphBuilder.AddPass(
        RDG_EVENT_NAME("MyPass"),
        PassParameters,
        ERDGPassFlags::Raster,
        [VertexShader, PassParameters](FRHICommandList& RHICmdList)
        {
            SetShaderParameters(RHICmdList, VertexShader, VertexShader.GetVertexShader(), *PassParameters);
            // ...
        });
}
```

---

## 8. FTypeLayout —— Shader 自定义反射机制

### 8.1 为什么需要自定义反射

`FShader` 及其子类**不继承 `UObject`**，因此无法使用 UE 的标准属性反射（`UPROPERTY` + UHT）。

但 Shader 系统需要反射能力：
- 运行时遍历参数成员，按名字绑定 Uniform Buffer 数据
- 序列化/反序列化 Shader 缓存
- 参数校验

UE 为此设计了 `FTypeLayout` 系统，用宏 + 模板元编程实现了一套独立的反射机制。

### 8.2 LAYOUT_FIELD 宏展开分析

在 `FShader` 子类中用 `LAYOUT_FIELD` 声明需要反射的成员：

```cpp
class FMyShader : public FGlobalShader
{
    DECLARE_GLOBAL_SHADER(FMyShader);

    // 声明需要参与反射的成员变量
    LAYOUT_FIELD(FShaderParameter, MyFloatParam);
    LAYOUT_FIELD(FShaderResourceParameter, MyTexture);
};
```

`LAYOUT_FIELD(Type, Name)` 宏展开后大致等价于：

```cpp
// 1. 定义真正的成员变量
Type Name;

// 2. 对模板参数 __COUNTER__ 做特化，提供 Initialize 方法
template<>
struct InternalLinkTime<__COUNTER__>
{
    static void Initialize(FTypeLayout& Layout)
    {
        // 先递归调用编号-1 的 Initialize，形成链式收集
        InternalLinkTime<__COUNTER__ - 1>::Initialize(Layout);

        // 再把本字段的反射信息加入 Layout
        // 包括：字段名称字符串、字段在对象内的 offset
        Layout.AddField(
            TEXT(#Name),                           // 字段名（字符串）
            offsetof(ThisClass, Name),             // 字段偏移
            GetTypeHash(TTypeName<Type>::GetName()) // 字段类型 hash
        );
    }
};
```

### 8.3 InternalLinkTime 链式模板结构

核心机制是一个以整数为模板参数的模板结构体：

```cpp
// 默认实现：什么都不做（终止递归）
template<int32 N>
struct InternalLinkTime
{
    static void Initialize(FTypeLayout& Layout) { /* 空实现 */ }
};
```

每次用 `LAYOUT_FIELD` 宏定义一个字段，就会生成一个 `InternalLinkTime<N>` 的特化版本：

```cpp
template<>
struct InternalLinkTime<1>  // 第 1 个字段
{
    static void Initialize(FTypeLayout& Layout)
    {
        InternalLinkTime<0>::Initialize(Layout); // 调 0 号 → 空实现（终止）
        Layout.AddField("MyFloatParam", offset_of_MyFloatParam, ...);
    }
};

template<>
struct InternalLinkTime<2>  // 第 2 个字段
{
    static void Initialize(FTypeLayout& Layout)
    {
        InternalLinkTime<1>::Initialize(Layout); // 调 1 号 → 收集第 1 个字段
        Layout.AddField("MyTexture", offset_of_MyTexture, ...);
    }
};
```

N 的自增利用了编译器内建宏 `__COUNTER__`，每次出现就自动加 1。

**收集过程（调用 Initialize(1, 2, ... N) 的效果）：**

```
调用 InternalLinkTime<2>::Initialize(Layout)
  → 调用 InternalLinkTime<1>::Initialize(Layout)
      → 调用 InternalLinkTime<0>::Initialize(Layout)  [空实现，返回]
      → AddField("MyFloatParam", ...)                  [收集字段1]
  → AddField("MyTexture", ...)                         [收集字段2]
```

最终结果：`Layout` 中按序存储了所有字段的反射信息。

**offset 的计算方式：**

```cpp
// 用零指针强转技巧计算成员偏移
uint32 Offset = (uint32)(
    (char*)(&((ThisClass*)0)->MemberName)
    - (char*)((ThisClass*)0)
);
```

这等价于 `offsetof(ThisClass, MemberName)`，拿到字段相对于对象起始地址的字节偏移。之后任意时刻，只要拿到对象指针加上此 offset，就能访问到该字段。

---

## 9. Shader 参数收集机制

### 9.1 BEGIN/END_SHADER_PARAMETER_STRUCT 宏

Shader 参数（传入 GPU 的 Uniform 数据）用专门的宏声明结构体：

```cpp
BEGIN_SHADER_PARAMETER_STRUCT(FMyShaderParameters, )
    SHADER_PARAMETER_STRUCT_REF(FViewUniformShaderParameters, View)
    SHADER_PARAMETER_TEXTURE(Texture2D, SceneColor)
    SHADER_PARAMETER_SAMPLER(SamplerState, SceneColorSampler)
    SHADER_PARAMETER(float, MyFloat)
    SHADER_PARAMETER(FVector4f, MyVec4)
END_SHADER_PARAMETER_STRUCT()
```

宏展开后会：
1. 定义一个 `struct FMyShaderParameters { ... }` 结构体，包含所有声明的成员变量
2. 在结构体内生成一个 `TypeInfo` 内嵌结构体，提供 `GetMembers()` 函数
3. `GetMembers()` 通过函数指针链收集所有参数的元数据

### 9.2 do-while 函数指针链

参数收集使用了和 `FTypeLayout` 类似但实现略有区别的链式结构。

`END_SHADER_PARAMETER_STRUCT()` 宏展开的 `TypeInfo::GetMembers()` 大致实现：

```cpp
static void GetMembers(TArray<FShaderParameterMemberInfo>& OutMembers)
{
    // do-while 循环遍历函数指针链
    auto* NextFunc = &GetLastMemberFunc;  // 从最后一个参数的收集函数开始
    do
    {
        NextFunc = (*NextFunc)(OutMembers);  // 执行当前函数，返回上一个函数指针
    } while (NextFunc != nullptr);          // 直到返回 nullptr（begin 处）
}
```

每个 `SHADER_PARAMETER(...)` 宏为参数 X 生成一个函数：

```cpp
// 参数 X 的收集函数
static GetMemberFuncPtr* CollectParam_X(TArray<FShaderParameterMemberInfo>& OutMembers)
{
    // 收集参数 X 的信息（名称、offset、类型）
    OutMembers.Add({
        TEXT("MyFloat"),
        offsetof(FMyShaderParameters, MyFloat),
        EUniformBufferBaseType::UBMT_FLOAT32,
        sizeof(float)
    });

    // 返回上一个参数（Y）的收集函数指针，形成链
    return &CollectParam_Y;
}
```

链的顺序是**逆序**的（从最后一个参数开始），通过每个函数返回"上一个"的函数指针来串联：

```
CollectParam_Z → 收集 Z 的信息 → 返回 CollectParam_Y
CollectParam_Y → 收集 Y 的信息 → 返回 CollectParam_X
CollectParam_X → 收集 X 的信息 → 返回 nullptr（begin 处）
nullptr        → do-while 退出
```

最终 `OutMembers` 中存储了所有参数的完整元数据，引擎可以凭此在渲染时自动完成参数绑定。

**USE_SHADER_PARAMETER_STRUCT 宏的作用：**

```cpp
SHADER_USE_PARAMETER_STRUCT(FMyShader, FGlobalShader);
```

展开后将 `FMyShaderParameters::TypeInfo::GetMembers()` 与 `FMyShader` 的类型信息连接起来，使引擎能够通过 `GetTypeLayout()` 访问参数元数据。

---

## 10. IMPLEMENT_GLOBAL_SHADER 注册流程

`IMPLEMENT_GLOBAL_SHADER` 宏将 C++ 类与 USF 文件、入口函数名、Shader 类型绑定，并生成关键的静态注册代码。

展开后核心内容：

```cpp
// 实现 GetTypeLayout 静态函数
const FTypeLayout& FMyShaderVS::GetTypeLayout()
{
    static FTypeLayout Layout;
    static bool bInitialized = false;
    if (!bInitialized)
    {
        bInitialized = true;
        // 调用链式模板收集所有字段信息
        InternalLinkTime<__COUNTER__>::Initialize(Layout);
    }
    return Layout;
}

// 静态注册对象（程序启动时自动执行）
static FGlobalShaderType FMyShaderVSType(
    TEXT("FMyShaderVS"),                       // C++ 类名
    TEXT("/Engine/Private/MyShader.usf"),       // USF 文件
    TEXT("MainVS"),                             // 入口函数
    SF_Vertex,                                  // Shader 频率
    sizeof(FMyShaderVS),                        // 类大小
    FMyShaderVS::FPermutationDomain::PermutationCount,
    &FMyShaderVS::ShouldCompilePermutation,
    &FMyShaderVS::GetTypeLayout,
    // ...
);
```

`FGlobalShaderType` 对象在程序启动时（main 之前，通过 static 初始化）自动将自己注册到全局 Shader 类型注册表，引擎可以在 Cook 和运行时通过名字查找并编译对应的 Permutation。

---

## 11. 完整流程总结

```
[编写阶段]
  .usf 文件（HLSL 语法，带 #if 预处理指令）
      ↓ IMPLEMENT_GLOBAL_SHADER 注册
  FGlobalShader 子类（C++）
      ↓ 参数反射宏
  BEGIN/END_SHADER_PARAMETER_STRUCT

[编译阶段（Cook 时）]
  FShaderCompilerManager
      ├─ 枚举所有 Permutation
      ├─ 调用 ShouldCompilePermutation() 过滤
      ├─ mcpp 预处理 USF → 展开 #if/#define
      ├─ HLSL 编译器 (DXC / FXC)
      │     → D3D12: DXIL bytecode
      │     → OpenGL: 先编译 HLSL，后 hlslcc 转 GLSL
      └─ 输出二进制 + optional data → 存入 ShaderMap 缓存

[运行时加载]
  FShaderMapRef → 按 FeatureLevel + Permutation ID 查找缓存
      ↓
  RHICreateVertexShader(bytecode, hash)
      ├─ D3D12: FD3D12DynamicRHI → 存 D3D12_SHADER_BYTECODE
      └─ OpenGL: FOpenGLDynamicRHI → glCompileShader

[渲染时使用]
  TShaderMapRef<FMyShader> Shader(View.ShaderMap, Permutation)
      ↓
  SetShaderParameters(RHICmdList, Shader, ...)
      ↓ 根据 FTypeLayout 的反射信息自动绑定参数
  提交 DrawCall / Dispatch
```

---

## 12. 关键类继承树（ASCII）

### RHI 层

```
FRHIResource
└── FRHIShader
    │   成员: EShaderFrequency Frequency
    │         FString ShaderName
    │         FSHAHash Hash
    │
    ├── FRHIGraphicsShader
    │   ├── FRHIVertexShader
    │   │   └── FD3D12VertexShader  (D3D12)
    │   │   └── FOpenGLVertexShader (OpenGL, GLuint Resource)
    │   ├── FRHIPixelShader
    │   │   └── FD3D12PixelShader
    │   │   └── FOpenGLPixelShader
    │   ├── FRHIMeshShader          (UE5 新增)
    │   └── FRHIGeometryShader
    │
    └── FRHIComputeShader
        └── FD3D12ComputeShader
        └── FOpenGLComputeShader
```

### 逻辑层

```
FShader
│  成员: int32 PermutationId
│        FTypeLayout（反射元数据）
│
├── FGlobalShader
│   │  不依赖材质，用于全局 Pass
│   └── （用户自定义，如 FMyPostProcessVS/PS）
│
├── FMaterialShader
│   │  依赖材质参数
│   └── FMeshMaterialShader
│       │  依赖材质 + VertexFactory
│       └── （大多数渲染用 Shader，如 TBasePassVS/PS）
│
└── （其他）
```

### 辅助类

```
FShaderCodeReader
│  解析 [bytecode][optional_data][int32 size] 格式

FTypeLayout
│  收集 LAYOUT_FIELD 声明的成员反射信息
│  成员: TArray<FTypeLayoutField> Fields

FGlobalShaderType : FShaderType
│  注册信息: USF路径、入口函数、Frequency
│  链接: ShouldCompilePermutation, GetTypeLayout
│  注册表: TLinkedList<FShaderType*>（全局单链表）
```

---

> 本笔记基于 UE5.1 源码，部分类名、宏名在 UE5.2+ 可能有调整，建议结合 IDE 实际搜索验证。
> 后续集数将继续分析：Shader 如何在 RenderPass 中被绑定和调用、Uniform Buffer 的传参机制。
