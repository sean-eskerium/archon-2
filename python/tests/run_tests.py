#!/usr/bin/env python3
"""
Comprehensive test runner for Archon Python backend.

This script runs the full test suite with proper coverage reporting.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the src directory to Python path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

def run_tests(test_type: str = "all", verbose: bool = True, coverage: bool = True):
    """
    Run the test suite.
    
    Args:
        test_type: Type of tests to run (unit, integration, e2e, all)
        verbose: Show verbose output
        coverage: Generate coverage report
    """
    # Ensure we're in the tests directory
    os.chdir(BASE_DIR)
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory based on type
    if test_type == "unit":
        cmd.append("tests/unit")
    elif test_type == "integration":
        cmd.append("tests/integration")
    elif test_type == "e2e":
        cmd.append("tests/e2e")
    elif test_type == "all":
        cmd.append("tests")
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-fail-under=80"
        ])
    
    # Add markers
    cmd.extend(["-m", test_type if test_type != "all" else ""])
    
    # Run the tests
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, env={**os.environ, "TESTING": "true"})
    
    if result.returncode == 0:
        print(f"\n✅ {test_type.capitalize()} tests passed!")
        if coverage:
            print("\n📊 Coverage report generated in htmlcov/index.html")
    else:
        print(f"\n❌ {test_type.capitalize()} tests failed!")
    
    return result.returncode

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Archon Python tests")
    parser.add_argument(
        "type",
        choices=["unit", "integration", "e2e", "all"],
        nargs="?",
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage reporting"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Less verbose output"
    )
    
    args = parser.parse_args()
    
    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        verbose=not args.quiet,
        coverage=not args.no_coverage
    )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()