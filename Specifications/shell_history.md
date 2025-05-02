# Shell Command History

- git remote add origin https://github.com/rysweet/code-story.git && git push -u origin main  # added remote and pushed initial commit
- git init && git branch -M main && git add . && git commit -m "chore: initial commit of specifications and status" && git remote add origin https://github.com/rysweet/code-story.git && git push -u origin main  # initialized git repo and committed specs
- git pull --rebase origin main && git push origin main  # synced local repo with remote
- git checkout -b p0-scaffolding  # created branch for P0 scaffolding
- poetry run ruff check . && poetry run mypy . && poetry run pytest  # validated linting, types, and tests
- git add pyproject.toml && git commit -m "chore: initialize Poetry project"  # committed Poetry configuration
- npm install -g pnpm  # installed pnpm globally
- git add package.json code_story js && git commit -m "chore: initialize pnpm workspace and basic folder structure"  # committed Node workspace scaffold
- git add docker-compose.yml && git commit -m "feat: add docker-compose for services"  # committed Docker Compose file
- git add .gitignore .editorconfig .ruff.toml .mypy.ini .eslintrc.json && git commit -m "chore: add repository configuration and quality tool configs"  # added repo ignores and config files
- git add .ruff.toml && git commit -m "fix: correct ruff config header"  # fixed ruff configuration section
- git add code_story/py.typed && git commit -m "feat: add py.typed for packaging to satisfy mypy"  # marked package as typed
- poetry run ruff check . && poetry run mypy . && poetry run pytest  # final validation before PR merge
