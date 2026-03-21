# Render Graph 技术调研：Adria vs SakuraEngine

本研究深入分析了两个现代实时渲染引擎中 **Render Graph** 的实现，重点关注：
- Render Graph 编译过程
- Barrier 处理策略
- 同步点管理
- Async Compute 异步计算实现
- RHI (Render Hardware Interface) 抽象设计
- 场景管理
- 材质系统
- 后处理系统

## 项目概述

| 项目 | 图形API | 实现复杂度 | 主要特点 |
|------|---------|------------|----------|
| [Adria](https://github.com/mateeeeeee/Adria) | DirectX 12 | 中等 | 简洁清晰的单线程 Render Graph 设计，代码易于理解 |
| [SakuraEngine](https://github.com/SakuraEngine/SakuraEngine) | D3D12/Metal/Vulkan | 高级 | 工业化设计，支持多队列异步计算，包含SSIS优化等先进技术 |

## 详细文档

- [Adria Render Graph & 渲染系统分析](./adria-analysis.md)
- [SakuraEngine Render Graph & 渲染系统分析](./sakura-analysis.md)

## 快速对比总结

| 特性 | Adria | SakuraEngine |
|------|-------|--------------|
| **编译流程** | 拓扑排序 -> 依赖级别构建 -> Pass 剔除 -> 资源生命周期计算 | 依赖分析 -> 队列分配 -> SSIS 同步优化 -> 内存别名 -> 屏障生成 -> 执行排序 |
| **Barrier 处理** | 按依赖级别批处理，每个级别前批量插入屏障 | 基于Subresource状态跟踪，支持分裂屏障优化，成本估算 |
| **同步点管理** | 简单的fence信号/等待，基于ID匹配 | SSIS (Static Synchronization Information) 优化，减少冗余同步 |
| **Async Compute** | 基础支持，需要用户标记AsyncCompute pass，简单跨队列同步 | 多异步计算队列支持，自动Pass分类，高级同步优化 |
| **RHI 抽象** | 轻量级抽象，基于D3D12概念封装 | 完整跨平台抽象，统一API支持多后端 |
| **场景管理** | 基于EnTT ECS，简单GPU驱动绘制 | 基于Actor组件系统，支持多样场景组织 |
| **材质系统** | 打包为结构化数据，GPU侧索引 | 独立材质资源系统，支持材质类型资产，预处理工具链 |
| **后处理** | 基于Render Graph的后处理pass链，支持多种效果 | 文档中未找到完整后处理实现框架 |
