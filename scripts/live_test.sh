#!/bin/bash
# Live Test Script for Marweis KB
# Usage: ADMIN_PW=xxx DEMO_PW=xxx TEST_PW=xxx bash live_test.sh
#   or source a .env.test file with the variables set.
set -e
BASE="${BASE:-http://127.0.0.1:8000}"
ADMIN_PW="${ADMIN_PW:?set ADMIN_PW env var}"
DEMO_PW="${DEMO_PW:-123456}"
TEST_PW="${TEST_PW:-test1234}"
PASS=0
FAIL=0

green() { echo -e "\033[32m$1\033[0m"; }
red() { echo -e "\033[31m$1\033[0m"; }
check() {
    local desc="$1" expected="$2" actual="$3"
    if echo "$actual" | grep -q "$expected"; then
        green "  PASS: $desc"
        PASS=$((PASS+1))
    else
        red "  FAIL: $desc (expected: $expected)"
        red "  Actual: $actual"
        FAIL=$((FAIL+1))
    fi
}

echo "=============================================="
echo " Marweis KB - Live Test Suite"
echo "=============================================="

# ─── 1. AUTH TESTS ───
echo ""
echo "─── 1. Authentication ───"

# 1.1 Login valid
echo "[1.1] Login with valid admin credentials"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":'"$ADMIN_PW"'}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
ADMIN_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
check "HTTP 200" "200" "$HTTP"
check "Returns token" "eyJ" "$ADMIN_TOKEN"

# 1.2 Login wrong password
echo "[1.2] Login with wrong password"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrongpassword123"}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
check "HTTP 401" "401" "$HTTP"
check "Error message" "用户名或密码错误" "$BODY"

# 1.3 Login non-existent user
echo "[1.3] Login with non-existent user"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"fakeuser99999","password":'"$TEST_PW"'}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
check "HTTP 401" "401" "$HTTP"
check "Does NOT reveal user existence" "用户名或密码错误" "$BODY"

# 1.4 Rate limiting
echo "[1.4] Rate limiting on rapid failed logins"
LAST_CODE=""
for i in $(seq 1 12); do
    LAST_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"username\":\"admin\",\"password\":\"wrong$i\"}")
done
check "Rate limit triggers (HTTP 429)" "429" "$LAST_CODE"

# 1.5 Self-registration
echo "[1.5] Self-registration"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser_tmp","display_name":"Test User","department":"器械注册部","password":'"$TEST_PW"'}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
check "HTTP 200" "200" "$HTTP"
check "Register success message" "注册成功" "$BODY"

# 1.6 Duplicate username
echo "[1.6] Duplicate username registration"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser_tmp","display_name":"Test User 2","department":"器械注册部","password":'"$TEST_PW"'}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
check "HTTP 400" "400" "$HTTP"
check "Username exists error" "用户名已存在" "$BODY"

# 1.7 Weak password
echo "[1.7] Weak password rejected"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"weakpw","display_name":"Weak","department":"器械注册部","password":"123"}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
check "HTTP 400" "400" "$HTTP"

# 1.8 Invalid department
echo "[1.8] Invalid department rejected"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"baddep","display_name":"Bad Dept","department":"黑客部","password":'"$TEST_PW"'}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
check "HTTP 400" "400" "$HTTP"
check "Invalid department message" "无效的部门" "$BODY"

# ─── 2. CATEGORY TESTS ───
echo ""
echo "─── 2. Categories ───"

