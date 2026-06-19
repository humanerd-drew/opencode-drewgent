# Audit Pattern: Content-Based Gap Analysis

When the user asks "does V2 match V1", do NOT just compare file existence (39-second `diff -rq`). That's superficial and doesn't catch functional gaps.

## Correct methodology

### 1. Catalog by layer

| Layer | What to check |
|-------|---------------|
| Pages (views) | Does every original `View.js` have an equivalent MPA page? |
| Components | Are reusable components (WongukBoard, TimelineNavigator, etc.) inlined or shared? |
| Calculations | Logic modules like `desire-skills.js` — ported or replaced by API? |
| CSS | Variables, base, component styles — imported or reimplemented? |
| Shared utilities | Store, Auth, API — ported to Svelte lib/ or still Vanilla? |

### 2. Content-based comparison (read files, not just stat)

For each critical file pair (original View.js ↔ MPA .svelte):

```python
# Pseudo-code for real comparison
features = [
    ("WongukBoard", "pillar.*board", "wonguk"),
    ("Sinsal 12신살", "sinsal.*year", "sinsal"),
    ("Desire tab", "desire.*report", "desire"),
    ("희용신 분석", "yongsin", "yongsin"),
    ("격국", "gyeokguk", "gyeokguk"),
    # ...
]
for name, orig_pat, mpa_pat in features:
    orig = re.search(orig_pat, open(orig_file).read(), re.I)
    mpa = re.search(mpa_pat, open(mpa_file).read(), re.I)
    result = '✅' if (orig and mpa) else '❌'  # only tag real losses
```

### 3. Categorize results

- **✅ Both sides**: Feature ported correctly
- **❌ Original has, MPA missing**: Real gap — needs fix
- **⚠️ MPA-only**: Enhancement (new feature)
- **❓ Neither**: Not relevant to this page

### 4. Report only real gaps

Present findings as:
```
✅ 기능 유지 (8/10)
❌ 기록 저장 안 됨, desire-skills.js 미포팅
```

Do NOT dump the full raw table unless asked.

## Why this matters

The user caught a 39-second filesystem diff immediately ("이 답변을 신뢰할 수없음"). They expect real analysis, not directory listing. Content-based comparison takes 2-3 minutes but produces actionable results.
