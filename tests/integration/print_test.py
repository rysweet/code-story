import sys
print("PRINT_TEST: Hello from stdout")
print("PRINT_TEST: Hello from stderr", file=sys.stderr)
sys.exit(0)