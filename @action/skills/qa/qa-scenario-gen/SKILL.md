---
title: qa-scenario-gen
description: Generate test scenarios and acceptance criteria from user requirements
trigger conditions:
  - Task involves multiple components
  - User mentions requirements, acceptance criteria
  - Starting new implementation project
space: outcome
type: document
tags: [qa, scenario, testing, requirements, contract-first]
links:
  - "[[@action/skills/qa/DESCRIPTION]]"
  - "[[@action/skills/SKILL-INDEX]]"
source: Hugh Kim's Loopy-Era Harness
---

# qa-scenario-gen — Test Scenario Generator

## Purpose

Analyzes user requirements and generates:
1. Structured acceptance criteria for `contract.json`
2. Test scenarios for micro-QA verification
3. Edge cases and boundary conditions

## How It Works

Parses user task description to extract:
- **Functional requirements** → acceptance criteria
- **Technical components** → test scenarios
- **Error conditions** → edge case tests
- **Performance needs** → non-functional tests

## Usage

```
skill: qa-scenario-gen
task_description: "Build a REST API that does X"
output_format: contract_json | scenarios | checklist
```

## Output Structure

### contract.json format
```json
{
  "task_id": "auto-generated",
  "acceptance_criteria": [
    {
      "id": "AC-001",
      "description": "API endpoint returns correct status code",
      "priority": "P0",
      "test_method": "automated",
      "verified": false
    }
  ]
}
```

### Test Scenarios
```
Scenario 1: Happy Path
  Given: valid input
  When: API called
  Then: returns 200 with expected data

Scenario 2: Invalid Input
  Given: malformed input
  When: API called
  Then: returns 400 with error message
```

## Hugh Kim's Approach

From Loopy-Era Harness:
- **CONTRACT-FIRST**: Write contract before implementation
- **PHASE 2.5**: 시나리오 확정 → 구현 → micro-QA → full-QA
- Scenarios become the micro-QA checklist

## Integration

- Output feeds into `QAEvidenceManager.create_contract()`
- Scenarios map to `micro-qa_*.json` files
- Edge cases become acceptance criteria with P0 priority

## Related
- [[@action/skills/SKILL-INDEX]]
- [[@action/skills/qa/DESCRIPTION]]
