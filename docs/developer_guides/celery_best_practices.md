# Celery Best Practices

## Avoiding Anti-Patterns in Celery Tasks

When working with Celery tasks in Code Story, it's important to avoid certain anti-patterns that can lead to issues in production. This guide outlines some key best practices and fixes for common issues.

### Don't Use `result.get()` Inside Tasks

One of the most critical anti-patterns to avoid is using `result.get()` inside a Celery task. This can lead to deadlocks, timeout issues, and reduced worker efficiency.

#### Why It's a Problem

When you call `.get()` inside a task:

1. It blocks the worker thread until the subtask completes
2. It can easily lead to deadlocks if tasks have cyclic dependencies
3. It defeats the purpose of asynchronous task execution
4. It can cause timeouts in CI/CD environments with resource constraints

Here's an example of the anti-pattern:

```python
@app.task
def task_a():
    result = task_b.delay()
    # DON'T DO THIS - blocks the worker thread
    data = result.get()  
    return process_data(data)
```

#### The Solution: Polling or Chain/Group

Instead of using `.get()`, you should use one of these patterns:

1. **Use polling with timeout:** Poll for task completion with a reasonable timeout

```python
@app.task
def task_a():
    subtask = task_b.delay()
    async_result = AsyncResult(subtask.id)
    
    # Poll with timeout
    timeout = 300  # 5 minutes
    start_time = time.time()
    result_data = None
    
    while time.time() - start_time < timeout:
        if async_result.ready():
            if async_result.successful():
                result_data = async_result.result
                break
            else:
                raise Exception(f"Subtask failed: {async_result.result}")
        time.sleep(1)
        
    if result_data is None:
        raise Exception(f"Subtask timed out after {timeout} seconds")
        
    return process_data(result_data)
```

2. **Use Celery's chain or group primitives:** For proper task chaining

```python
from celery import chain

# Chain tasks together
result = chain(
    task_a.s(),
    task_b.s(),
    task_c.s()
).delay()
```

### Other Best Practices

1. **Use reasonable timeouts:** Always include timeouts when waiting for results
2. **Handle errors gracefully:** Catch exceptions and provide meaningful error messages
3. **Use task routing:** Direct different types of tasks to appropriate queues
4. **Monitor task queues:** Set up monitoring to detect issues like queue backups
5. **Limit concurrency:** Configure worker concurrency based on available resources
6. **Use proper serialization:** Be careful with task parameters and return values

## Testing Celery Tasks

When writing tests for Celery tasks:

1. **Mock task execution in unit tests:** Don't rely on actual task execution in unit tests
2. **Use real services in integration tests:** For integration tests, use actual services with appropriate test configurations
3. **Start required services automatically:** Ensure services start automatically in test fixtures
4. **Add proper cleanup:** Always clean up resources after tests complete
5. **Use appropriate timeouts:** Set reasonable timeouts for waiting on task completion in tests

By following these best practices, you can avoid common issues with Celery task execution and ensure that your asynchronous code works reliably in production.