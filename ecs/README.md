# ECS Frameworks - Component Storage & CRUD Comparison

This research compares **six popular/open-source ECS (Entity Component System) implementations** focusing on how they store components in memory and how they handle component CRUD operations.

## Research Scope

For each framework, we examined:
1.  **Memory storage architecture** - How are components arranged in memory? SoA vs AoS, sparse vs dense, chunks vs pages?
2.  **Component CRUD flow** - Step-by-step process for Create, Read, Update, Delete operations
3.  **Memory layout diagrams** - Any existing diagrams from documentation or created from code analysis

## Frameworks Researched

| Framework | Architecture | Memory Model | Main Approach | Report |
|-----------|--------------|--------------|---------------|--------|
| [decs (vblanco20-1/decs)](https://github.com/vblanco20-1/decs) | Archetype-based | 16KB fixed chunks, Pure SoA | Chunked archetype SoA | [codemap/decs-codemap.md](codemap/decs-codemap.md) |
| [HybridECS (StellarWarp/HybridECS)](https://github.com/StellarWarp/HybridECS) | Hybrid Archetype/Sparse | Auto-switching sparse + chunk SoA | Two-level hybrid: component groups + auto sparse↔chunk | [codemap/hybridecs-codemap.md](codemap/hybridecs-codemap.md) |
| [ENTT (skypjack/entt)](https://github.com/skypjack/entt) | Sparse Set | Paged sparse-dense per component | Each component in own sparse-dense pool (SoA) | [codemap/entt-codemap.md](codemap/entt-codemap.md) |
| [flecs (SanderMertens/flecs)](https://github.com/SanderMertens/flecs) | Archetype-based (Table) | SoA tables + sparse storage for special components | Table-based archetypes with SoA columns | [codemap/flecs-codemap.md](codemap/flecs-codemap.md) |
| [SakuraEngine Sugoi ECS](https://github.com/SakuraEngine/SakuraEngine) | Archetype-based | 3-size chunked SoA | Fixed-size pool chunks, SoA with change tracking | [codemap/sakuraengine-codemap.md](codemap/sakuraengine-codemap.md) |
| [bevy (bevyengine/bevy)](https://github.com/bevyengine/bevy) | Hybrid Archetype/Sparse | Tables (SoA) + optional sparse sets | Archetype tables with per-component storage type selection | [codemap/bevy-codemap.md](codemap/bevy-codemap.md) |

## Summary Table - Key Characteristics

| Framework | Storage Approach | Chunking | Sparse/Dense | Is SoA? | Adding/Removing requires move? |
|-----------|------------------|----------|--------------|---------|---------------------------------|
| **decs** | Archetype | 16KB fixed chunks | Bitmask for free slots | Yes (full SoA) | Yes (move to new archetype chunk) |
| **HybridECS** | Hybrid Archetype/Sparse | 2KB fixed chunks (when in chunk mode) | Sparse for small archetypes, dense chunk for large | Yes (when chunked) | Yes |
| **ENTT** | Per-component sparse set | Paged (4096/1024) | Sparse-dense per component | Yes (each component separate) | No (no archetype move) |
| **flecs** | Archetype (tables) | Dynamic growth | Dense SoA in tables, sparse for relationships | Yes (columns) | Yes (move to new table) |
| **Sakura Sugoi** | Archetype | 1KB/64KB/512KB pools | Sparse entity lookup, dense chunks | Yes | Yes |
| **bevy** | Hybrid Archetype/Sparse | Dynamic table growth | Table dense SoA + optional sparse sets | Yes (default table storage) | Yes (for table components) |

## Key Architectural Differences

Two main approaches:

### 1. **Archetype-based (All grouped by component signature)**
- **How it works**: Entities with the exact same set of components are grouped together in contiguous memory (tables/chunks)
- **Pros**: Excellent cache locality when iterating over systems with multiple components
- **Cons**: Adding/removing components requires moving the entire entity to a different archetype (O(C) cost where C = number of components)
- **Implementations**: decs, HybridECS, flecs, SakuraEngine, bevy

### 2. **Sparse Set per Component (Each component stored independently)**
- **How it works**: Each component type gets its own sparse-dense storage pool. Only stores the component for entities that have it.
- **Pros**: O(1) add/remove, no moving when components change
- **Cons**: Worse cache locality when iterating over multiple components because entities aren't grouped together
- **Implementations**: ENTT (pure sparse-set), bevy (optional sparse for specific components)

### 3. **Hybrid Approaches**
- HybridECS: Auto-switches between sparse storage for small archetypes and chunked SoA for large archetypes
- bevy: Default to table (archetype) SoA, but allows per-component opt-in to sparse set storage for components that are frequently added/removed

## Directory Structure

```
~/my-research/ecs/
├── README.md                 # This file - overview and comparison
├── findings.md               # Interesting findings and observations
├── codemap/                  # Detailed codemap for each framework
│   ├── decs-codemap.md
│   ├── hybridecs-codemap.md
│   ├── entt-codemap.md
│   ├── flecs-codemap.md
│   ├── sakuraengine-codemap.md
│   └── bevy-codemap.md
└── docs/                     # Additional documentation
```

## Reading the Reports

Each codemap file follows the same structure:
1.  Project overview and official links
2.  Memory storage architecture with diagrams
3.  Complete step-by-step CRUD flow
4.  Memory layout diagrams (from docs or created)
5.  Key source files with line numbers
6.  Core code snippets showing key algorithms
7.  Summary of key design choices
