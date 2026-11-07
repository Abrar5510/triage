# CRITICAL: Remote Code Execution in sqlparse via unsafe expression evaluation (CVSS 9.8)

**Package:** sqlparse
**Affected versions:** 0.4.4 and earlier
**Severity:** Critical (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

## Executive summary

During a comprehensive security assessment of the sqlparse library, our team identified a
critical remote code execution vulnerability in the `sqlparse.utils.eval_expression()` helper.
This function is invoked internally by `sqlparse.format()` when the `strip_comments=True`
option is enabled, and passes user-controlled SQL comment content directly to Python's built-in
`eval()` without sanitization.

## Technical details

The vulnerable code path is as follows:

1. `sqlparse.format(sql, strip_comments=True)` instantiates `StripCommentsFilter`.
2. The filter calls `sqlparse.utils.eval_expression(token.value)` to normalise comment hints.
3. `eval_expression()` evaluates the hint with `eval()`, enabling arbitrary code execution.

## Proof of concept

```python
import sqlparse
payload = "SELECT 1 /*+ __import__('os').getcwd() */"
print(sqlparse.utils.eval_expression(payload))
```

## Impact

An unauthenticated remote attacker can execute arbitrary code on any server that formats
user-supplied SQL with sqlparse. Immediate patching is strongly recommended.

## Remediation

Upgrade to the latest version and avoid enabling `strip_comments` on untrusted input.
