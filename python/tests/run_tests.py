#!/usr/bin/env python3
"""Enhanced test runner for the Archon test suite.

This script provides a comprehensive interface for running tests with various options:
- Test type selection (unit, integration, e2e, performance)
- Marker-based filtering
- Parallel execution support
- Coverage reporting
- Performance profiling
- HTML report generation
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any


class TestRunner:
    """Enhanced test runner with advanced features."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_root = Path(__file__).parent
        self.pytest_args = ["pytest"]
        self.env = os.environ.copy()
        
    def add_common_args(self, args: argparse.Namespace):
        """Add common pytest arguments based on parsed args."""
        # Verbosity
        if args.verbose:
            self.pytest_args.append("-vv")
        elif args.quiet:
            self.pytest_args.append("-q")
        else:
            self.pytest_args.append("-v")
        
        # Show output
        if args.capture == "no":
            self.pytest_args.append("-s")
        elif args.capture == "sys":
            self.pytest_args.append("--capture=sys")
        
        # Traceback style
        self.pytest_args.append(f"--tb={args.tb}")
        
        # Stop on first failure
        if args.exitfirst:
            self.pytest_args.append("-x")
        
        # Last failed
        if args.lf:
            self.pytest_args.append("--lf")
        
        # Failed first
        if args.ff:
            self.pytest_args.append("--ff")
        
        # Parallel execution
        if args.parallel:
            self.pytest_args.extend(["-n", str(args.parallel)])
        
        # Random order
        if args.random:
            self.pytest_args.append("--random-order")
        
        # Timeout
        if args.timeout:
            self.pytest_args.append(f"--timeout={args.timeout}")
        
        # Max failures
        if args.maxfail:
            self.pytest_args.append(f"--maxfail={args.maxfail}")
    
    def add_coverage_args(self, args: argparse.Namespace):
        """Add coverage-related arguments."""
        if args.no_cov:
            self.pytest_args.append("--no-cov")
        else:
            # Coverage is enabled by default in pytest.ini
            if args.cov_report:
                for report_type in args.cov_report:
                    self.pytest_args.append(f"--cov-report={report_type}")
    
    def add_marker_filters(self, args: argparse.Namespace):
        """Add marker-based filtering."""
        markers = []
        
        # Test type markers
        if args.unit:
            markers.append("unit")
        if args.integration:
            markers.append("integration")
        if args.e2e:
            markers.append("e2e")
        if args.performance:
            markers.append("performance")
        
        # Priority markers
        if args.priority:
            markers.extend(args.priority)
        
        # Feature markers
        if args.feature:
            markers.extend(args.feature)
        
        # Custom markers
        if args.mark:
            markers.extend(args.mark)
        
        # Combine markers
        if markers:
            if args.all_markers:
                # All markers must match (AND)
                marker_expr = " and ".join(markers)
            else:
                # Any marker matches (OR)
                marker_expr = " or ".join(markers)
            
            self.pytest_args.extend(["-m", marker_expr])
        
        # Exclude markers
        if args.skip_mark:
            skip_expr = " or ".join(args.skip_mark)
            if markers:
                # Combine with existing markers
                self.pytest_args[-1] = f"({self.pytest_args[-1]}) and not ({skip_expr})"
            else:
                self.pytest_args.extend(["-m", f"not ({skip_expr})"])
    
    def add_test_selection(self, args: argparse.Namespace):
        """Add test file/directory selection."""
        if args.tests:
            # Specific test files or directories
            for test in args.tests:
                test_path = Path(test)
                if not test_path.is_absolute():
                    test_path = self.test_root / test_path
                self.pytest_args.append(str(test_path))
        elif args.type:
            # Test type directories
            type_dirs = {
                "unit": "unit",
                "integration": "integration",
                "e2e": "e2e",
                "performance": "performance"
            }
            for test_type in args.type:
                if test_type in type_dirs:
                    self.pytest_args.append(str(self.test_root / type_dirs[test_type]))
        else:
            # Default: run all tests
            self.pytest_args.append(str(self.test_root))
        
        # Keyword expression
        if args.keyword:
            self.pytest_args.extend(["-k", args.keyword])
    
    def add_reporting_args(self, args: argparse.Namespace):
        """Add reporting-related arguments."""
        # JUnit XML report
        if args.junit_xml:
            self.pytest_args.extend(["--junit-xml", args.junit_xml])
        
        # HTML report
        if args.html:
            self.pytest_args.extend(["--html", args.html, "--self-contained-html"])
        
        # JSON report
        if args.json_report:
            self.pytest_args.extend(["--json-report", "--json-report-file", args.json_report])
        
        # Duration reporting
        if args.durations is not None:
            self.pytest_args.extend(["--durations", str(args.durations)])
    
    def setup_environment(self, args: argparse.Namespace):
        """Set up environment variables."""
        self.env["TESTING"] = "true"
        
        if args.env:
            # Load environment from file
            env_file = Path(args.env)
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            self.env[key.strip()] = value.strip()
        
        # Set test environment
        if args.test_env:
            self.env["TEST_ENV"] = args.test_env
        
        # Debug mode
        if args.debug:
            self.env["PYTEST_DEBUG"] = "1"
            self.env["LOG_LEVEL"] = "DEBUG"
    
    def run(self, args: argparse.Namespace) -> int:
        """Run tests with the specified arguments."""
        # Build pytest command
        self.add_common_args(args)
        self.add_coverage_args(args)
        self.add_marker_filters(args)
        self.add_test_selection(args)
        self.add_reporting_args(args)
        
        # Setup environment
        self.setup_environment(args)
        
        # Dry run - just print the command
        if args.dry_run:
            print("Would run:", " ".join(self.pytest_args))
            print("\nEnvironment overrides:")
            for key, value in self.env.items():
                if key not in os.environ or os.environ[key] != value:
                    print(f"  {key}={value}")
            return 0
        
        # Show configuration
        if args.show_config:
            print("Test configuration:")
            print(f"  Project root: {self.project_root}")
            print(f"  Test root: {self.test_root}")
            print(f"  Command: {' '.join(self.pytest_args)}")
            print()
        
        # Run tests
        start_time = time.time()
        
        try:
            result = subprocess.run(
                self.pytest_args,
                cwd=self.project_root,
                env=self.env,
                check=False
            )
            
            duration = time.time() - start_time
            
            # Print summary
            if not args.quiet:
                print(f"\nTests completed in {duration:.2f} seconds")
                
                if result.returncode == 0:
                    print("✅ All tests passed!")
                else:
                    print(f"❌ Tests failed with exit code: {result.returncode}")
            
            return result.returncode
            
        except KeyboardInterrupt:
            print("\n\nTest run interrupted by user")
            return 130
        except Exception as e:
            print(f"\nError running tests: {e}")
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced test runner for Archon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all unit tests
  %(prog)s --unit
  
  # Run integration and e2e tests in parallel
  %(prog)s --integration --e2e -n 4
  
  # Run tests matching a keyword
  %(prog)s -k "test_project or test_task"
  
  # Run critical priority tests only
  %(prog)s --priority critical
  
  # Run tests with specific markers
  %(prog)s -m "websocket and not slow"
  
  # Run failed tests from last run
  %(prog)s --lf
  
  # Generate HTML report
  %(prog)s --html report.html
