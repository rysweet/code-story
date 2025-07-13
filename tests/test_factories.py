# specs: specs/06-ingestion-pipeline/ingestion-pipeline.md
# code rules: .roo/rules-code/08-unified-test-infra.md, .roo/rules-code/04-testing-requirements.md, .roo/rules-code/03-coding-guidelines.md

"""
Test Data Factories for Integration/E2E Tests

This module provides standardized, reusable, and composable test data builders for common entities
such as repositories, users, jobs, and graphdb nodes. All factories are designed for isolation, reproducibility,
and compatibility with parallel test execution.

Usage:
    from tests.test_factories import UserFactory, RepositoryFactory, JobFactory, FileNodeFactory, DirectoryNodeFactory

    user = UserFactory.build()
    repo = RepositoryFactory.build(owner=user)
    job = JobFactory.build(repository=repo)
    file_node = FileNodeFactory.build()
    dir_node = DirectoryNodeFactory.build()

All factories return plain dataclasses or Pydantic models, and do not persist to any database or service.
Persistence (if needed) should be handled in the test using the unified fixture.

References:
    - [Ingestion Pipeline Spec](../specs/06-ingestion-pipeline/ingestion-pipeline.md)
    - [Unified Test Infra Rules](../.roo/rules-code/08-unified-test-infra.md)
    - [Testing Requirements](../.roo/rules-code/04-testing-requirements.md)
    - [Coding Guidelines](../.roo/rules-code/03-coding-guidelines.md)
"""

import uuid
import random
import string
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# Existing factories for User, Repository, Job...

def _random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@dataclass
class User:
    id: str
    username: str
    email: str
    is_active: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

class UserFactory:
    @staticmethod
    def build(username: Optional[str] = None, email: Optional[str] = None, is_active: bool = True, **kwargs) -> User:
        uid = str(uuid.uuid4())
        uname = username or f"user_{_random_string()}"
        mail = email or f"{uname}@example.com"
        return User(
            id=uid,
            username=uname,
            email=mail,
            is_active=is_active,
            extra=kwargs
        )

@dataclass
class Repository:
    id: str
    name: str
    owner_id: str
    url: str
    is_private: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

class RepositoryFactory:
    @staticmethod
    def build(owner: Optional[User] = None, name: Optional[str] = None, is_private: bool = False, **kwargs) -> Repository:
        rid = str(uuid.uuid4())
        repo_name = name or f"repo_{_random_string()}"
        owner_obj = owner or UserFactory.build()
        url = f"https://example.com/{owner_obj.username}/{repo_name}"
        return Repository(
            id=rid,
            name=repo_name,
            owner_id=owner_obj.id,
            url=url,
            is_private=is_private,
            extra=kwargs
        )

@dataclass
class Job:
    id: str
    repository_id: str
    user_id: str
    status: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

class JobFactory:
    @staticmethod
    def build(repository: Optional[Repository] = None, user: Optional[User] = None, status: str = "pending", parameters: Optional[Dict[str, Any]] = None, **kwargs) -> Job:
        jid = str(uuid.uuid4())
        repo_obj = repository or RepositoryFactory.build()
        user_obj = user or UserFactory.build()
        params = parameters or {}
        return Job(
            id=jid,
            repository_id=repo_obj.id,
            user_id=user_obj.id,
            status=status,
            parameters=params,
            extra=kwargs
        )

# --- New: GraphDB Node Factories ---

from codestory.graphdb.models import FileNode, DirectoryNode

class FileNodeFactory:
    @staticmethod
    def build(
        path: Optional[str] = None,
        name: Optional[str] = None,
        extension: Optional[str] = None,
        size: Optional[int] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> FileNode:
        fname = name or f"file_{_random_string(5)}.py"
        fpath = path or f"/tmp/{fname}"
        ext = extension or fname.split('.')[-1]
        fsize = size if size is not None else random.randint(100, 4096)
        fcontent = content or f"print('test {fname}')"
        return FileNode(
            path=fpath,
            name=fname,
            extension=ext,
            size=fsize,
            content=fcontent,
            **kwargs
        )

class DirectoryNodeFactory:
    @staticmethod
    def build(
        path: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> DirectoryNode:
        dname = name or f"dir_{_random_string(5)}"
        dpath = path or f"/tmp/{dname}"
        return DirectoryNode(
            path=dpath,
            name=dname,
            **kwargs
        )