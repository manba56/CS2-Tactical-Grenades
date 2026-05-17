#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# CS2 Tactics Suite — Build Report Generator
# ═══════════════════════════════════════════════════════════════
#
# Called by Jenkins post-build to auto-populate build report.
# Reads Allure results, coverage data, and git info to fill the
# build report template.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail
cd "$(dirname "$0")/.."

REPORT_DIR="docs/build_reports"
mkdir -p "$REPORT_DIR"

BUILD_NUMBER="${BUILD_NUMBER:-manual}"
BRANCH_NAME="${BRANCH_NAME:-$(git branch --show-current 2>/dev/null || echo 'unknown')}"
GIT_COMMIT="${GIT_COMMIT:-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')}"
BUILD_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
REPORT_FILE="$REPORT_DIR/构建报告_${BUILD_NUMBER}.md"

# Count test results from Allure results
PASSED=0; FAILED=0; SKIPPED=0; TOTAL=0
if [ -d "allure-results" ]; then
  for f in allure-results/*-result.json; do
    [ -f "$f" ] || continue
    TOTAL=$((TOTAL + 1))
    STATUS=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
    case "$STATUS" in
      passed) PASSED=$((PASSED + 1)) ;;
      failed|broken) FAILED=$((FAILED + 1)) ;;
      skipped) SKIPPED=$((SKIPPED + 1)) ;;
    esac
  done
fi

PASS_RATE=0
if [ $TOTAL -gt 0 ]; then
  PASS_RATE=$(python3 -c "print(round($PASSED / $TOTAL * 100, 1))")
fi

# Coverage from coverage.xml
COVERAGE="N/A"
if [ -f "coverage.xml" ]; then
  COVERAGE=$(python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
root = tree.getroot()
rate = root.attrib.get('line-rate', '0')
print(str(round(float(rate) * 100, 1)))
" 2>/dev/null || echo "N/A")
fi

VERDICT="PASS"
if [ $FAILED -gt 0 ]; then
  VERDICT="FAIL"
fi

cat > "$REPORT_FILE" << EOF
# CS2 Tactics Suite — 构建测试报告

## 构建信息

| 项目 | 值 |
|------|-----|
| 构建编号 | #${BUILD_NUMBER} |
| 分支 | ${BRANCH_NAME} |
| 提交 SHA | ${GIT_COMMIT} |
| 触发时间 | ${BUILD_TIME} |
| 测试级别 | ${TEST_LEVEL:-api} |

## 测试统计

| 指标 | 数值 |
|------|------|
| 总用例数 | ${TOTAL} |
| 通过 | ${PASSED} |
| 失败 | ${FAILED} |
| 跳过 | ${SKIPPED} |
| 通过率 | ${PASS_RATE}% |
| 代码覆盖率 | ${COVERAGE}% |

## 结论

**${VERDICT}**

| 报告链接 | URL |
|----------|-----|
| Allure Report | ${BUILD_URL:-}allure |
| Coverage Report | ${BUILD_URL:-}coverage-html |

---

*报告生成时间: ${BUILD_TIME}*
EOF

echo "[Report] Generated: $REPORT_FILE"
cat "$REPORT_FILE"
