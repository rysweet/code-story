#!/bin/bash
# Run comprehensive OpenAI client tests

# Set up Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from template."
    cp .env-template .env
    echo "Please edit .env to add your API credentials."
    exit 1
fi

# Print test options
echo "OpenAI Client Testing Options:"
echo "1. Run basic test (test_azure_openai.py)"
echo "2. Run comprehensive test (test_openai_client_comprehensive.py)"
echo "3. Run integration tests (pytest)"
echo "4. Run all tests"
echo ""
read -p "Select option (1-4): " option

case $option in
    1)
        echo "Running basic OpenAI client test..."
        python scripts/test_azure_openai.py
        ;;
    2)
        echo "Running comprehensive OpenAI client test..."
        python scripts/test_openai_client_comprehensive.py
        ;;
    3)
        echo "Running pytest integration tests..."
        python -m pytest tests/integration/test_llm/ -v --run-openai
        ;;
    4)
        echo "Running all tests..."
        python scripts/test_azure_openai.py
        echo ""
        python scripts/test_openai_client_comprehensive.py
        echo ""
        python -m pytest tests/integration/test_llm/ -v --run-openai
        ;;
    *)
        echo "Invalid option."
        exit 1
        ;;
esac