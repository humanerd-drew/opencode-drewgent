# Ponytail Original Examples (from DietrichGebert/ponytail)

## Date Picker

**Task:** "Add a date picker to this form."

### Without Ponytail
```bash
npm install flatpickr
```
```jsx
import flatpickr from "flatpickr";
import "flatpickr/dist/flatpickr.min.css";
import { useEffect, useRef } from "react";

export default function DatePicker({ value, onChange, minDate, maxDate }) {
  const inputRef = useRef(null);
  const instanceRef = useRef(null);

  useEffect(() => {
    instanceRef.current = flatpickr(inputRef.current, {
      defaultDate: value,
      minDate,
      maxDate,
      dateFormat: "Y-m-d",
      onChange: ([date]) => onChange(date),
    });
    return () => instanceRef.current?.destroy();
  }, []);

  useEffect(() => {
    instanceRef.current?.setDate(value, false);
  }, [value]);

  return <input ref={inputRef} className="date-picker" />;
}
```
1 dependency + 1 wrapper + 2 useEffects + CSS import + cleanup.

### With Ponytail
```html
<!-- ponytail: browser has one -->
<input type="date">
```
**1 dep + 30 lines → 0 deps + 1 line.** Native, accessible, localized, keyboard-navigable.

## Email Validation

### Without Ponytail
```js
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
function validate(email) {
  return EMAIL_REGEX.test(email);
}
```

### With Ponytail
```html
<!-- ponytail: browser validates -->
<input type="email">
```
Or in Node.js: `import { isEmail } from 'node:util'` (Node 22+).

## Caching

### Without Ponytail
```js
const cache = new Map();
function get(key) {
  if (cache.has(key)) return cache.get(key);
  const value = expensive(key);
  cache.set(key, value);
  return value;
}
```

### With Ponytail
```js
// ponytail: lru-cache on npm — install only if you need LRU eviction
// ponytail: if TTL is enough, stdlib Map + setInterval sweep
// ponytail: if single entry, a module-level variable
import { LRUCache } from 'lru-cache';
const cache = new LRUCache({ max: 100 });
```

## Sorting

### Without Ponytail
```js
const sorted = [...items].sort((a, b) => a.name.localeCompare(b.name));
```

### With Ponytail
```js
// ponytail: Intl.Collator exists
const collator = new Intl.Collator();
const sorted = [...items].sort(collator.compare);
```
Locale-aware, configurable sensitivity, reuses comparison object.
