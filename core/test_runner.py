import subprocess
import os
import json
from pathlib import Path

class TestRunner:
    """Run tests using various frameworks (Pytest, Jest, Mocha)."""
    
    def __init__(self, workspace_root):
        # .resolve() ensures we have a clean absolute path for subprocess calls
        self.workspace_root = Path(workspace_root).resolve()
    
    def run_tests(self, path, framework='pytest'):
        """
        Execute tests at given path and return a structured summary.
        """
        test_path = Path(path)
        if not test_path.exists():
            return {"error": "Path does not exist: " + str(path)}
        
        # Initialize result object
        result = {
            'framework': framework,
            'status': 'unknown',
            'counts': {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0},
            'output_snippet': '',
            'full_logs': ''
        }
        
        # 1. Map frameworks to their CLI commands
        commands = {
            'pytest': ['pytest', str(test_path), '-v'],
            'jest': ['npx', 'jest', str(test_path), '--json'],
            'mocha': ['npx', 'mocha', str(test_path), '--reporter', 'json']
        }
        
        if framework not in commands:
            return {"error": "Unsupported framework: " + framework}

        try:
            # 2. Run the subprocess
            proc = subprocess.run(
                commands[framework],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=60  # Prevent infinite loops from hanging the AI
            )
            
            raw_output = proc.stdout + proc.stderr
            result['full_logs'] = raw_output
            
            # 3. Parse output based on framework
            if framework == 'pytest':
                self._parse_pytest(raw_output, result)
            else:
                self._parse_json_frameworks(proc.stdout, raw_output, result, framework)

            # 4. Final Status Check
            if result['counts']['failed'] > 0 or result['counts']['errors'] > 0:
                result['status'] = 'FAILED'
            elif result['counts']['passed'] > 0:
                result['status'] = 'PASSED'
            
            # Truncate logs for AI efficiency (keep the last 2000 chars where errors usually are)
            result['output_snippet'] = raw_output[-2000:] if len(raw_output) > 2000 else raw_output
            
            return result

        except subprocess.TimeoutExpired:
            return {"error": "Test execution timed out after 60 seconds."}
        except Exception as e:
            return {"error": "Runner exception: " + str(e)}

    def _parse_pytest(self, output, result):
        """Heuristic parsing for Pytest output."""
        result['counts']['passed'] = output.count('PASSED')
        result['counts']['failed'] = output.count('FAILED')
        result['counts']['errors'] = output.count('ERROR')
        result['counts']['skipped'] = output.count('SKIPPED')
        result['counts']['total'] = sum(result['counts'].values())

    def _parse_json_frameworks(self, stdout, full_output, result, framework):
        """Parse JSON output for Jest/Mocha or fallback to symbol counting."""
        try:
            # Locate the start of JSON in case of pre-log warnings
            json_start = stdout.find('{')
            if json_start != -1:
                data = json.loads(stdout[json_start:])
                if framework == 'jest':
                    result['counts']['total'] = data.get('numTotalTests', 0)
                    result['counts']['passed'] = data.get('numPassedTests', 0)
                    result['counts']['failed'] = data.get('numFailedTests', 0)
                elif framework == 'mocha':
                    stats = data.get('stats', {})
                    result['counts']['total'] = stats.get('tests', 0)
                    result['counts']['passed'] = stats.get('passes', 0)
                    result['counts']['failed'] = stats.get('failures', 0)
                return
        except:
            pass # If JSON fails, fall back to counting checkmarks/symbols
        
        result['counts']['passed'] = full_output.count('✓') + full_output.count('passed')
        result['counts']['failed'] = full_output.count('✕') + full_output.count('failed')