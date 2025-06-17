#!/usr/bin/env node

/**
 * Test Runner Script for Archon Frontend
 * 
 * This script provides a unified interface for running different types of tests
 * with various options for coverage, filtering, and reporting.
 * 
 * Usage:
 *   node test/run_tests.js [options]
 * 
 * Options:
 *   --type <unit|integration|e2e|all>  Run specific type of tests (default: all)
 *   --coverage                         Run with coverage report
 *   --watch                           Run in watch mode
 *   --ui                              Open Vitest UI
 *   --filter <pattern>                Filter tests by pattern
 *   --update-snapshots                Update snapshots
 *   --bail                            Stop on first test failure
 *   --verbose                         Verbose output
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Parse command line arguments
const args = process.argv.slice(2);
const options = {
  type: 'all',
  coverage: false,
  watch: false,
  ui: false,
  filter: null,
  updateSnapshots: false,
  bail: false,
  verbose: false,
};

// Process arguments
for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case '--type':
      options.type = args[++i] || 'all';
      break;
    case '--coverage':
      options.coverage = true;
      break;
    case '--watch':
      options.watch = true;
      break;
    case '--ui':
      options.ui = true;
      break;
    case '--filter':
      options.filter = args[++i];
      break;
    case '--update-snapshots':
      options.updateSnapshots = true;
      break;
    case '--bail':
      options.bail = true;
      break;
    case '--verbose':
      options.verbose = true;
      break;
    case '--help':
      showHelp();
      process.exit(0);
  }
}

function showHelp() {
  console.log(`
Archon Frontend Test Runner

Usage:
  node test/run_tests.js [options]

Options:
  --type <unit|integration|e2e|all>  Run specific type of tests (default: all)
  --coverage                         Run with coverage report
  --watch                           Run in watch mode
  --ui                              Open Vitest UI
  --filter <pattern>                Filter tests by pattern
  --update-snapshots                Update snapshots
  --bail                            Stop on first test failure
  --verbose                         Verbose output
  --help                            Show this help message

Examples:
  # Run all tests with coverage
  node test/run_tests.js --coverage

  # Run only unit tests in watch mode
  node test/run_tests.js --type unit --watch

  # Run tests matching a pattern
  node test/run_tests.js --filter "websocket"

  # Open Vitest UI
  node test/run_tests.js --ui
  `);
}

// Build vitest command
function buildCommand() {
  const vitestArgs = ['vitest'];

  // Add test type filter
  if (options.type !== 'all') {
    const patterns = {
      unit: 'test/(services|components|hooks|contexts|lib)/**/*.test.{ts,tsx}',
      integration: 'test/integration/**/*.test.{ts,tsx}',
      e2e: 'test/e2e/**/*.test.{ts,tsx}',
    };
    
    if (patterns[options.type]) {
      vitestArgs.push(patterns[options.type]);
    }
  }

  // Add options
  if (options.coverage) {
    vitestArgs.push('--coverage');
  }

  if (options.watch) {
    vitestArgs.push('--watch');
  } else {
    vitestArgs.push('--run');
  }

  if (options.ui) {
    vitestArgs.push('--ui');
  }

  if (options.filter) {
    vitestArgs.push('--grep', options.filter);
  }

  if (options.updateSnapshots) {
    vitestArgs.push('--update');
  }

  if (options.bail) {
    vitestArgs.push('--bail', '1');
  }

  if (options.verbose) {
    vitestArgs.push('--reporter=verbose');
  }

  return vitestArgs;
}

// Run tests
function runTests() {
  const command = buildCommand();
  
  console.log('🧪 Running Archon Frontend Tests');
  console.log('📋 Command:', 'npx', command.join(' '));
  console.log('');

  const startTime = Date.now();
  
  const child = spawn('npx', command, {
    stdio: 'inherit',
    shell: true,
    cwd: path.resolve(__dirname, '..'),
  });

  child.on('close', (code) => {
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    
    console.log('');
    console.log('⏱️  Test execution time:', duration, 'seconds');
    
    if (code === 0) {
      console.log('✅ Tests passed!');
      
      if (options.coverage) {
        console.log('📊 Coverage report generated at: coverage/index.html');
        console.log('   Run "open coverage/index.html" to view the report');
      }
    } else {
      console.log('❌ Tests failed with exit code:', code);
    }
    
    process.exit(code);
  });

  child.on('error', (error) => {
    console.error('❌ Failed to run tests:', error);
    process.exit(1);
  });
}

// Check if we're in the right directory
function checkDirectory() {
  const packageJsonPath = path.join(__dirname, '..', 'package.json');
  
  if (!fs.existsSync(packageJsonPath)) {
    console.error('❌ Error: package.json not found. Make sure you run this script from the archon-ui-main directory.');
    process.exit(1);
  }
  
  try {
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    if (!packageJson.devDependencies || !packageJson.devDependencies.vitest) {
      console.error('❌ Error: Vitest not found in devDependencies. Run "npm install" first.');
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Error reading package.json:', error.message);
    process.exit(1);
  }
}

// Generate coverage report summary
function showCoverageSummary() {
  const coveragePath = path.join(__dirname, '..', 'coverage', 'coverage-summary.json');
  
  if (fs.existsSync(coveragePath)) {
    try {
      const coverage = JSON.parse(fs.readFileSync(coveragePath, 'utf8'));
      const total = coverage.total;
      
      console.log('\n📊 Coverage Summary:');
      console.log(`   Statements: ${total.statements.pct}%`);
      console.log(`   Branches:   ${total.branches.pct}%`);
      console.log(`   Functions:  ${total.functions.pct}%`);
      console.log(`   Lines:      ${total.lines.pct}%`);
    } catch (error) {
      // Ignore coverage summary errors
    }
  }
}

// Main execution
async function main() {
  checkDirectory();
  runTests();
  
  // Show coverage summary after tests complete (if coverage was requested)
  if (options.coverage) {
    process.on('exit', () => {
      showCoverageSummary();
    });
  }
}

// Handle interrupts gracefully
process.on('SIGINT', () => {
  console.log('\n\n🛑 Test run interrupted by user');
  process.exit(130);
});

// Run the script
main();