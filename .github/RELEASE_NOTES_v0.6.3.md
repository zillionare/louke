# louke v0.6.3

**Patch release.** Switches the `lk models bind` candidate ranking from token-overlap to **Levenshtein edit distance**, which handles naming-style mismatches (e.g., `kimi-2.6` ↔ `kimi-k2.6`) much more accurately. Also fixes `extract_unresolved` to use the actual `resolve_model` chain (alias → opencode models → auth filter) instead of a heuristic.

## Highlights

- **Levenshtein-based ranking** for `lk models bind` candidates. `kimi-2.6` now ranks `ark/kimi-k2.6` and `opencode/kimi-k2.6` as the top 2 matches (similarity 0.857, distance 1) instead of getting buried in unrelated Claude/Big Pickle models.
- **`qwen-3.7-max`** now correctly ranks `opencode/qwen3.5-plus` and `opencode/qwen3.6-plus` at the top (similarity 0.5) instead of returning random models.
- **Accurate `extract_unresolved`**: now uses the full `resolve_model` chain. Was 8 (any name without `/`); now correctly identifies only the 4 (or however many) truly unresolvable abstracts.
- **No new dependencies**: Levenshtein distance is a 30-line stdlib-only implementation in `louke/_common.py`.

## What's in this release

### Edit distance matching

Algorithm (in `louke/_common.py`):

```python
def levenshtein(s1: str, s2: str) -> int:
    """Levenshtein distance: min single-character edits to transform s1 into s2.
    Iterative two-row DP, O(len(s1) * len(s2)) time."""
    ...

def similarity(s1: str, s2: str) -> float:
    """Normalized similarity in [0, 1] based on Levenshtein distance.
    similarity = 1 - distance / max(len(s1), len(s2))"""
    ...
```

Used in `_rank_candidates` (in `louke/models.py`):

```python
def _rank_candidates(abstract, models):
    abstract_norm = normalize(abstract)  # strip non-alphanumeric
    scored = []
    for m in models:
        m_norm = normalize(m.split('/')[-1])
        sim = similarity(abstract_norm, m_norm)
        if sim > 0:
            scored.append((m, sim))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [m for m, _ in scored[:12]]
```

### Ranking examples (v0.6.2 → v0.6.3)

| abstract | v0.6.2 top | v0.6.3 top (sim, dist) |
|---|---|---|
| `kimi-2.6` | mixed kimi + claude | `ark/kimi-k2.6` (0.857, 1) ✓ |
| `kimi-2.7-code` | `opencode/kimi-k2.7-code` | `opencode/kimi-k2.7-code` (0.909, 1) ✓ improved |
| `minimax-2.7` | `minimax-cn/MiniMax-M2.7` | `minimax-cn/MiniMax-M2.7` (0.900, 1) ✓ |
| `qwen-3.7-max` | random minimax | `opencode/qwen3.5-plus` (0.500, 5) ✓ qwen-related |
| `glm-5.2` | `ark/glm-5.2` | `ark/glm-5.2` (1.000, 0) ✓ perfect |
| `deepseek-v4-flash` | `ark/deepseek-v4-flash` | `ark/deepseek-v4-flash` (1.000, 0) ✓ perfect |

### `extract_unresolved` fix

Before (v0.6.2):
```python
return [n for n in used if n not in all_aliases and ('/' not in n)]
# Returns any abstract name without '/', even if it could be resolved via opencode models
```

After (v0.6.3):
```python
return [n for n in used if resolve_model(n) == n]
# Actually runs the full resolve chain (alias → strong/weak match → auth filter)
```

This means `lk models bind --all-unresolved` shows the correct number of truly unresolvable abstracts.

## Backward compatibility

- All v0.6.2 commands work identically
- The only user-visible change: `lk models bind kimi-2.6` shows better top candidates (more relevant kimi models ranked higher)
- `extract_unresolved` count may differ from v0.6.2 (smaller, more accurate)

## Install / upgrade

```bash
lk upgrade
lk --version  # lk 0.6.3
```

## License

MIT
