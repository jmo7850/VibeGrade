"""Pytest configuration and fixtures."""

import asyncio
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn))
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_ts_project(temp_workspace):
    """Create a minimal TypeScript project for testing."""
    project = temp_workspace / "test_ts_project"
    project.mkdir()

    # package.json
    (project / "package.json").write_text("""
{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc",
    "test": "jest"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "jest": "^29.0.0",
    "@types/jest": "^29.0.0"
  }
}
""")

    # tsconfig.json
    (project / "tsconfig.json").write_text("""
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true,
    "outDir": "./dist"
  },
  "include": ["src/**/*"]
}
""")

    # Source file
    src = project / "src"
    src.mkdir()
    (src / "index.ts").write_text("""
export function greet(name: string): string {
  return `Hello, ${name}!`;
}

export function add(a: number, b: number): number {
  return a + b;
}
""")

    # Test file
    (src / "index.test.ts").write_text("""
import { greet, add } from './index';

test('greet returns greeting', () => {
  expect(greet('World')).toBe('Hello, World!');
});

test('add adds numbers', () => {
  expect(add(2, 3)).toBe(5);
});
""")

    return project


@pytest.fixture
def sample_py_project(temp_workspace):
    """Create a minimal Python project for testing."""
    project = temp_workspace / "test_py_project"
    project.mkdir()

    # pyproject.toml
    (project / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "1.0.0"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
""")

    # Source file
    src = project / "src"
    src.mkdir()
    (src / "main.py").write_text("""
def greet(name: str) -> str:
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    return a + b

if __name__ == "__main__":
    print(greet("World"))
""")

    # Test file
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("""
from src.main import greet, add

def test_greet():
    assert greet("World") == "Hello, World!"

def test_add():
    assert add(2, 3) == 5
""")

    return project


@pytest.fixture
def problematic_ts_project(temp_workspace):
    """Create a TypeScript project with known issues for testing."""
    project = temp_workspace / "problematic_ts"
    project.mkdir()

    (project / "package.json").write_text("""
{
  "name": "problematic-project",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc",
    "test": "jest"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "jest": "^29.0.0"
  }
}
""")

    (project / "tsconfig.json").write_text("""
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true
  }
}
""")

    src = project / "src"
    src.mkdir()

    # File with unused variable
    (src / "utils.ts").write_text("""
export function processData(data: string) {
  const unused = "this is not used";
  return data.toUpperCase();
}

const apiKey = "sk_live_abcdef123456"; // Secret!
""")

    return project


@pytest.fixture
def settings():
    """Test settings."""
    return Settings(
        app_env="test",
        app_debug=True,
        database_url="sqlite+aiosqlite:///:memory:",
        github_token=None,
        rubric_version="v1",
        rubric_path=Path("../rubric/v1.yaml"),
    )
