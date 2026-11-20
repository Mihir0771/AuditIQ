<#
.SYNOPSIS
  Task runner for AuditIQ on Windows PowerShell.
.DESCRIPTION
  Provides developer commands: install, dev, lint, format, typecheck, test, coverage, clean, doctor.
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("help", "install", "dev", "lint", "format", "typecheck", "test", "coverage", "clean", "doctor")]
    [string]$Task = "help"
)

switch ($Task) {
    "help" {
        Write-Host "AuditIQ PowerShell Task Runner" -ForegroundColor Cyan
        Write-Host "Usage: .\tasks.ps1 <task>"
        Write-Host "  install   : Install package"
        Write-Host "  dev       : Install package with dev dependencies + Playwright Chromium"
        Write-Host "  lint      : Run ruff linter"
        Write-Host "  format    : Run ruff code formatter"
        Write-Host "  typecheck : Run mypy type checking"
        Write-Host "  test      : Run pytest"
        Write-Host "  coverage  : Run pytest with test coverage"
        Write-Host "  clean     : Clean cache and build files"
        Write-Host "  doctor    : Run environment doctor check"
    }
    "install" {
        python -m pip install -e .
    }
    "dev" {
        python -m pip install -e ".[dev]"
        python -m playwright install chromium
    }
    "lint" {
        ruff check src tests
    }
    "format" {
        ruff format src tests
        ruff check --fix src tests
    }
    "typecheck" {
        mypy src tests
    }
    "test" {
        pytest
    }
    "coverage" {
        pytest --cov=auditiq --cov-report=term-missing --cov-report=html
    }
    "clean" {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .pytest_cache, .mypy_cache, .ruff_cache, htmlcov, .coverage, dist, build, *.egg-info
        Write-Host "Cleaned temporary files." -ForegroundColor Green
    }
    "doctor" {
        python -m auditiq doctor
    }
}
