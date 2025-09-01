#!/usr/bin/env node

/**
 * Syntax Validation Script
 * Validates TypeScript/JavaScript files for basic syntax errors
 */

const fs = require('fs');
const path = require('path');

// Simple syntax validation patterns
const syntaxChecks = {
  typescript: {
    patterns: [
      { name: 'Unclosed braces', regex: /\{[^}]*$/, severity: 'error' },
      { name: 'Unclosed parentheses', regex: /\([^)]*$/, severity: 'error' },
      { name: 'Missing semicolons', regex: /\w+\s*\n\s*\w+/, severity: 'warning' },
      { name: 'Unused imports', regex: /import.*from.*['"][^'"]*['"];\s*\n\s*\n/, severity: 'info' }
    ]
  },
  javascript: {
    patterns: [
      { name: 'Unclosed braces', regex: /\{[^}]*$/, severity: 'error' },
      { name: 'Unclosed parentheses', regex: /\([^)]*$/, severity: 'error' }
    ]
  }
};

// Check if file has valid structure
function validateFileStructure(filePath, content) {
  const issues = [];
  
  // Check for basic React component structure
  if (filePath.includes('pages/') && (filePath.endsWith('.tsx') || filePath.endsWith('.jsx'))) {
    if (!content.includes('export default')) {
      issues.push({ type: 'error', message: 'Missing default export for page component' });
    }
  }
  
  // Check for API route structure
  if (filePath.includes('pages/api/') && (filePath.endsWith('.ts') || filePath.endsWith('.js'))) {
    if (!content.includes('export default') && !content.includes('handler')) {
      issues.push({ type: 'error', message: 'Missing default export or handler for API route' });
    }
  }
  
  // Check for proper imports
  if (content.includes('React') && !content.includes('import') && !content.includes('require')) {
    issues.push({ type: 'warning', message: 'Using React without import statement' });
  }
  
  return issues;
}

// Validate a single file
function validateFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const ext = path.extname(filePath);
    const issues = [];
    
    // Basic structure validation
    const structureIssues = validateFileStructure(filePath, content);
    issues.push(...structureIssues);
    
    // Count braces and parentheses
    const openBraces = (content.match(/\{/g) || []).length;
    const closeBraces = (content.match(/\}/g) || []).length;
    const openParens = (content.match(/\(/g) || []).length;
    const closeParens = (content.match(/\)/g) || []).length;
    
    if (openBraces !== closeBraces) {
      issues.push({ 
        type: 'error', 
        message: `Mismatched braces: ${openBraces} open, ${closeBraces} close` 
      });
    }
    
    if (openParens !== closeParens) {
      issues.push({ 
        type: 'error', 
        message: `Mismatched parentheses: ${openParens} open, ${closeParens} close` 
      });
    }
    
    // Check for common syntax issues
    const lines = content.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const lineNum = i + 1;
      
      // Check for missing semicolons (basic check)
      if (line.trim().match(/^(const|let|var|return)\s+.*[^;{}\s]$/)) {
        issues.push({ 
          type: 'warning', 
          message: `Line ${lineNum}: Possible missing semicolon`,
          line: lineNum 
        });
      }
      
      // Check for console.log (should be removed in production)
      if (line.includes('console.log') && !line.includes('//')) {
        issues.push({ 
          type: 'info', 
          message: `Line ${lineNum}: Console.log found (consider removing for production)`,
          line: lineNum 
        });
      }
    }
    
    return { valid: issues.filter(i => i.type === 'error').length === 0, issues };
    
  } catch (error) {
    return { 
      valid: false, 
      issues: [{ type: 'error', message: `Failed to read file: ${error.message}` }] 
    };
  }
}

// Find all TypeScript/JavaScript files
function findSourceFiles(dir, files = []) {
  const entries = fs.readdirSync(dir);
  
  for (const entry of entries) {
    const fullPath = path.join(dir, entry);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      // Skip node_modules and .next directories
      if (!['node_modules', '.next', '.git', 'dist', 'build'].includes(entry)) {
        findSourceFiles(fullPath, files);
      }
    } else if (stat.isFile()) {
      const ext = path.extname(entry);
      if (['.ts', '.tsx', '.js', '.jsx'].includes(ext)) {
        files.push(fullPath);
      }
    }
  }
  
  return files;
}

// Main validation function
async function validateProject() {
  console.log('🔍 Starting Syntax Validation...\n');
  
  const projectRoot = __dirname;
  const sourceFiles = findSourceFiles(projectRoot);
  
  console.log(`Found ${sourceFiles.length} source files to validate\n`);
  
  let totalFiles = 0;
  let validFiles = 0;
  let totalIssues = { error: 0, warning: 0, info: 0 };
  
  for (const filePath of sourceFiles) {
    const relativePath = path.relative(projectRoot, filePath);
    const result = validateFile(filePath);
    
    totalFiles++;
    if (result.valid) {
      validFiles++;
    }
    
    // Count issues by type
    for (const issue of result.issues) {
      totalIssues[issue.type]++;
    }
    
    // Report results
    if (result.issues.length === 0) {
      console.log(`✅ ${relativePath}`);
    } else {
      const errorCount = result.issues.filter(i => i.type === 'error').length;
      const warningCount = result.issues.filter(i => i.type === 'warning').length;
      const infoCount = result.issues.filter(i => i.type === 'info').length;
      
      const status = errorCount > 0 ? '❌' : warningCount > 0 ? '⚠️' : 'ℹ️';
      console.log(`${status} ${relativePath}`);
      
      for (const issue of result.issues) {
        const prefix = issue.type === 'error' ? '  ❌' : issue.type === 'warning' ? '  ⚠️' : '  ℹ️';
        const location = issue.line ? ` (line ${issue.line})` : '';
        console.log(`${prefix} ${issue.message}${location}`);
      }
    }
  }
  
  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 Validation Summary:');
  console.log('='.repeat(60));
  console.log(`Files validated: ${totalFiles}`);
  console.log(`Files without errors: ${validFiles}`);
  console.log(`Files with errors: ${totalFiles - validFiles}`);
  console.log(`\nIssues found:`);
  console.log(`  ❌ Errors: ${totalIssues.error}`);
  console.log(`  ⚠️  Warnings: ${totalIssues.warning}`);
  console.log(`  ℹ️  Info: ${totalIssues.info}`);
  
  const success = totalIssues.error === 0;
  
  if (success) {
    console.log('\n🚀 Syntax validation passed! No critical errors found.');
  } else {
    console.log('\n⚠️  Syntax validation found errors that need to be fixed.');
  }
  
  return success;
}

// Run validation if called directly
if (require.main === module) {
  validateProject()
    .then(success => process.exit(success ? 0 : 1))
    .catch(error => {
      console.error('Validation error:', error);
      process.exit(1);
    });
}

module.exports = { validateProject };