"""
    )
    
    # Test selection
    selection = parser.add_argument_group("test selection")
    selection.add_argument("tests", nargs="*", help="Specific test files or directories")
    selection.add_argument("-k", "--keyword", help="Only run tests matching keyword expression")
    selection.add_argument("--type", choices=["unit", "integration", "e2e", "performance"],
                          action="append", help="Test types to run")
    
    # Test type shortcuts
    types = parser.add_argument_group("test type shortcuts")
    types.add_argument("--unit", action="store_true", help="Run unit tests")
    types.add_argument("--integration", action="store_true", help="Run integration tests")
    types.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    types.add_argument("--performance", action="store_true", help="Run performance tests")
    
    # Markers
    markers = parser.add_argument_group("marker filtering")
    markers.add_argument("-m", "--mark", action="append", help="Run tests matching marker(s)")
    markers.add_argument("--skip-mark", action="append", help="Skip tests matching marker(s)")
    markers.add_argument("--priority", choices=["critical", "high", "standard", "nice_to_have"],
                        action="append", help="Run tests with specific priority")
    markers.add_argument("--feature", action="append",
                        help="Run tests for specific features (websocket, sse, mcp, rag)")
    markers.add_argument("--all-markers", action="store_true",
                        help="Require all specified markers (AND instead of OR)")
    
    # Execution options
    execution = parser.add_argument_group("execution options")
    execution.add_argument("-n", "--parallel", type=int, metavar="N",
                          help="Run tests in parallel using N workers")
    execution.add_argument("-x", "--exitfirst", action="store_true",
                          help="Exit on first failure")
    execution.add_argument("--maxfail", type=int, metavar="N",
                          help="Exit after N failures")
    execution.add_argument("--lf", "--last-failed", action="store_true",
                          help="Run only tests that failed last time")
    execution.add_argument("--ff", "--failed-first", action="store_true",
                          help="Run failed tests first")
    execution.add_argument("--random", action="store_true",
                          help="Run tests in random order")
    execution.add_argument("--timeout", type=int, metavar="SECONDS",
                          help="Timeout for each test")
    
    # Output options
    output = parser.add_argument_group("output options")
    output.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    output.add_argument("-q", "--quiet", action="store_true", help="Quiet output")
    output.add_argument("--tb", choices=["auto", "short", "line", "no"],
                       default="short", help="Traceback style")
    output.add_argument("--capture", choices=["yes", "no", "sys"],
                       default="yes", help="Capture stdout/stderr")
    output.add_argument("--show-config", action="store_true",
                       help="Show test configuration before running")
    
    # Coverage options
    coverage = parser.add_argument_group("coverage options")
    coverage.add_argument("--no-cov", action="store_true", help="Disable coverage")
    coverage.add_argument("--cov-report", action="append",
                         choices=["term", "term-missing", "html", "xml", "json"],
                         help="Coverage report format(s)")
    
    # Reporting options
    reporting = parser.add_argument_group("reporting options")
    reporting.add_argument("--junit-xml", metavar="FILE", help="Generate JUnit XML report")
    reporting.add_argument("--html", metavar="FILE", help="Generate HTML report")
    reporting.add_argument("--json-report", metavar="FILE", help="Generate JSON report")
    reporting.add_argument("--durations", type=int, metavar="N",
                          help="Show N slowest test durations (0 for all)")
    
    # Environment options
    env = parser.add_argument_group("environment options")
    env.add_argument("--env", metavar="FILE", help="Load environment from file")
    env.add_argument("--test-env", choices=["local", "ci", "staging"],
                    default="local", help="Test environment")
    env.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    # Other options
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be run without running tests")
    
    args = parser.parse_args()
    
    # Create and run test runner
    runner = TestRunner()
    return runner.run(args)


if __name__ == "__main__":
    sys.exit(main())