echo "[2.1] List categories (authenticated)"
CATS=$(curl -s "$BASE/api/categories" -H "Authorization: Bearer $ADMIN_TOKEN")
CAT_COUNT=$(echo "$CATS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
check "Categories returned" "True" "$([ "$CAT_COUNT" -gt 0 ] && echo True || echo False)"
echo "  Category count: $CAT_COUNT"

echo "[2.2] List categories (guest/no auth)"
CATS_GUEST=$(curl -s "$BASE/api/categories")
CAT_COUNT_GUEST=$(echo "$CATS_GUEST" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
echo "  Guest visible categories: $CAT_COUNT_GUEST"
check "Guest gets fewer/same categories" "True" "$([ "$CAT_COUNT_GUEST" -le "$CAT_COUNT" ] && echo True || echo False)"

echo "[2.3] Create category requires super_admin"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/categories" \
  -H "Content-Type: application/json" \
  -d '{"name":"TEST_CATEGORY_DELETE_ME","sort_order":99}')
HTTP=$(echo "$RESP" | tail -1)
check "HTTP 403 (guest cant create)" "403" "$HTTP"

# ─── 3. DOCUMENT TESTS ───
echo ""
echo "─── 3. Documents ───"

echo "[3.1] List documents"
DOCS=$(curl -s "$BASE/api/documents?size=5" -H "Authorization: Bearer $ADMIN_TOKEN")
DOC_TOTAL=$(echo "$DOCS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
DOC_COUNT=$(echo "$DOCS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['items']))" 2>/dev/null)
check "Returns items" "True" "$([ "$DOC_COUNT" -gt 0 ] && echo True || echo False)"
echo "  Total docs: $DOC_TOTAL, items: $DOC_COUNT"

echo "[3.2] List documents - pagination"
DOCS_P2=$(curl -s "$BASE/api/documents?page=2&size=5" -H "Authorization: Bearer $ADMIN_TOKEN")
P2_ITEMS=$(echo "$DOCS_P2" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['items']))" 2>/dev/null)
check "Page 2 returns items" "True" "$([ "$P2_ITEMS" -gt 0 ] && echo True || echo False)"

echo "[3.3] Get first document detail"
FIRST_ID=$(echo "$DOCS" | python3 -c "import sys,json; print(json.load(sys.stdin)['items'][0]['id'])" 2>/dev/null)
DETAIL=$(curl -s "$BASE/api/documents/$FIRST_ID" -H "Authorization: Bearer $ADMIN_TOKEN")
DETAIL_TITLE=$(echo "$DETAIL" | python3 -c "import sys,json; print(json.load(sys.stdin)['title'])" 2>/dev/null)
check "Document detail returned" "True" "$([ -n "$DETAIL_TITLE" ] && echo True || echo False)"
echo "  Title: $DETAIL_TITLE"

echo "[3.4] Document not found (404)"
RESP=$(curl -s -w "\n%{http_code}" "$BASE/api/documents/00000000-0000-0000-0000-000000000000" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
HTTP=$(echo "$RESP" | tail -1)
check "HTTP 404 for invalid ID" "404" "$HTTP"

echo "[3.5] Get download URL"
RESP=$(curl -s -w "\n%{http_code}" "$BASE/api/documents/$FIRST_ID/download" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
HTTP=$(echo "$RESP" | tail -1)
check "Download returns redirect (307)" "307" "$HTTP"

echo "[3.6] Get preview token"
RESP=$(curl -s "$BASE/api/documents/$FIRST_ID/preview-token" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
PREVIEW_TOK=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
check "Preview token generated" "True" "$([ -n "$PREVIEW_TOK" ] && echo True || echo False)"

echo "[3.7] Preview with token"
if [ -n "$PREVIEW_TOK" ]; then
  RESP=$(curl -s -w "\n%{http_code}" "$BASE/api/documents/$FIRST_ID/preview?token=$PREVIEW_TOK")
  HTTP=$(echo "$RESP" | tail -1)
  check "Preview returns content (200 or 307)" "True" "$([ "$HTTP" = "200" -o "$HTTP" = "307" ] && echo True || echo False)"
fi

# ─── 4. SEARCH TESTS ───
echo ""
echo "─── 4. Search ───"

echo "[4.1] Search with keyword"
SEARCH=$(curl -s "$BASE/api/search?q=医疗器械" -H "Authorization: Bearer $ADMIN_TOKEN")
SEARCH_TOTAL=$(echo "$SEARCH" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
check "Search returns results" "True" "$([ "$SEARCH_TOTAL" -gt 0 ] && echo True || echo False)"
echo "  Results: $SEARCH_TOTAL"

echo "[4.2] Search with empty query"
SEARCH=$(curl -s "$BASE/api/search?q=" -H "Authorization: Bearer $ADMIN_TOKEN")
SEARCH_TOTAL=$(echo "$SEARCH" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
echo "  Empty query results: $SEARCH_TOTAL"

# ─── 5. PERSONAL TESTS ───
echo ""
echo "─── 5. Personal Center ───"

echo "[5.1] My uploads"
RESP=$(curl -s "$BASE/api/me/uploads" -H "Authorization: Bearer $ADMIN_TOKEN")
MY_COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
check "My uploads returns data" "True" "$([ "$MY_COUNT" -ge 0 ] && echo True || echo False)"
echo "  Upload count: $MY_COUNT"

echo "[5.2] Personal stats"
STATS=$(curl -s "$BASE/api/me/stats" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Stats returned" "total_uploads" "$STATS"
echo "  $STATS"

echo "[5.3] Add/remove favorite (requires auth)"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/me/favorites/$FIRST_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
HTTP=$(echo "$RESP" | tail -1)
check "Add favorite HTTP 200" "200" "$HTTP"

RESP=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE/api/me/favorites/$FIRST_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
HTTP=$(echo "$RESP" | tail -1)
check "Remove favorite HTTP 200" "200" "$HTTP"

echo "[5.4] Personal endpoints require auth"
RESP=$(curl -s -w "\n%{http_code}" "$BASE/api/me/uploads")
HTTP=$(echo "$RESP" | tail -1)
check "HTTP 403 (no auth)" "403" "$HTTP"

# ─── 6. ADMIN TESTS ───
echo ""
echo "─── 6. Admin (Security-Critical) ───"

echo "[6.1] List users (super_admin)"
USERS=$(curl -s "$BASE/api/admin/users" -H "Authorization: Bearer $ADMIN_TOKEN")
USER_COUNT=$(echo "$USERS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
check "User list returned" "True" "$([ "$USER_COUNT" -gt 0 ] && echo True || echo False)"
echo "  User count: $USER_COUNT"

echo "[6.2] Create a dept_admin user for testing"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/admin/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"username":"test_dept_admin","password":'"$TEST_PW"',"display_name":"Test Dept Admin","department":"器械注册部","role":"dept_admin"}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
check "Create dept_admin HTTP 200" "200" "$HTTP"
DEPT_ADMIN_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
echo "  dept_admin ID: $DEPT_ADMIN_ID"

# Login as dept_admin
echo "[6.3] Login as dept_admin"
RESP=$(curl -s -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"test_dept_admin","password":'"$TEST_PW"'}')
DEPT_TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
check "dept_admin login" "True" "$([ -n "$DEPT_TOKEN" ] && echo True || echo False)"

# ═══════════════════════════════════════════════
# CRITICAL SECURITY TEST C-1:
# dept_admin creates super_admin user
# ═══════════════════════════════════════════════
echo ""
echo ">>> C-1: dept_admin creates super_admin user <<<"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/admin/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEPT_TOKEN" \
  -d '{"username":"hacker_super","password":"hack1234","display_name":"Hacker","department":"器械注册部","role":"super_admin"}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')

if [ "$HTTP" = "200" ] || [ "$HTTP" = "201" ]; then
    HACKER_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    red "  VULNERABILITY CONFIRMED: dept_admin created super_admin!"
    red "  Response: HTTP $HTTP - User created with super_admin role"
    red "  Hacker user ID: $HACKER_ID"

    # Try to login as hacker
    echo "  Attempting login as newly created super_admin..."
    HACK_LOGIN=$(curl -s -X POST "$BASE/api/auth/login" \
      -H "Content-Type: application/json" \
      -d '{"username":"hacker_super","password":"hack1234"}')
    HACK_TOKEN=$(echo "$HACK_LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
    HACK_ROLE=$(echo "$HACK_LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['user']['role'])" 2>/dev/null)
    if [ "$HACK_ROLE" = "super_admin" ]; then
        red "  BREACHED: Successfully logged in as super_admin (role=$HACK_ROLE)"
        red "  Full system compromise confirmed!"
    fi
    FAIL=$((FAIL+3))
else
    green "  SECURITY OK: dept_admin cannot create super_admin (HTTP $HTTP)"
    check "Request rejected" "403\|400" "$HTTP"
fi

# ═══════════════════════════════════════════════
# CRITICAL SECURITY TEST C-2:
# dept_admin escalates existing user to super_admin
# ═══════════════════════════════════════════════
echo ""
echo ">>> C-2: dept_admin escalates user role to super_admin <<<"
# Create a normal employee first
RESP=$(curl -s -X POST "$BASE/api/admin/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"username":"victim_emp","password":"victim123","display_name":"Victim Employee","department":"器械注册部","role":"employee"}')
VICTIM_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
echo "  Victim employee ID: $VICTIM_ID"

# dept_admin tries to escalate victim to super_admin
RESP=$(curl -s -w "\n%{http_code}" -X PUT "$BASE/api/admin/users/$VICTIM_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEPT_TOKEN" \
  -d '{"role":"super_admin"}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')

if [ "$HTTP" = "200" ]; then
    red "  VULNERABILITY CONFIRMED: dept_admin escalated user to super_admin!"
    red "  Response: HTTP $HTTP"
    # Verify the escalation
    VERIFY=$(curl -s -X POST "$BASE/api/auth/login" \
      -H "Content-Type: application/json" \
      -d '{"username":"victim_emp","password":"victim123"}')
    VERIFY_ROLE=$(echo "$VERIFY" | python3 -c "import sys,json; print(json.load(sys.stdin)['user']['role'])" 2>/dev/null)
    if [ "$VERIFY_ROLE" = "super_admin" ]; then
        red "  CONFIRMED: Victim is now super_admin (role=$VERIFY_ROLE)"
    fi
    FAIL=$((FAIL+3))
else
    green "  SECURITY OK: dept_admin cannot escalate roles (HTTP $HTTP)"
    check "Escalation rejected" "403\|400" "$HTTP"
fi

# ═══════════════════════════════════════════════
# TEST M-5: dept_admin cross-department user management
# ═══════════════════════════════════════════════
echo ""
echo ">>> M-5: dept_admin creates user in another department <<<"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/admin/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEPT_TOKEN" \
  -d '{"username":"cross_dept_user","password":"cross1234","display_name":"Cross Dept","department":"临床评价部","role":"employee"}')
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
if [ "$HTTP" = "200" ]; then
    red "  ISSUE CONFIRMED: dept_admin created user in another department!"
    red "  Response: HTTP $HTTP"
    FAIL=$((FAIL+2))
else
    green "  OK: Cross-department creation rejected (HTTP $HTTP)"
fi

# ═══════════════════════════════════════════════
# TEST H-1: Document list with no visible categories
# ═══════════════════════════════════════════════
echo ""
echo ">>> H-1: Document list when user has no visible categories <<<"
echo "  (Testing with guest/non-admin user)"

# Unauthenticated access
GUEST_DOCS=$(curl -s "$BASE/api/documents?size=10")
GUEST_TOTAL=$(echo "$GUEST_DOCS" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
echo "  Guest total docs: $GUEST_TOTAL"

# Check if any returned docs have non-null category_id (which would indicate the bug)
GUEST_ITEMS=$(echo "$GUEST_DOCS" | python3 -c "
import sys,json
data = json.load(sys.stdin)
cats = set()
for item in data['items']:
    cats.add(item.get('category_id'))
print(f'Unique category_ids: {cats}')
print(f'Total items: {len(data[\"items\"])}')
" 2>/dev/null)
echo "  $GUEST_ITEMS"

# ─── 7. CLEANUP ───
echo ""
echo "─── 7. Cleanup test data ───"

echo "[7.1] Delete test users"
for UID in "$DEPT_ADMIN_ID" "$VICTIM_ID"; do
    if [ -n "$UID" ] && [ "$UID" != "null" ]; then
        curl -s -o /dev/null -X DELETE "$BASE/api/admin/users/$UID" \
          -H "Authorization: Bearer $ADMIN_TOKEN"
        echo "  Deleted user: $UID"
    fi
done

# Also try to delete hacker and cross_dept if they were created
HACKER_UID=$(curl -s "$BASE/api/admin/users?size=100" -H "Authorization: Bearer $ADMIN_TOKEN" | \
  python3 -c "import sys,json; data=json.load(sys.stdin); [print(i['id']) for i in data['items'] if i['username'] in ['hacker_super','cross_dept_user','testuser_tmp']]" 2>/dev/null)
for UID in $HACKER_UID; do
    if [ -n "$UID" ]; then
        curl -s -o /dev/null -X DELETE "$BASE/api/admin/users/$UID" \
          -H "Authorization: Bearer $ADMIN_TOKEN"
        echo "  Deleted test user: $UID"
    fi
done

# ─── RESULTS ───
echo ""
echo "=============================================="
echo " TEST RESULTS"
echo "=============================================="
green "  Passed: $PASS"
if [ "$FAIL" -gt 0 ]; then
    red "  Failed: $FAIL"
else
    green "  Failed: $FAIL"
fi
echo ""
if [ "$FAIL" -gt 0 ]; then
    red "SECURITY ISSUES FOUND! See details above."
else
    green "All tests passed."
fi
