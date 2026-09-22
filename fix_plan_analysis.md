# Fix Plan Analysis: Location Handlers & State Initialization

## Overview
This document analyzes the current state of `location_stories.py`'s location handlers (`handle_location_6` and `handle_location_7`) and presents a unified fix plan to standardize them alongside other handlers.

---

## 1. Current Handler Signatures

### `handle_location_6_furry_cave` (Lines ~600-640)
```python
def handle_location_6_furry_cave(data, game, uid):
    """Обработать события на локации 'Мохнатая Пещера'."""
```

**Entry Pattern:**
1. `data == "furry_cave_start"` → Sets `game.story_state = "furry_exploring"`
2. `data == "furry_end"` → Clears state, resets nav stack
3. Sub-branches for `furry_warm`, `furry_sleep`, etc.

**Key Observation:** Handles both **entry** and **sub-menu** states within one function.

### `handle_location_7_sanctuary_peak` (Lines ~645-695)
```python
def handle_location_7_sanctuary_peak(data, game, uid):
    """Обработать события на локации 'Вершина Святилища'."""
```

**Entry Pattern:**
1. `data == "sanctuary_peak_start"` → Sets `game.story_state = "sanctuary_choice"`
2. `data == "sanctuary_resolve"` → Calls `resolve_ending()` to determine final variant
3. Sub-branches for `sanctuary_heroic`, `sanctuary_gentle`, `sanctuary_mysterious`

**Key Observation:** Handles **entry**, **ending selection**, and **3 ending variants**.

---

## 2. Comparison with Other Handlers

Let's compare with `handle_location_2` (the "reference handler"):

### `handle_location_2_river` (Example Reference)
```python
def handle_location_2_river(data, game, uid):
    if data == "river_ferocious":
        # Entry state
        game.story_state = "river_ferocious"
        ...
    elif data == "snake_flee":
        # Snake flee event
        ...
    elif data == "snake_stab":
        # Snake stab event
        ...
```

**Pattern:** Uses specific `data` prefixes to trigger different states.

---

## 3. Unified Fix Plan

### Goal: Normalize `handle_location_6` and `handle_location_7` to match the pattern of other handlers.

### Phase 1: Entry State Standardization

**For `handle_location_6`:**
1. Add explicit entry state when `data` matches the location ID.
2. Use `game.story_state = "furry_exploring"` as the "default exploring" state.

**For `handle_location_7`:**
1. Add `data == "sanctuary_peak_start"` to set `game.story_state = "sanctuary_exploring"`.
2. Keep `data == "sanctuary_resolve"` as the "ending trigger".

### Phase 2: Ending Consolidation (Location 7)

**Current State:**
- `sanctuary_heroic` → Heroic ending
- `sanctuary_gentle` → Gentle ending  
- `sanctuary_mysterious` → Mysterious ending

**Proposed Consolidation:**
1. Keep the 3 ending variants as-is.
2. Ensure all 3 variants set `game.story_state` to a unique ending ID.
3. After all 3 branches, add a `return text, kb` fallback.

### Phase 3: Cleanup & Edge Cases

**For both handlers:**
1. Ensure `text` and `kb` are initialized at function start.
2. Add a `return text, kb` at the very end (in case no `data` matches).
3. Verify all sub-branches return tuples consistently.

---

## 4. Implementation Checklist

- [ ] **`handle_location_6`:** Add entry state handling
- [ ] **`handle_location_7`:** Add entry state + consolidate endings
- [ ] **Both handlers:** Verify `text` and `kb` initialization
- [ ] **Both handlers:** Add final `return` clause
- [ ] **Test flow:** Trigger `location_enter_6` → verify `furry_exploring` state
- [ ] **Test flow:** Trigger `location_enter_7` → verify `sanctuary_exploring` state

---

## 5. Expected Flow After Fix

### Location 6 (Furry Cave) Flow:
```
1. Bot sends: "Мохнатая Пещера — убежище..."
2. Player clicks buttons → triggers sub-states
3. `furry_warm` → `game.story_state = "furry_warmed"`
4. `furry_end` → Clears state, resets nav stack
```

### Location 7 (Sanctuary Peak) Flow:
```
1. Bot sends: "Ты достиг вершины..."
2. `data == "sanctuary_resolve"` → Calls `resolve_ending()`
3. `sanctuary_heroic` → Heroic ending text
4. `sanctuary_gentle` → Gentle ending text
5. `sanctuary_mysterious` → Mysterious ending text
```

---

## 6. Next Steps

1. **Apply the fixes** to `location_stories.py`
2. **Run bot tests** with specific data triggers
3. **Verify state transitions** in the message log
4. **Document any quirks** discovered during testing

---

## 7. Key Insight

Both handlers follow the same **data-trigger pattern** as other location handlers:
- They accept `(data, game, uid)` consistently.
- They return `(text, kb)` tuples reliably.
- The difference is **semantic:** Location 6 handles "exploring → sub-states," while Location 7 handles "entry → ending resolution."

This makes them **ideal candidates for incremental refactoring** rather than a full rewrite.
