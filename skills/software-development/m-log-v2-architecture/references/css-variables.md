# CSS Variables Design System (m-log-v2)

출처: `/Users/drew/m-log/DESIGN_REFERENCE.md`
원본 CSS: `/Users/drew/m-log/public/app/shared/theme/variables.css`

## 핵심 토큰

| Token | Dark 값 | 용도 |
|---|---|---|
| `--bg-deep-space` | `#080C12` | 최상위 배경 |
| `--bg-surface` | `#0F172A` | 카드/표면 배경 |
| `--bg-elevated` | `#1E293B` | 호버/강조 배경 |
| `--text-primary` | `#F8FAFC` | 주요 텍스트 |
| `--text-secondary` | `#94A3B8` | 보조 텍스트 |
| `--text-tertiary` | `#64748B` | 희미한 텍스트 |
| `--sys-primary` | `#7C4DFF` | 강조/포인트 색 |
| `--border-color` | `#1E293B` | 테두리 |

## 오행 색상 (변경 금지)

| Token | 값 | 오행 |
|---|---|---|
| `--wood` | `#00E676` | 木 |
| `--fire` | `#FF1744` | 火 |
| `--earth` | `#FFD600` | 土 |
| `--metal` | `#E0E0E0` | 金 |
| `--water` | `#2979FF` | 水 |

## CSS Import 순서

```html
<link rel="stylesheet" href="/app/shared/theme/variables.css">
<link rel="stylesheet" href="/app/css/index.css">
<link rel="stylesheet" href="/app/css/z-override.css">
```

`index.css`가 내부적으로 import하는 순서:
variables.css → base.css → layout.css → components/* → utility.css

## 절대 금지

- ❌ 하드코딩 색상 (#F8FAFC 등 직접 사용)
- ❌ `index.css` 직접 수정 (import만 추가)
- ❌ `variables.css` 외부의 `--variable` 정의
