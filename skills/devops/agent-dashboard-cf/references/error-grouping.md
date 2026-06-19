# Error Grouping Strategy

Problem: Recurring errors (e.g. HTTP 400 every few minutes) flood the dashboard with identical entries.

## Solution

Group by error message prefix (first 60 chars), show count + latest sample.

### Before (v1-v4)
Flat list, dedup by first 60 chars. Same error still appears as 1 entry but next pusher run may pick different recent timestamp. User sees "same error again."

### After (v5)
```python
from collections import Counter
error_types = Counter()
for line in log:
    key = msg[:60]
    error_types[key] += 1
for key, count in error_types.most_common(5):
    result.append({"message": msg, "count": count, ...})
```
Top 5 error types, each with occurrence count. New types naturally displace old ones.

## Health Warning Double-Count
compute_health_status() counts cron errors + recent_errors + disk independently. A single root cause (a failing cron job) can appear as both a cron error AND an error log entry, causing the warning count to exceed the actual number of distinct issues.
