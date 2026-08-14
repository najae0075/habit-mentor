import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_application_layers_are_present():
    expected = {
        "pages": ["admin.py", "daily.py", "guide.py", "router.py"],
        "services": ["supabase.py"],
        "domain": ["habits.py", "recommendations.py", "progress.py"],
        "components": ["layout.py", "sidebar.py"],
        "styles": ["app.css"],
    }
    for directory, files in expected.items():
        for filename in files:
            assert (ROOT / directory / filename).is_file()


def test_streamlit_automatic_pages_menu_is_disabled():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "showSidebarNavigation = false" in config


def test_app_is_an_orchestrator_for_extracted_layers():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "from components.layout import inject_styles" in app
    assert "from pages.router import render_page" in app
    assert "from services.supabase import SupabaseBackend" in app
    assert "from domain.progress import" in app
    assert "@media" not in app


def test_app_avoids_runtime_sensitive_toasts():
    python_files = [ROOT / "app.py", *(ROOT / "pages").glob("*.py")]
    for path in python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            function = call.func
            assert not (
                isinstance(function, ast.Attribute) and function.attr == "toast"
            ), path
