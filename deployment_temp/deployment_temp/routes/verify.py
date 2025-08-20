import ast
import re
import json
from typing import Dict, Any, List, Tuple
from starlette.routing import Router, Route
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP


class MCPCodeValidator:
    """Validates MCP server code for correctness and security"""
    
    DANGEROUS_FUNCTIONS = [
        'eval', 'exec', 'compile', '__import__', 'open', 'file',
        'input', 'raw_input', 'reload', 'vars', 'globals', 'locals',
        'dir', 'getattr', 'setattr', 'hasattr', 'delattr'
    ]
    
    DANGEROUS_MODULES = [
        'os', 'sys', 'subprocess', 'shutil', 'socket', 'urllib',
        'requests', 'http', 'ftplib', 'smtplib', 'telnetlib'
    ]
    
    @staticmethod
    def validate_syntax(source_code: str) -> Tuple[bool, str]:
        """Check if code has valid Python syntax"""
        try:
            ast.parse(source_code)
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
        except Exception as e:
            return False, f"Parse error: {str(e)}"
    
    @staticmethod
    def check_security(source_code: str) -> List[str]:
        """Check for potentially dangerous code patterns"""
        issues = []
        
        # Check for dangerous function calls
        for func in MCPCodeValidator.DANGEROUS_FUNCTIONS:
            if re.search(rf'\b{func}\s*\(', source_code):
                issues.append(f"Dangerous function detected: {func}")
        
        # Check for dangerous imports
        for module in MCPCodeValidator.DANGEROUS_MODULES:
            if re.search(rf'import\s+{module}|from\s+{module}', source_code):
                issues.append(f"Dangerous module import detected: {module}")
        
        # Check for file operations
        if re.search(r'open\s*\(|file\s*\(', source_code):
            issues.append("File operation detected")
        
        return issues
    
    @staticmethod
    def analyze_mcp_structure(source_code: str) -> Dict[str, Any]:
        """Analyze code structure for MCP components"""
        result = {
            "has_fastmcp_import": False,
            "has_fastmcp_instance": False,
            "mcp_instance_name": None,
            "has_tools": False,
            "has_resources": False,
            "has_prompts": False,
            "tool_functions": [],
            "resource_functions": [],
            "prompt_functions": []
        }
        
        try:
            tree = ast.parse(source_code)
            
            # Check imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and 'fastmcp' in node.module:
                        result["has_fastmcp_import"] = True
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if 'fastmcp' in alias.name.lower():
                            result["has_fastmcp_import"] = True
            
            # Check for FastMCP instance creation
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    if isinstance(node.value, ast.Call):
                        if (isinstance(node.value.func, ast.Name) and 
                            node.value.func.id == 'FastMCP'):
                            result["has_fastmcp_instance"] = True
                            if node.targets and isinstance(node.targets[0], ast.Name):
                                result["mcp_instance_name"] = node.targets[0].id
            
            # Check for decorated functions (tools, resources, prompts)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        decorator_name = ""
                        if isinstance(decorator, ast.Attribute):
                            decorator_name = decorator.attr
                        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            decorator_name = decorator.func.attr
                        
                        if decorator_name == "tool":
                            result["has_tools"] = True
                            result["tool_functions"].append(node.name)
                        elif decorator_name == "resource":
                            result["has_resources"] = True
                            result["resource_functions"].append(node.name)
                        elif decorator_name == "prompt":
                            result["has_prompts"] = True
                            result["prompt_functions"].append(node.name)
        
        except Exception:
            pass
        
        return result
    
    @staticmethod
    def validate_execution(source_code: str) -> Tuple[bool, str, Any]:
        """Safely test if code can be executed and creates valid MCP instance"""
        try:
            # Create safe execution environment
            safe_globals = {'FastMCP': FastMCP}
            
            # Execute the code
            exec(source_code, safe_globals)
            
            # Look for FastMCP instance
            mcp_instance = None
            for var_name, var_value in safe_globals.items():
                if isinstance(var_value, FastMCP):
                    mcp_instance = var_value
                    break
            
            if mcp_instance:
                return True, "Valid MCP instance created", mcp_instance
            else:
                return False, "No FastMCP instance found after execution", None
                
        except Exception as e:
            return False, f"Execution error: {str(e)}", None


async def verify_mcp_code_handler(request):
    """Verify if provided code is valid MCP server code"""
    try:
        body = await request.json()
        source_code = body.get('source_code', '').strip()
        validation_level = body.get('validation_level', 'basic')
        
        if not source_code:
            return JSONResponse({
                "status": "error",
                "message": "source_code is required"
            }, status_code=400)
        
        # Initialize validation results
        validation_results = {
            "syntax_valid": False,
            "has_fastmcp_instance": False,
            "has_valid_tools": False,
            "security_issues": [],
            "structure_analysis": {},
            "execution_valid": False,
            "errors": []
        }
        
        # 1. Syntax validation
        syntax_valid, syntax_error = MCPCodeValidator.validate_syntax(source_code)
        validation_results["syntax_valid"] = syntax_valid
        if not syntax_valid:
            validation_results["errors"].append(syntax_error)
        
        # 2. Security checks
        security_issues = MCPCodeValidator.check_security(source_code)
        validation_results["security_issues"] = security_issues
        
        # 3. Structure analysis
        structure = MCPCodeValidator.analyze_mcp_structure(source_code)
        validation_results["structure_analysis"] = structure
        validation_results["has_fastmcp_instance"] = structure["has_fastmcp_instance"]
        validation_results["has_valid_tools"] = structure["has_tools"]
        
        # 4. Execution validation (if requested and safe)
        if validation_level == "full" and syntax_valid and not security_issues:
            exec_valid, exec_message, mcp_instance = MCPCodeValidator.validate_execution(source_code)
            validation_results["execution_valid"] = exec_valid
            if not exec_valid:
                validation_results["errors"].append(exec_message)
        
        # Determine overall validity
        is_valid = (
            syntax_valid and
            not security_issues and
            structure["has_fastmcp_instance"] and
            (validation_level == "basic" or validation_results["execution_valid"])
        )
        
        return JSONResponse({
            "status": "success",
            "is_valid": is_valid,
            "validation_results": validation_results
        })
        
    except json.JSONDecodeError:
        return JSONResponse({
            "status": "error",
            "message": "Invalid JSON in request body"
        }, status_code=400)
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Validation error: {str(e)}"
        }, status_code=500)


# Router setup
router = Router([
    Route("/", verify_mcp_code_handler, methods=["POST"])
])