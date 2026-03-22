# Research Findings

Interesting observations and unexpected patterns discovered during research.

## decs (vblanco20-1/decs)

- **Extremely simple**: Single header file (~56KB) with all code. Minimalist approach.
- Inspired by Unity ECS chunk approach - fixed 16KB chunks, SoA layout.
- Doesn't use sparse/dense - uses bitmask to track free slots in chunk.
- Adding/removing component always requires copying all components to new archetype chunk.
- No existing memory diagrams in docs, but the layout is straightforward.

## HybridECS (StellarWarp/HybridECS)

- **Most sophisticated hybrid approach** of all frameworks researched. Two levels of hybridization:
  1. Modular partitioning into **component groups** reduces archetype explosion
  2. **Auto conversion** between sparse storage (small archetypes) and chunk SoA (large archetypes) based on entity count
- **Tag components stored separately**: Always kept in sparse sets to avoid copying overhead when tags change
- **Excellent documentation with multiple memory diagrams** - all hosted on CDN in the README. The diagrams are the most complete of any of the frameworks researched.
- 2KB fixed chunk size - smaller than most other implementations.
- Automatic threshold calculation: `sparse_to_chunk_convert_limit = 2KB / total_component_size` - adapts automatically based on what fits.

## ENTT (skypjack/entt)

- **Pure sparse-set per-component approach**: Each component type gets its own sparse-dense paged pool.
- **No archetypes**: No grouping of entities by component composition. This means no moving when adding/removing components.
- **Paging for both sparse and dense**:
  - Sparse pages: 4096 entries per page
  - Component pages: 1024 components per page
- **Three configurable deletion policies**: `swap_and_pop` (default), `in_place` (tombstones with free list for pointer stability), `swap_only`
- **Pointer stability** with paging: References to components never invalidate when storage grows.
- **Empty component optimization**: Doesn't allocate any data for empty components - just tracks presence in sparse set.
- No memory diagrams in documentation.

## flecs (SanderMertens/flecs)

- **Archetype = Table**: Each unique combination is a table, each component is a column (SoA).
- **Supports sparse components**: Components can be marked as sparse/`DontFragment` and stored outside tables in sparse set storage. Used for relationships like `ChildOf`.
- **Fast O(1) lookup** for low component ids (< FLECS_HI_COMPONENT_ID) using direct `component_map` array.
- **Swap-with-last deletion**: O(1) deletion from tables - keeps array contiguous.
- **Has a component lifecycle diagram** in documentation showing the add/remove/set flow.
- **Lifecycle hooks order**: `OnAdd` after ctor, `OnRemove` before dtor - this is the correct approach that most frameworks agree on.

## SakuraEngine Sugoi ECS

- **Three fixed chunk sizes from memory pools**: 1KB (small), 64KB (default), 512KB (large). Chunk allocated from appropriate pool based on archetype size.
- **Thread-safe design**: Per-component per-chunk reader-writer locks for parallel access.
- **Change tracking**: Per-component timestamps allow systems to only process changed entities.
- **Cached random access optimization**: Caches last accessed chunk and pointer for faster repeated access.
- **Array components**: Built-in support for inline arrays with fallback to heap if capacity exceeded.
- **Shared components**: Allow meta-entities to share components across many entities without duplication.
- No existing diagrams, created from code analysis.

## bevy (bevyengine/bevy)

- **Hybrid approach**: Archetype-based table storage by default, but **per-component choice** between table and sparse set.
- **Multiple archetypes can share same table** if they differ only by sparse components - reduces fragmentation.
- **Change detection** built into every column - stores added/changed ticks per-component per-entity.
- **Optional caller location tracking** for debugging change detection.
- **Archetype has table_id + entity location**: Clear separation between table (storage) and archetype (logical grouping).
- Table storage = SoA with one column per component - very clean structure.
- Sparse set storage is still dense for the actual data - just mapping is sparse.
- No existing graphical diagrams, created text diagrams from code.

## Cross-Framework Comparisons

- **Archetype-based is dominant**: 5 out of 6 implementations use archetype-based approach. This reflects the current industry consensus that better cache locality for iteration is more important than fast add/remove in practice.
- **SoA is universal**: All implementations use SoA (Structure of Arrays) for dense storage. No modern ECS uses AoS anymore.
- **Chunking popular**: 4 out of 6 use chunked storage (fixed-size blocks). This helps with memory fragmentation and cache.
- **Hybrid is trending**: Newer implementations (HybridECS, bevy) are moving to hybrid approaches that give you the best of both worlds rather than pure approaches.
- **All implementations use swap-with-last for deletion** to keep storage contiguous when deleting from a dense block - this is now standard practice.
- **Change detection/tracking**: All newer implementations (Sakura, bevy, flecs) include built-in change tracking. ENTT and decs don't have built-in change tracking - it's left to the user.
- **Thread safety**: Modern implementations (Sakura, flecs, bevy) design for parallelism from the start.
