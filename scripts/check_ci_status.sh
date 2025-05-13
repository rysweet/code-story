#!/bin/bash
# Script to check the CI/CD workflow status for a GitHub repository

# Check if gh client is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed. Please install it first."
    exit 1
fi

# Check if logged in to GitHub
if ! gh auth status &> /dev/null; then
    echo "Error: Not logged in to GitHub. Please run 'gh auth login' first."
    exit 1
fi

# Get the current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Checking CI status for branch: $CURRENT_BRANCH"

# Get repository info from git config
REPO_URL=$(git config --get remote.origin.url)
REPO_NAME=$(basename -s .git "$REPO_URL")
REPO_OWNER=$(dirname "$REPO_URL" | xargs basename)

# Handle SSH vs HTTPS URLs
if [[ "$REPO_URL" == *":"* ]]; then
    # SSH format: git@github.com:owner/repo.git
    REPO_OWNER=$(echo "$REPO_URL" | cut -d ':' -f 2 | cut -d '/' -f 1)
    REPO_NAME=$(echo "$REPO_URL" | cut -d '/' -f 2 | sed 's/\.git$//')
fi

# Check the workflow runs
echo "Fetching latest workflow runs..."
gh run list --repo "$REPO_OWNER/$REPO_NAME" --branch "$CURRENT_BRANCH" --limit 5

# Get the latest run ID
LATEST_RUN_ID=$(gh run list --repo "$REPO_OWNER/$REPO_NAME" --branch "$CURRENT_BRANCH" --limit 1 --json databaseId --jq '.[0].databaseId')

if [ -z "$LATEST_RUN_ID" ]; then
    echo "No workflow runs found for branch $CURRENT_BRANCH"
    exit 0
fi

echo "Latest workflow run ID: $LATEST_RUN_ID"
echo "Details for latest workflow run:"
gh run view --repo "$REPO_OWNER/$REPO_NAME" "$LATEST_RUN_ID"

# Get the status of the latest run
STATUS=$(gh run view --repo "$REPO_OWNER/$REPO_NAME" "$LATEST_RUN_ID" --json status --jq '.status')
CONCLUSION=$(gh run view --repo "$REPO_OWNER/$REPO_NAME" "$LATEST_RUN_ID" --json conclusion --jq '.conclusion')

echo "Status: $STATUS"
echo "Conclusion: $CONCLUSION"

# Check if any job failed
FAILED_JOBS=$(gh run view --repo "$REPO_OWNER/$REPO_NAME" "$LATEST_RUN_ID" --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .name')

if [ -n "$FAILED_JOBS" ]; then
    echo "Failed jobs:"
    echo "$FAILED_JOBS"
    
    # Get logs for failed jobs
    for job in $FAILED_JOBS; do
        echo "=== Logs for failed job: $job ==="
        JOB_ID=$(gh run view --repo "$REPO_OWNER/$REPO_NAME" "$LATEST_RUN_ID" --json jobs --jq ".jobs[] | select(.name == \"$job\") | .databaseId")
        gh run view --repo "$REPO_OWNER/$REPO_NAME" --job "$JOB_ID" --log
    done
    
    exit 1
else
    if [ "$STATUS" == "completed" ] && [ "$CONCLUSION" == "success" ]; then
        echo "CI passed successfully! 🎉"
    else
        echo "CI is still running or had a different conclusion: $CONCLUSION"
    fi
fi

exit 0