#!/bin/bash
#
# Unit tests for install.sh functions
# Run with: bash tests/unit/test_install_script.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for test output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test assertion helpers
assert_equals() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "$expected" == "$actual" ]]; then
        echo -e "${GREEN}PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}: $test_name"
        echo "  Expected: '$expected'"
        echo "  Actual:   '$actual'"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local test_name="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "$haystack" == *"$needle"* ]]; then
        echo -e "${GREEN}PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}: $test_name"
        echo "  Expected to contain: '$needle'"
        echo "  Actual: '$haystack'"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_function_exists() {
    local func_name="$1"
    local test_name="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    if type "$func_name" &> /dev/null; then
        echo -e "${GREEN}PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}: $test_name"
        echo "  Function '$func_name' not found"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Source install.sh but override main to prevent execution
# We do this by extracting functions via a subshell approach
INSTALL_SCRIPT="$REPO_ROOT/scripts/install.sh"

# Define the functions we need by extracting them
eval "$(awk '/^detect_distro\(\) \{/,/^}/' "$INSTALL_SCRIPT")"
eval "$(awk '/^check_pip\(\) \{/,/^}/' "$INSTALL_SCRIPT")"
eval "$(awk '/^show_pip_install_instructions\(\) \{/,/^}/' "$INSTALL_SCRIPT")"
eval "$(awk '/^detect_platform\(\) \{/,/^}/' "$INSTALL_SCRIPT")"
eval "$(awk '/^has_docker\(\) \{/,/^}/' "$INSTALL_SCRIPT")"

# Define color variables used by the functions
GREEN=''
YELLOW=''
RED=''
NC=''

# Stub warn function
warn() {
    echo "WARNING: $1"
}

# ============================================================================
# Tests
# ============================================================================

echo "=== install.sh Unit Tests ==="
echo ""

# Test: Functions exist
echo "--- Function Existence Tests ---"
assert_function_exists "detect_distro" "detect_distro function exists"
assert_function_exists "check_pip" "check_pip function exists"
assert_function_exists "show_pip_install_instructions" "show_pip_install_instructions function exists"

echo ""
echo "--- show_pip_install_instructions Tests ---"

test_pip_instructions_fedora() {
    local output=$(show_pip_install_instructions "fedora" 2>&1)
    assert_contains "$output" "dnf" "Fedora pip instructions mention dnf"
}
test_pip_instructions_fedora || true

test_pip_instructions_rhel() {
    local output=$(show_pip_install_instructions "rhel" 2>&1)
    assert_contains "$output" "dnf" "RHEL pip instructions mention dnf"
}
test_pip_instructions_rhel || true

test_pip_instructions_centos() {
    local output=$(show_pip_install_instructions "centos" 2>&1)
    assert_contains "$output" "dnf" "CentOS pip instructions mention dnf"
}
test_pip_instructions_centos || true

test_pip_instructions_ubuntu() {
    local output=$(show_pip_install_instructions "ubuntu" 2>&1)
    assert_contains "$output" "apt" "Ubuntu pip instructions mention apt"
}
test_pip_instructions_ubuntu || true

test_pip_instructions_debian() {
    local output=$(show_pip_install_instructions "debian" 2>&1)
    assert_contains "$output" "apt" "Debian pip instructions mention apt"
}
test_pip_instructions_debian || true

test_pip_instructions_arch() {
    local output=$(show_pip_install_instructions "arch" 2>&1)
    assert_contains "$output" "pacman" "Arch pip instructions mention pacman"
}
test_pip_instructions_arch || true

test_pip_instructions_manjaro() {
    local output=$(show_pip_install_instructions "manjaro" 2>&1)
    assert_contains "$output" "pacman" "Manjaro pip instructions mention pacman"
}
test_pip_instructions_manjaro || true

test_pip_instructions_opensuse() {
    local output=$(show_pip_install_instructions "opensuse" 2>&1)
    assert_contains "$output" "zypper" "openSUSE pip instructions mention zypper"
}
test_pip_instructions_opensuse || true

test_pip_instructions_alpine() {
    local output=$(show_pip_install_instructions "alpine" 2>&1)
    assert_contains "$output" "apk" "Alpine pip instructions mention apk"
}
test_pip_instructions_alpine || true

test_pip_instructions_unknown() {
    local output=$(show_pip_install_instructions "unknowndistro" 2>&1)
    assert_contains "$output" "package manager" "Unknown distro gets generic instructions"
}
test_pip_instructions_unknown || true

echo ""
echo "--- check_pip Tests ---"

test_check_pip_returns_status() {
    # This test checks that check_pip returns a valid status
    if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
        check_pip
        local result=$?
        assert_equals "0" "$result" "check_pip returns 0 when pip available"
    else
        # If pip not available, check_pip should return non-zero
        check_pip || true
        local result=$?
        assert_equals "1" "$result" "check_pip returns 1 when pip unavailable"
    fi
}
test_check_pip_returns_status || true

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "=== Test Summary ==="
echo "Total:  $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
if [[ $TESTS_FAILED -gt 0 ]]; then
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    exit 1
else
    echo "Failed: 0"
    exit 0
fi
