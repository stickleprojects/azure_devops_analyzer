"""
Unit tests for verifying Python imports and module structure.

These tests verify that all imports are correctly configured without
executing the actual code logic.
"""

import sys
import importlib.util
from pathlib import Path


def _get_project_root() -> Path:
    """Get the project root directory (where pyproject.toml is located)."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


class TestImportsAndStructure:
    """Test suite for verifying Python module imports and structure."""

    def test_celery_app_module_exists(self):
        """Verify celery_app module can be imported."""
        spec = importlib.util.find_spec("src.scheduler.celery_app")
        assert spec is not None, "src.scheduler.celery_app module not found"
        assert spec.origin is not None, "celery_app.py not found on disk"

    def test_tasks_module_imports(self):
        """Verify tasks module has correct imports."""
        spec = importlib.util.find_spec("src.scheduler.tasks")
        assert spec is not None, "src.scheduler.tasks module not found"
        
        # Read the file and check key imports
        project_root = _get_project_root()
        tasks_file = project_root / "src" / "scheduler" / "tasks.py"
        content = tasks_file.read_text()
        
        required_imports = [
            "from src.scheduler.celery_app import celery_app",
            "from src.workflows.github_analysis import GitHubAnalysisWorkflow",
        ]
        
        for required_import in required_imports:
            assert required_import in content, \
                f"Missing required import: {required_import}"

    def test_submit_extraction_task_imports(self):
        """Verify submit_extraction_task.py has correct imports."""
        project_root = _get_project_root()
        script_file = project_root / "scripts" / "submit_extraction_task.py"
        assert script_file.exists(), "submit_extraction_task.py not found"
        
        content = script_file.read_text()
        
        required_imports = [
            "from src.scheduler.celery_app import celery_app",
            "from src.scheduler.tasks import run_github_extraction",
        ]
        
        for required_import in required_imports:
            assert required_import in content, \
                f"Missing required import in submit_extraction_task.py: {required_import}"

    def test_no_circular_imports(self):
        """Verify there are no obvious circular imports in module structure."""
        # Check tasks.py doesn't import from submit_extraction_task
        project_root = _get_project_root()
        tasks_file = project_root / "src" / "scheduler" / "tasks.py"
        content = tasks_file.read_text()
        assert "from scripts" not in content, "Circular import detected: tasks imports from scripts"
        assert "submit_extraction_task" not in content, "Circular import detected"

    def test_celery_app_structure(self):
        """Verify celery_app.py has required structure."""
        project_root = _get_project_root()
        celery_file = project_root / "src" / "scheduler" / "celery_app.py"
        assert celery_file.exists(), "celery_app.py not found"
        
        content = celery_file.read_text()
        
        required_elements = [
            "celery_app = Celery",
            "broker_url",
            "celery_app.conf.update",
            "celery_app.autodiscover_tasks",
        ]
        
        for element in required_elements:
            assert element in content, f"Missing required element in celery_app.py: {element}"

    def test_tasks_define_correct_task_names(self):
        """Verify tasks are defined with correct names."""
        project_root = _get_project_root()
        tasks_file = project_root / "src" / "scheduler" / "tasks.py"
        content = tasks_file.read_text()
        
        required_tasks = [
            '@celery_app.task(name="tasks.run_github_extraction"',
            'def run_github_extraction',
        ]
        
        for task_def in required_tasks:
            assert task_def in content, f"Missing task definition: {task_def}"

    def test_workflow_import_path(self):
        """Verify GitHubAnalysisWorkflow can be imported from correct path."""
        spec = importlib.util.find_spec("src.workflows.github_analysis")
        assert spec is not None, "src.workflows.github_analysis module not found"

    def test_no_missing_module_references(self):
        """Verify files don't reference non-existent modules."""
        project_root = _get_project_root()
        tasks_file = project_root / "src" / "scheduler" / "tasks.py"
        content = tasks_file.read_text()
        
        # These should NOT be imported (were removed as non-existent)
        forbidden_imports = [
            "from tasks.extraction",
            "from tasks.analysis",
            "from tasks.storage",
            "from tasks.maintenance",
            "from scheduler.celery_app",
        ]
        
        for forbidden in forbidden_imports:
            assert forbidden not in content, \
                f"File still references non-existent module: {forbidden}"

    def test_syntax_is_valid_python(self):
        """Verify Python files have valid syntax."""
        import py_compile
        
        project_root = _get_project_root()
        files_to_check = [
            "src/scheduler/celery_app.py",
            "src/scheduler/tasks.py",
            "scripts/submit_extraction_task.py",
        ]
        
        for file_path in files_to_check:
            full_path = project_root / file_path
            try:
                py_compile.compile(str(full_path), doraise=True)
            except py_compile.PyCompileError as e:
                raise AssertionError(f"Syntax error in {file_path}: {e}")


class TestModuleImportability:
    """Test that modules can be imported without runtime execution."""

    def test_celery_app_can_be_loaded(self):
        """Test that celery_app module can be loaded as a spec."""
        spec = importlib.util.find_spec("src.scheduler.celery_app")
        assert spec is not None
        assert spec.origin is not None
        
        # Load module without executing
        module = importlib.util.module_from_spec(spec)
        assert module is not None

    def test_tasks_module_structure(self):
        """Test that tasks module has expected function definitions."""
        project_root = _get_project_root()
        tasks_file = project_root / "src" / "scheduler" / "tasks.py"
        content = tasks_file.read_text()
        
        # Check function definitions exist
        assert "def run_github_extraction" in content
        assert "def cleanup_database" in content
        assert "def backup_database" in content
        
        # Check they're decorated as Celery tasks
        assert "@celery_app.task" in content


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
