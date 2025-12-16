#!/bin/bash
# ScholarFlow Test Runner

echo "==================================="
echo "  ScholarFlow Test Suite"
echo "==================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing..."
    uv add pytest pytest-asyncio
fi

# Run tests
echo "🧪 Running tests..."
echo ""

# Run all tests
pytest tests/ -v

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "❌ Some tests failed!"
    exit 1
fi
