# Piccolo 源码解读第一期：代码结构

> 来源：Games104 官方 Piccolo 引擎源码解读系列
> 代码版本：v0.0.9
> 主讲：Piccolo 主要开发者

---

## 目录

1. [前置知识与环境要求](#前置知识与环境要求)
2. [获取源码与版本管理](#获取源码与版本管理)
3. [根目录结构总览](#根目录结构总览)
4. [engine 文件夹详解](#engine-文件夹详解)
5. [source 文件夹详解](#source-文件夹详解)
6. [runtime 分层架构](#runtime-分层架构)
7. [代码规模统计](#代码规模统计)
8. [构建与运行流程](#构建与运行流程)
9. [引擎启动流程（入口分析）](#引擎启动流程入口分析)
10. [RuntimeGlobalContext：系统管理中心](#runtimeglobalcontext系统管理中心)
11. [每帧 Tick 流程](#每帧-tick-流程)
12. [实战：为引擎添加 Lua 脚本支持](#实战为引擎添加-lua-脚本支持)
13. [关键术语表](#关键术语表)
14. [总结](#总结)

---

## 前置知识与环境要求

本系列讲解假设读者满足以下条件：

1. 有 **C++ 语言基础**
2. 学过 **Games104** 或有游戏引擎相关知识背景
3. 有一台已配置好 **C++ 和 CMake 开发环境**的电脑

---

## 获取源码与版本管理

- **源码托管平台**：GitHub（Piccolo 开源仓库）
- **版本控制工具**：`git`
- **构建工具**：`CMake`
- **讲解使用版本**：`v0.0.9` tag

熟悉 git 的同学可以直接 `git checkout v0.0.9`；不熟悉的话可以在 GitHub 的 Release 页面找到对应版本，下载源码压缩包解压即可。

---

## 根目录结构总览

解压后的根目录内容可分为四类：

| 类别 | 内容 | 说明 |
|------|------|------|
| **配置文件** | 以 `.` 开头的文件和文件夹（如 `.github`、`.clangformat`） | 各平台或工具的配置文件，在某些操作系统上默认隐藏 |
| **构建脚本** | `CMakeLists.txt`、CMake 相关脚本 | 指定工程如何构建 |
| **平台批处理** | `build_linux.bat`、`build_macos.bat`、`build_windows.bat` | 一键构建脚本（封装了 CMake 生成+编译两步） |
| **项目说明** | `LICENSE`、`README.md`、`RELEASE_NOTES.md` | 项目授权、简介、更新日志 |

除上述四类外，最重要的只有一个 **`engine` 文件夹**，包含引擎所有核心内容。

---

## engine 文件夹详解

```
engine/
├── third_party/     # 第三方库（源码或二进制，直接内嵌仓库）
├── asset/           # 引擎启动时默认关卡所需资产
├── binary/          # 构建过程中生成（不纳入版本仓库，灰色显示）
│                    #   └── piccolo_parser（参与构建的代码生成工具）
├── config/          # 编辑器启动所需的配置文件
├── jolt_asset/      # Jolt Physics 物理库所需 Shader
├── shader/          # 引擎启动必需的 Shader 文件
├── source/          # ★ 引擎所有源代码（重点）
├── template/        # piccolo_parser 代码生成所用的 Mustache 模板文件
├── .gitignore       # 指明不加入版本仓库的文件（如 binary/ 文件夹）
└── CMakeLists.txt   # 顶层工程构建描述
```

### binary/ 文件夹特别说明

`binary/` 在构建过程中生成，**不纳入 git 版本仓库**（`.gitignore` 中指定），但其中存放了 `piccolo_parser`。这个工具会：

1. 解析引擎 C++ 源代码
2. 根据 `template/` 中的模板文件**生成功能性代码**（反射、序列化代码）

---

## source 文件夹详解

```
source/
├── generated/       # piccolo_parser 生成的功能性代码（反射/序列化）
├── editor/          # 编辑器所有源代码
├── meta_parser/     # piccolo_parser 本身的源代码
├── precompile/      # CMake 脚本 + 配置文件
│                    #   └── 确保构建前先调用 piccolo_parser 生成代码
├── runtime/         # ★★★ 引擎最核心的代码
└── test/            # 测试代码（目前基本为空，仅有一个 .java 文件）
```

### precompile/ 的作用

`precompile/` 中的 CMake 脚本和配置文件，使得每次构建引擎工程前都会先运行 `piccolo_parser`，解析源码并将生成的代码放入 `source/generated/`，再参与后续编译。

---

## runtime 分层架构

`runtime/` 下有 **4 个子文件夹**，直接对应 Games104 第三课讲到的**分层架构**：

```
runtime/
├── core/            # Core Layer      —— 基础核心层
├── function/        # Function Layer  —— 功能层（最大）
├── platform/        # Platform Layer  —— 平台抽象层
├── resource/        # Resource Layer  —— 资源层
├── engine.h         # ★ 引擎入口头文件
├── engine.cpp       # ★ 引擎入口实现
└── CMakeLists.txt   # runtime 工程构建描述
```

---

## 代码规模统计

| 模块 | 代码行数（有效行） |
|------|-------------------|
| `function/` | 25,728 行（最大） |
| `core/` | 4,674 行 |
| `resource/` | 866 行 |
| `platform/` | 81 行（最小） |
| `engine.cpp` + `engine.h` | 少量 |
| **合计** | **31,481 行** |

---

## 构建与运行流程

```bash
# Step 1: CMake 生成工程（以当前目录为根）
cmake -S . -B build

# Step 2: 编译构建
cmake --build build
```

也可以直接使用平台对应的一键批处理脚本（`build_windows.bat` 等），它封装了上述两步操作。

---

## 引擎启动流程（入口分析）

### 入口类：`PiccoloEngine`

文件位于 `engine/source/runtime/engine.h`，整个文件只有 `PiccoloEngine` 一个类，对外暴露以下关键 public 函数：

```cpp
class PiccoloEngine {
public:
    void start_engine(const std::string& config_file_path);
    void shutdown_engine();
    void run();
    void tick_one_frame(float delta_time);

    // initialize() 和 clear() 为空的占位函数
};
```

### `start_engine()`

1. 注册所有类型的元信息（调用 `meta_register()`）
2. 调用 `g_runtime_global_context.start_systems(config_file_path)`

### `shutdown_engine()`

与 `start_engine()` 相反：先打印 log，再逐个关闭 system，最后取消注册类型元信息。

### `run()`

主循环，每帧检查窗口是否要关闭，若不关闭则调用 `tick_one_frame(delta_time)`。

### `tick_one_frame()`

逻辑与渲染分离架构的核心，执行顺序如下：

```
tick_one_frame():
  1. tick logic（逻辑 tick）
  2. 计算 FPS
  3. swap logic/render data（交换逻辑和渲染数据）
  4. tick render（渲染 tick）
  5. 其他非逻辑/渲染的更新（如物理 debug renderer、窗口标题）
```

---

## RuntimeGlobalContext：系统管理中心

全局变量 `g_runtime_global_context`（`G_` 开头表示全局变量）是 `RuntimeGlobalContext` 类型。

```cpp
// 伪代码示意
class RuntimeGlobalContext {
public:
    WindowSystem*       m_window_system;
    RenderSystem*       m_render_system;
    InputSystem*        m_input_system;
    PhysicsManager*     m_physics_manager;
    ParticleManager*    m_particle_manager;
    // ... 更多 system 和 manager ...

    void start_systems(const std::string& config_file_path);
    void shutdown_systems();
};
```

### System vs Manager 的区别

| 类型 | 定位 | 典型例子 |
|------|------|----------|
| **System** | 物理上的支持系统 | 窗口、输入、渲染 |
| **Manager** | 引擎逻辑上的管理系统 | 物理系统、粒子系统 |

> 如果未来需要添加新的系统，直接在 `RuntimeGlobalContext` 中添加成员即可统一管理。

---

## 每帧 Tick 流程

### 逻辑 Tick

```
logic tick:
  1. tick world
  2. tick input（用户输入）
```

### World 的 Tick

```
World.tick():
  - 若 world 未加载，从 JSON 资产路径加载（默认: hello_world.json）
  - 找到 active level
  - level.tick(active_level)

Level.tick():
  - 遍历所有 GObjects（Game Objects）
  - 遍历 active_character
  - tick physics_scene
  ↓
  GObject.tick():
    - 遍历身上挂载的所有 Component，逐一 tick
```

### Game Object 与 Component 的关系

```
World
  └── Level（可有多个，但同时只有一个 active）
        └── GObject（Game Object，无自身功能）
              └── Component（真正实现功能）
                    ├── TransformComponent
                    ├── AnimationComponent
                    ├── MotorComponent
                    └── ...（可自定义扩展）
```

> **核心设计**：`GObject` 本身没有任何功能，所有功能由其上挂载的不同 `Component` 实现。

---

## 实战：为引擎添加 Lua 脚本支持

本期通过给引擎添加 `LuaComponent` 来演示如何扩展 Piccolo。

### 步骤一：添加第三方库

将以下两个库解压到 `engine/third_party/`：
- **lua**（无 CMakeLists.txt，需手动编写）
- **sol2**（有 CMakeLists.txt，直接 `add_subdirectory` 引用）

在 `engine/third_party/CMakeLists.txt` 中添加：

```cmake
add_subdirectory(sol2)
add_subdirectory(lua)   # lua 需要自己仿照其他库编写 CMakeLists.txt
```

### 步骤二：链接到 piccolo_runtime

在 `source/runtime/CMakeLists.txt` 中找到 `target_link_libraries`：

```cmake
target_link_libraries(PiccoloRuntime
    ...
    lua_static
    sol2
)
```

### 步骤三：创建 LuaComponent

文件路径：`source/runtime/function/framework/component/lua/lua_component.h/.cpp`

仿照 `AnimationComponent` 的结构：

```cpp
// lua_component.h（最简形式）
REFLECTION_TYPE(LuaComponent)
CLASS(LuaComponent : public Component, WhiteListFields) {
    GENERATED_BODY()
public:
    void post_load_resource() override;
    void tick(float delta_time) override;

private:
    META(Enable)
    std::string m_lua_script;  // 要执行的 Lua 脚本内容

    sol::state m_lua_state;
};
```

关键注解说明：
- `REFLECTION_TYPE` / `CLASS` / `GENERATED_BODY()`：让 piccolo_parser 生成该类的反射和序列化代码
- `META(Enable)`：标记该字段参与序列化/反序列化
- `WhiteListFields`：只有标记了 `META(Enable)` 的字段才会参与反射

### 步骤四：将 LuaComponent 添加到小白人（player）

玩家数据文件：`engine/asset/objects/character/player.object.json`

仿照已有 component 的格式，在 components 数组中添加：

```json
{
    "type_name": "LuaComponent",
    "context": {
        "lua_script": "print('Hello World')"
    }
}
```

> `type_name`：告知反序列化工具要实例化的类型
> `context`：该类型需要反序列化的字段（字段名去掉 `m_` 前缀）

### 步骤五：初始化并执行 Lua

```cpp
// lua_component.cpp
void LuaComponent::post_load_resource() {
    m_lua_state.open_libraries(sol::lib::base);  // 添加 print 等基础函数
}

void LuaComponent::tick(float delta_time) {
    m_lua_state.script(m_lua_script);  // 每帧执行 lua 脚本
}
```

验证：切换到 Game Mode 后，命令行疯狂输出 `Hello World`，说明 LuaComponent 已成功挂载并参与每帧 tick。

---

## 关键术语表

| 术语 | 说明 |
|------|------|
| `piccolo_parser` | Piccolo 引擎的代码生成工具，解析 C++ 源码，根据 Mustache 模板生成反射和序列化代码 |
| `CMake` | 跨平台构建工具，用于控制代码编译流程 |
| `git` | 版本控制工具，管理不同人在不同时间的代码修改 |
| `RuntimeGlobalContext` | 运行时全局上下文，持有所有 System 和 Manager 的单例，通过全局变量 `g_runtime_global_context` 访问 |
| `System` | 物理层面的支持系统（窗口、输入、渲染） |
| `Manager` | 逻辑层面的管理系统（物理、粒子等） |
| `PiccoloEngine` | 引擎的顶层入口类，负责启动/关闭所有系统和每帧 tick |
| `tick_one_frame()` | 每帧执行的核心函数，体现逻辑与渲染分离架构 |
| `World` | 所有逻辑实体的载体，由多个 Level 组成 |
| `Level` | World 的组成单元，同时只有一个 active level |
| `GObject` | Game Object，引擎中的游戏对象，本身无功能 |
| `Component` | 挂载在 GObject 上的功能单元，实现具体游戏逻辑 |
| `META(Enable)` | 标记字段参与序列化/反序列化和反射 |
| `REFLECTION_TYPE` / `CLASS` / `GENERATED_BODY()` | 触发 piccolo_parser 为该类生成反射代码的宏 |
| `WhiteListFields` | 只有标注 `META(Enable)` 的字段才会参与反射 |
| `sol2` | C++ 的 Lua 绑定库，简化在 C++ 中执行 Lua 脚本 |
| `post_load_resource()` | Component 反序列化完成后会调用的初始化函数 |

---

## 总结

Piccolo 引擎的整体结构清晰地体现了 Games104 课程中讲授的分层架构：

1. **入口**：`engine.h` 中的 `PiccoloEngine` 类
2. **系统管理**：`RuntimeGlobalContext`（全局变量 `g_runtime_global_context`）统一管理所有 System 和 Manager
3. **主循环**：`run()` → `tick_one_frame()` → 逻辑 tick + 渲染 tick（逻辑与渲染分离）
4. **逻辑主体**：`World` → `Level` → `GObject` → `Component`（Entity-Component 架构）
5. **功能扩展**：通过添加新的 `Component` 类实现，同时借助 piccolo_parser 自动处理反射和序列化

扩展引擎的基本步骤：
- 添加第三方库到 `third_party/` 并修改 CMake
- 创建继承自 `Component` 的新类，使用反射宏标注
- 通过修改 JSON 资产文件将 Component 实例挂载到游戏对象

**思考题**（来自视频末尾）：
- `RuntimeGlobalContext` 使用全局变量的优缺点是什么？有无替代方案？
- GObject 上不同 Component 的执行顺序不确定，会带来什么问题？如何解决？
- 如何设计 Lua 脚本的生命周期和与引擎各系统的交互接口？
