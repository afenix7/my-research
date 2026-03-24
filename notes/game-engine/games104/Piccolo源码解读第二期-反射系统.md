# Piccolo 源码解读第二期：反射系统

> 来源：Games104 官方 Piccolo 引擎源码解读系列
> 代码版本：v0.0.9（在第一期基础上继续修改）
> 主讲：Piccolo 主要开发者

---

## 目录

1. [为什么需要反射系统](#为什么需要反射系统)
2. [反射系统整体数据流](#反射系统整体数据流)
3. [piccolo_parser 工作原理](#piccolo_parser-工作原理)
4. [生成代码的结构分析](#生成代码的结构分析)
5. [all_reflection.h 与运行时注册](#all_reflectionh-与运行时注册)
6. [反射信息的存储：几个关键 map](#反射信息的存储几个关键-map)
7. [OOP 封装：TypeMeta 与 FieldAccessor](#oop-封装typemeta-与-fieldaccessor)
8. [实战一：通过反射读写 Component 字段](#实战一通过反射读写-component-字段)
9. [实战二：为反射系统添加函数反射能力](#实战二为反射系统添加函数反射能力)
10. [关键术语表](#关键术语表)
11. [总结](#总结)

---

## 为什么需要反射系统

C++ 原生不支持运行时反射（不能在运行时查询一个类有哪些字段、字段类型是什么）。Piccolo 的反射系统主要用于：

- **序列化/反序列化**：将 JSON 资产文件自动转换为 C++ 对象实例（如将 `player.object.json` 中的数据填充到各个 Component）
- **编辑器 UI**：在编辑器中展示并修改对象属性
- **脚本系统交互**：Lua 等脚本语言需要通过反射访问 C++ 的 Component 字段和函数

---

## 反射系统整体数据流

```
[源码编译阶段]
piccolo_parser 源码
    ↓ 构建
piccolo_parser 可执行文件
    ↓
CMake 收集 piccolo_runtime 所有 .h 路径
    ↓ 生成
puzzle_header.h（内容：include 所有运行时头文件）
    ↓
piccolo_precompile 工程构建（先于 runtime 构建）
    ↓ 调用 piccolo_parser 解析
    libclang 获取所有类的 AST
        ↓ 根据标签筛选（REFLECTION_TYPE、META(Enable) 等）
    收集感兴趣的类和字段信息（类型名、变量名等）
        ↓ 使用 Mustache 模板渲染
    生成 C++ 代码 → source/generated/

[运行时编译阶段]
source/generated/ 中生成的代码
  + piccolo_runtime 其他源码
    ↓ 一起编译
piccolo_runtime（含反射能力）
```

---

## piccolo_parser 工作原理

### 入口：`main()` 函数

```
main()
  ↓ 处理命令行参数
  ↓ 调用 parse(params)

parse():
  实例化 Parser 对象
  ↓ 调用 parser.parse_header_files()

parse_header_files():
  用 libclang 处理 puzzle_header.h
  ↓ 调用 build_class_ast()

build_class_ast():
  遍历所有根节点
  ├── class_decl（类声明）
  └── struct_decl（结构体声明）
  ↓ 对每个声明构造 Class 对象
  ↓ 传递给 schema_module 进行代码生成
```

### `Class` 类的构造过程

遍历 class 节点下所有子节点，对以下两类做特殊处理：

| 子节点类型 | 处理方式 |
|------------|----------|
| `base_specifier`（基类声明） | 记录基类信息 |
| `field_declaration`（字段声明） | 构造 `Field` 对象 |

`Field` 类保存：字段是否可访问（`is_accessible`）、变量名、类型名等信息。

### 标签系统

通过在 C++ 源码中添加宏标签来标记"需要反射"的内容：

```cpp
REFLECTION_TYPE(MotorComponent)
CLASS(MotorComponent : public Component, WhiteListFields) {
    GENERATED_BODY()

    META(Enable)
    float m_jump_height;   // 标记了 META(Enable)，会参与反射

    float m_speed;         // 未标记，不会参与反射
};
```

| 宏/标签 | 作用 |
|---------|------|
| `REFLECTION_TYPE(ClassName)` | 标记这个类需要生成反射代码 |
| `CLASS(ClassName : Base, Attrs)` | 类声明 + 属性（如 `WhiteListFields`、`Fields`） |
| `GENERATED_BODY()` | 占位，供生成代码插入 |
| `META(Enable)` | 标记字段参与反射/序列化 |
| `WhiteListFields` | 只有 `META(Enable)` 的字段才反射 |
| `Fields` | 所有字段都反射（无需逐一标注） |

---

## 生成代码的结构分析

以 `MotorComponent` 为例，生成的文件（`source/generated/`）结构如下：

### 第一部分：`TypeWrapperOperator` 类

包含三类函数：

**1. 类级别函数（3 个）**

```cpp
// 取类名
static const char* get_class_name();

// 从 JSON 构造实例
static void* construct_from_json(const Json& json_data);

// 转换为 JSON
static Json write_to_json(void* instance);
```

**2. 基类相关函数（1 个）**

```cpp
// 取得基类的反射实例
static TypeMeta get_base_class_instance();
```

**3. 字段相关函数（每个 META(Enable) 字段生成 5 个）**

以字段 `motor_resource`（即 `m_motor_resource`，自动去掉 `m_` 前缀）为例：

```cpp
// 取字段类型名
static const char* get_motor_resource_type_name();

// 取字段变量名
static const char* get_motor_resource_field_name();

// setter
static void set_motor_resource(void* instance, void* value);

// getter
static void* get_motor_resource(void* instance);

// 是否为 std::vector 类型
static bool is_array_motor_resource();  // 对 std::vector 做特殊处理
```

### 第二部分：`TypeWrapperRegister_{ClassName}` 函数

```cpp
void TypeWrapperRegister_MotorComponent() {
    // 将字段的 5 个函数组成一个元组，注册到 field_map
    FieldFunctionTuple motor_resource_funcs = {
        get_motor_resource_type_name,
        get_motor_resource_field_name,
        set_motor_resource,
        get_motor_resource,
        is_array_motor_resource
    };
    TypeMetaRegister::register_to_field_map("MotorComponent", motor_resource_funcs);

    // 基类相关函数注册到 class_map
    TypeMetaRegister::register_to_class_map("MotorComponent", get_base_class_instance);
}
```

### 第三部分：`TypeWrappers::Register_{ClassName}()`

调用上述注册函数的包装，最终由 `all_reflection.h` 统一调用。

---

## all_reflection.h 与运行时注册

`source/generated/` 中有一个特殊文件 `all_reflection.h`：

```cpp
// all_reflection.h
#include "motor_component.reflection.gen.h"
#include "animation_component.reflection.gen.h"
// ... include 所有 .reflection.gen.h 文件

namespace Piccolo {
    void meta_register() {
        // 调用所有类的注册函数
        TypeWrappers::Register_MotorComponent();
        TypeWrappers::Register_AnimationComponent();
        // ...
    }
}
```

这个 `meta_register()` 函数在第一期中提到过，是 **`start_engine()` 里最先调用的函数**，从而在引擎启动时完成所有反射信息的注册。

---

## 反射信息的存储：几个关键 map

所有反射信息在运行时存储在以下几个 map 中：

| Map 名称 | 存储内容 |
|----------|----------|
| `field_map` | key: 类名，value: 该类所有字段的 `FieldFunctionTuple` 列表 |
| `class_map` | key: 类名，value: 基类相关的反射函数 |
| `method_map`（扩展后新增） | key: 类名，value: 该类所有方法的 `MethodFunctionTuple` 列表 |

---

## OOP 封装：TypeMeta 与 FieldAccessor

为了更面向对象地查询类型信息，Piccolo 封装了两个辅助类：

### `TypeMeta`

```cpp
class TypeMeta {
public:
    // 通过类名获取 TypeMeta
    static TypeMeta new_meta_from_name(const std::string& class_name);

    // 获取该类型上所有字段的 FieldAccessor 列表
    std::vector<FieldAccessor> get_fields() const;

    // 获取该类型上所有方法的 MethodAccessor 列表（扩展后）
    std::vector<MethodAccessor> get_methods() const;
};
```

### `FieldAccessor`

```cpp
class FieldAccessor {
public:
    // 取字段类型名
    const char* get_field_type_name() const;

    // 取字段变量名
    const char* get_field_name() const;

    // 通用 setter
    void set(void* instance, void* value) const;

    // 通用 getter
    void* get(void* instance) const;

    // 是否为 std::vector
    bool is_array() const;
};
```

这两个类的实现就是对 `field_map`、`class_map` 等几个 map 的查询封装。

---

## 实战一：通过反射读写 Component 字段

### 目标

让 LuaComponent 中的 Lua 脚本能够：
- 获取 `MotorComponent` 上的 `is_moving` 字段（bool）
- 修改 `MotorComponent.motor_resource` 的 `jump_height` 字段（float）
- 实现：静止时跳跃高度 = 5，移动时跳跃高度 = 10

### 步骤一：为 `is_moving` 添加 `META(Enable)`

```cpp
// motor_component.h
CLASS(MotorComponent : public Component, WhiteListFields) {
    META(Enable)
    bool m_is_moving { false };  // 新增 META(Enable) 标记

    META(Enable)
    MotorComponentResource m_motor_resource;
};
```

### 步骤二：在 LuaComponent 中实现 get/set 函数

```cpp
// 函数签名：接收 game_object_id 和 field_name（格式："ComponentType.field"）
float get(GObjectID go_id, const std::string& field_name);
void  set(GObjectID go_id, const std::string& field_name, float value);
```

实现逻辑（以 `get` 为例）：

```
get(go_id, "MotorComponent.is_moving"):
  1. 取得 game_object 上所有的 components
  2. 将 field_name 以 '.' 分割，取前半部分作为 component 名
  3. 在所有 component 中找到名字匹配的 component
  4. 通过 TypeMeta::new_meta_from_name(component_type_name) 取得 TypeMeta
  5. 遍历 type_meta.get_fields()，找到名字匹配的 FieldAccessor
  6. 调用 field_accessor.get(component_ptr) 返回值
```

### 步骤三：将 get/set 函数传递给 Lua 虚拟机

```cpp
// 在 post_load_resource() 中注册给 Lua
m_lua_state.set_function("set_float", [this](GObjectID id, const std::string& field, float val) {
    set(id, field, val);
});
m_lua_state.set_function("get_float", [this](GObjectID id, const std::string& field) -> float {
    return get(id, field);
});
```

### 步骤四：修改 Lua 脚本

```lua
-- 判断 is_moving 字段
local is_moving = get_float(go_id, "MotorComponent.is_moving")
-- 根据状态设置跳跃高度
if is_moving > 0 then
    set_float(go_id, "MotorComponent.motor_resource.jump_height", 10)
else
    set_float(go_id, "MotorComponent.motor_resource.jump_height", 5)
end
```

---

## 实战二：为反射系统添加函数反射能力

### 目标

让 Lua 脚本能通过反射调用 `MotorComponent` 上的 `get_off_stuck_dead()` 函数（解除卡死）。

### 现有反射系统的局限

原有反射系统**只能反射字段，不能反射函数**。需要扩展两个部分：
1. `piccolo_parser`：识别并收集函数信息
2. `piccolo_runtime`：存储和调用函数反射信息

---

### Part A：修改 piccolo_parser

#### 1. 新增 `Method` 类（仿照 `Field` 类）

```cpp
class Method {
public:
    Method(const clang::CXXMethodDecl* method_decl);

    bool is_accessible() const;  // 检查 whitelist_methods 标签
    std::string get_name() const;
    // ... 其他方法信息
};
```

在 `is_accessible()` 中，仿照 `Field` 检查 `fields`/`whitelist_fields` 的逻辑，增加对 `methods`/`whitelist_methods` 标签的检查。

#### 2. 在 `Class` 类中添加 `m_methods` 成员

```cpp
class Class {
    std::vector<Field>  m_fields;
    std::vector<Method> m_methods;  // 新增

    // 在构造函数中处理 CXXMethodDecl 节点
    // 对每个方法声明构造 Method 对象并加入 m_methods
};
```

#### 3. 修改 `should_compile()` 函数

```cpp
bool should_compile() const {
    // 原来：只有 fields 被标记才编译
    // 现在：fields 或 methods 有标记就编译
    return has_fields() || has_methods();
}
```

#### 4. 扩展代码生成模板

在 `generate_class_render_data()` 中，仿照 fields 的 Mustache 模板，为 methods 添加新模板：

每个被反射的函数生成 **2 个函数**（比字段的 5 个少）：

```
// 取方法名
static const char* get_{method_name}_method_name();

// 调用函数（invoke）
static void invoke_{method_name}(void* instance);
```

同样在 `TypeWrapperRegister` 中将这两个函数注册到 `method_map`：

```cpp
MethodFunctionTuple stuck_funcs = {
    get_get_off_stuck_dead_method_name,
    invoke_get_off_stuck_dead
};
TypeMetaRegister::register_to_method_map("MotorComponent", stuck_funcs);
```

---

### Part B：修改 piccolo_runtime

#### 1. 添加 `MethodFunctionTuple` 和 `method_map`

```cpp
// 方法的函数元组：(取方法名函数, invoke函数)
using MethodFunctionTuple = std::pair<
    std::function<const char*()>,            // get_method_name
    std::function<void(void*)>               // invoke
>;

// 在反射存储中添加 method_map
std::unordered_map<std::string, std::vector<MethodFunctionTuple>> method_map;
```

#### 2. 添加 `MethodAccessor` 类（仿照 `FieldAccessor`）

```cpp
class MethodAccessor {
public:
    const char* get_method_name() const;
    void invoke(void* instance) const;
};
```

#### 3. 在 `TypeMeta` 中添加 `get_methods_list()`

```cpp
std::vector<MethodAccessor> TypeMeta::get_methods() const {
    // 从 method_map 查询并返回 MethodAccessor 列表
}
```

---

### Part C：在 LuaComponent 中实现 `invoke` 函数

```cpp
void invoke(GObjectID go_id, const std::string& target_name) {
    // target_name 格式：
    //   - "MotorComponent.get_off_stuck_dead"：component 上的成员函数
    //   （如果含 '.' 且点前面是 component 名，点后面是方法名）

    if (target_name has no '.') {
        // 目标是某个 component 本身的成员函数
        找到对应 component
        TypeMeta meta = TypeMeta::new_meta_from_name(component_type);
        遍历 meta.get_methods() 找到目标 MethodAccessor
        method_accessor.invoke(component_ptr);
    } else {
        // 目标是 component 上某个字段的成员函数（需进一步处理）
    }
}
```

### 验证结果

运行后在命令行看到 `get_off_stuck_dead` 的 log 输出，说明通过反射成功调用了 Component 上的函数。

---

## 关键术语表

| 术语 | 说明 |
|------|------|
| `piccolo_parser` | 在编译期解析 C++ 源码、生成反射代码的工具 |
| `puzzle_header.h` | 自动生成的头文件，include 了所有 runtime 头文件，供 parser 解析 |
| `libclang` | LLVM 提供的 C/C++ 代码解析库，用于获取 AST |
| AST | Abstract Syntax Tree，抽象语法树 |
| Mustache | 无逻辑的模板引擎，用于根据数据渲染代码模板（大小写敏感） |
| `source/generated/` | piccolo_parser 生成的所有反射/序列化代码的存放目录 |
| `TypeWrapperOperator` | 生成代码中的操作类，包含类/字段/基类相关的反射函数 |
| `TypeWrapperRegister_{Name}` | 生成的注册函数，将反射信息注册到各个 map |
| `all_reflection.h` | 汇总所有反射注册调用的文件，包含 `meta_register()` 函数 |
| `meta_register()` | 引擎启动最先调用的函数，完成所有反射信息注册 |
| `field_map` | 存储所有类的字段反射信息的 map |
| `class_map` | 存储所有类的基类反射信息的 map |
| `method_map` | 存储所有类的方法反射信息的 map（扩展后添加） |
| `FieldFunctionTuple` | 字段反射的 5 个函数组成的元组（类型名/变量名/set/get/is_array） |
| `MethodFunctionTuple` | 方法反射的 2 个函数组成的元组（方法名/invoke） |
| `TypeMeta` | 面向对象地查询类型反射信息的封装类 |
| `FieldAccessor` | 字段反射的访问器，提供 get/set/is_array 等操作 |
| `MethodAccessor` | 方法反射的访问器，提供 invoke 操作（扩展后添加） |
| `META(Enable)` | 标记字段（或函数）参与反射/序列化的宏 |
| `WhiteListFields` | 只反射有 `META(Enable)` 标记的字段 |
| `WhiteListMethods` | 只反射有 `META(Enable)` 标记的方法（扩展后添加） |
| `Fields` | 所有字段都参与反射（无需逐一标注） |
| `post_load_resource()` | Component 反序列化后的初始化回调，适合做 Lua state 初始化 |

---

## 总结

Piccolo 的反射系统采用**编译期代码生成**的思路，整体分为三个阶段：

### 阶段一：信息收集（编译期）

`piccolo_parser` 在构建 runtime 之前运行，利用 libclang 解析所有 `.h` 文件的 AST，根据宏标签筛选需要反射的类和字段，收集元信息。

### 阶段二：代码生成（编译期）

用 Mustache 模板将收集到的信息渲染为 C++ 代码，生成到 `source/generated/` 目录中。生成的代码包含每个类的字段（及方法）的操作函数，以及注册函数。

### 阶段三：运行时使用（运行期）

引擎启动时调用 `meta_register()`，将所有反射信息注册到 `field_map`、`class_map`、`method_map` 等 map 中。之后通过 `TypeMeta` 和 `FieldAccessor`/`MethodAccessor` 以面向对象的方式查询和操作反射信息，支持序列化/反序列化、脚本交互等功能。

### 本期扩展实现路径总结

```
添加函数反射能力：
  piccolo_parser 端：
    1. 新增 Method 类（仿 Field）
    2. Class 中添加 m_methods，收集方法 AST 信息
    3. 修改 should_compile() 判断条件
    4. 在 generate_class_render_data() 中添加 methods 的 Mustache 模板

  piccolo_runtime 端：
    1. 新增 MethodFunctionTuple 和 method_map
    2. 新增 MethodAccessor 类（仿 FieldAccessor）
    3. TypeMeta 中添加 get_methods_list()

  使用端（LuaComponent）：
    1. 实现 invoke 函数，通过反射调用目标 component 上的方法
    2. 注册 invoke 给 Lua 虚拟机
```

**思考题**（来自视频末尾）：
- 目前函数反射只支持最简单的 `void()` 无参无返回值函数，如何扩展以支持任意签名的函数？（提示：可以考虑 `std::any`、模板特化、或函数包装器）
