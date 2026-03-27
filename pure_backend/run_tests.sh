#!/usr/bin/env bash
set -euo pipefail

echo "===================================="
echo "Running Unit Test Group"
echo "===================================="
pytest -q unit_tests

echo ""
echo "===================================="
echo "Running API Test Group"
echo "===================================="
pytest -q API_tests

echo ""
echo "===================================="
echo "Test Summary"
echo "===================================="
echo "All unit_tests and API_tests passed."
