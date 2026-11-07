# Uncaught RecursionError in sqlparse.parse on deeply nested brackets (DoS)

**Package:** sqlparse (PyPI)
**Affected versions:** < 0.5.0 (tested on 0.4.4)
**Fixed in:** 0.5.0
**Reference:** GHSA-2m57-hf25-phgg / CVE-2024-4340

## Summary

Passing a heavily nested list to `sqlparse.parse()` causes a `RecursionError` in the grouping
engine. Any service that parses untrusted SQL with sqlparse (query formatters, linters, SQL
dashboards) can be crashed with a single request.

## Steps to reproduce

```python
import sqlparse
sqlparse.parse('[' * 10000 + ']' * 10000)
```

On 0.4.4 this raises `RecursionError: maximum recursion depth exceeded`. In 0.5.0 the parser
enforces a grouping depth limit and raises a regular `SQLParseError` instead.

## Impact

Denial of service of any process that parses attacker-controlled SQL.
