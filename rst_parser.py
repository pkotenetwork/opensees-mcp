"""
RST Document Parser for OpenSeesPy and OPSVIS documentation.
Extracts:
- Document Titles & Breadcrumbs
- Section Headings
- API Signatures (.. function::, .. class::, .. autofunction::, etc.)
- Parameters & Arguments
- Descriptions & Notes
- Python code examples and blocks
- Intelligent section-based chunking
"""
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Tuple

UNDERLINE_CHARS = set("=-~^\"*#`:")

# Cache for AST-extracted python function signatures and docstrings
_PYTHON_FUNCTIONS_CACHE: Dict[str, Dict[str, Tuple[str, str, str]]] = {}

def get_python_functions_from_dir(py_dir: Path) -> Dict[str, Tuple[str, str, str]]:
    """
    Parses Python source files using AST to extract (signature, docstring, parameters)
    without needing to import the module or load external C/C++ DLLs.
    """
    cache_key = str(py_dir.resolve())
    if cache_key in _PYTHON_FUNCTIONS_CACHE:
        return _PYTHON_FUNCTIONS_CACHE[cache_key]

    fn_map: Dict[str, Tuple[str, str, str]] = {}
    if not py_dir.exists():
        return fn_map

    for py_file in py_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                fn_name = node.name
                doc = ast.get_docstring(node) or ""
                # Construct signature
                pos_args = []
                defaults = [None] * (len(node.args.args) - len(node.args.defaults)) + list(node.args.defaults)
                for arg, default in zip(node.args.args, defaults):
                    if default is None:
                        pos_args.append(arg.arg)
                    else:
                        try:
                            default_val = ast.unparse(default)
                        except Exception:
                            default_val = "..."
                        pos_args.append(f"{arg.arg}={default_val}")

                signature = f"{fn_name}({', '.join(pos_args)})"

                # Extract parameter section from docstring if present
                params = ""
                if "Args:" in doc or "Parameters" in doc:
                    param_lines = []
                    capture = False
                    for line in doc.splitlines():
                        if "Args:" in line or "Parameters" in line:
                            capture = True
                            continue
                        if capture:
                            if line.strip().startswith(("Returns:", "Usage:", "Notes:", "Examples:", "Yields:")):
                                break
                            if line.strip():
                                param_lines.append(line.strip())
                    params = "\n".join(param_lines).strip()

                fn_map[fn_name] = (signature, doc, params)

    _PYTHON_FUNCTIONS_CACHE[cache_key] = fn_map
    return fn_map

@dataclass
class DocChunk:
    chunk_id: str
    repo: str
    file_path: str
    doc_title: str
    section_title: str
    command_name: str
    signature: str
    parameters: str
    content: str
    code_blocks: str
    breadcrumbs: str
    token_estimate: int

def clean_inline_rst(text: str) -> str:
    """Removes RST roles and inline markup to produce clean, readable text."""
    if not text:
        return ""
    # Remove :role:`content` -> content
    text = re.sub(r":[a-zA-Z0-9_-]+:`([^`]+)`", r"\1", text)
    # Remove `content <url>`_ -> content
    text = re.sub(r"`([^`<]+)\s*<[^>]+>`_", r"\1", text)
    # Remove :doc:`target` or `target`_
    text = re.sub(r"`([^`]+)`_?", r"\1", text)
    # Clean up double backticks ``code`` -> code
    text = re.sub(r"``([^`]+)``", r"\1", text)
    return text.strip()

def extract_signature_and_command(line: str) -> tuple[str, str]:
    """
    Extracts signature and primary command/function name from a Sphinx directive:
    e.g., '.. function:: model('basic', '-ndm', ndm, ...)'
    returns ('model('basic', ...)', 'model')
    """
    # Match .. directive:: signature
    match = re.match(r"^\.\.\s+(?:function|autofunction|class|method|module|cmd)::\s*(.+)$", line.strip())
    if match:
        sig = match.group(1).strip()
        # Find command name
        cmd_match = re.match(r"^([a-zA-Z0-9_]+)", sig)
        cmd_name = cmd_match.group(1) if cmd_match else ""
        return sig, cmd_name
    return "", ""

class RSTParser:
    @staticmethod
    def parse_file(file_path: Path, repo: str) -> List[DocChunk]:
        """Parses an RST file into one or more structured DocChunks."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        lines = content.splitlines()
        if not lines:
            return []

        # Determine breadcrumbs from path
        rel_parts = file_path.parent.parts
        # Extract folder names as breadcrumbs
        breadcrumbs = " > ".join(p for p in file_path.parts if p not in ["..", "."])

        # 1. First pass: find document title
        doc_title = file_path.stem.replace("_", " ").title()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith(".."):
                continue
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if len(next_line) >= 3 and len(next_line) >= len(stripped):
                    if set(next_line).issubset(UNDERLINE_CHARS) and len(set(next_line)) == 1:
                        doc_title = stripped
                        break

        # 2. Slice into sections or logical blocks
        chunks: List[DocChunk] = []
        current_section = doc_title
        current_sig = ""
        current_cmd = ""
        current_content_lines: List[str] = []
        code_blocks: List[str] = []
        parameters_lines: List[str] = []

        in_code_block = False
        code_indent = 0
        current_code_lines: List[str] = []

        # If AST python source files are available in opsvis-master/opsvis, resolve autofunction
        # Look for opsvis directory in project root
        opsvis_source_candidates = [
            file_path.parents[2] / "opsvis-master" / "opsvis",
            file_path.parents[1] / "opsvis-master" / "opsvis",
            file_path.parents[2] / "opsvis",
        ]
        opsvis_source_dir = next((p for p in opsvis_source_candidates if p.exists() and p.is_dir()), None)
        py_func_map = get_python_functions_from_dir(opsvis_source_dir) if opsvis_source_dir else {}

        def flush_chunk():
            nonlocal current_content_lines, code_blocks, parameters_lines, current_sig, current_cmd
            content_str = "\n".join(current_content_lines).strip()
            if not content_str and not current_sig and not code_blocks:
                return

            # If no command found yet, look inside the section or file name
            cmd_name = current_cmd
            if not cmd_name:
                candidate = current_section.split()[0].strip()
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", candidate):
                    cmd_name = candidate
                elif re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", file_path.stem):
                    cmd_name = file_path.stem

            # Check if this command can be enriched from AST docstrings/signatures
            if cmd_name in py_func_map:
                ast_sig, ast_doc, ast_params = py_func_map[cmd_name]
                if not current_sig or "(" not in current_sig:
                    current_sig = ast_sig
                if not parameters_lines and ast_params:
                    parameters_lines.append(ast_params)
                if not content_str or len(content_str) < 50:
                    content_str = f"{content_str}\n\n{ast_doc}".strip()

            code_str = "\n\n".join(code_blocks).strip()
            param_str = "\n".join(parameters_lines).strip()

            combined_text = f"{doc_title} {current_section} {current_sig} {content_str} {param_str} {code_str}"
            token_est = max(1, len(combined_text.split()))

            chunk_idx = len(chunks) + 1
            chunk_id = f"{repo}:{file_path.stem}:{chunk_idx}"

            chunk = DocChunk(
                chunk_id=chunk_id,
                repo=repo,
                file_path=str(file_path),
                doc_title=doc_title,
                section_title=current_section,
                command_name=cmd_name,
                signature=current_sig,
                parameters=param_str,
                content=content_str,
                code_blocks=code_str,
                breadcrumbs=breadcrumbs,
                token_estimate=token_est
            )
            chunks.append(chunk)

            # Reset section accumulation
            current_content_lines = []
            code_blocks = []
            parameters_lines = []

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            stripped = line.strip()

            # Handle code block accumulation
            if in_code_block:
                if not stripped:
                    current_code_lines.append(line)
                    i += 1
                    continue
                indent = len(line) - len(line.lstrip())
                if indent >= code_indent:
                    current_code_lines.append(line)
                    i += 1
                    continue
                else:
                    # End of code block
                    code_blocks.append("\n".join(current_code_lines).strip())
                    current_code_lines = []
                    in_code_block = False

            # Check for section header (line followed by underline)
            if stripped and not stripped.startswith("..") and i + 1 < n:
                next_line = lines[i + 1].strip()
                if len(next_line) >= 3 and len(next_line) >= len(stripped):
                    if set(next_line).issubset(UNDERLINE_CHARS) and len(set(next_line)) == 1:
                        # Flush current section before starting a new one
                        if current_content_lines or current_sig:
                            flush_chunk()
                        current_section = stripped
                        i += 2
                        continue

            # Check for Sphinx signature directive
            if stripped.startswith(".. ") and ("::" in stripped):
                sig, cmd = extract_signature_and_command(stripped)
                if sig:
                    if current_content_lines or (current_sig and current_sig != sig):
                        flush_chunk()
                    current_sig = sig
                    current_cmd = cmd
                    i += 1
                    continue

            # Check for code-block directive or literal block (::)
            if stripped.startswith(".. code-block::") or stripped.startswith(".. code::") or stripped == "::" or line.endswith("::"):
                in_code_block = True
                code_indent = len(line) - len(line.lstrip()) + 3
                current_code_lines = []
                current_content_lines.append(line)
                i += 1
                continue

            # Check for parameter table lines (e.g., ``param`` |type| description)
            if "``" in stripped and ("|int|" in stripped or "|float|" in stripped or "|str|" in stripped or "|list|" in stripped):
                parameters_lines.append(clean_inline_rst(stripped))

            current_content_lines.append(line)
            i += 1

        if in_code_block and current_code_lines:
            code_blocks.append("\n".join(current_code_lines).strip())

        flush_chunk()

        # If file was completely empty or had no chunks, generate at least one chunk for filename reference
        if not chunks:
            chunk_id = f"{repo}:{file_path.stem}:1"
            chunks.append(DocChunk(
                chunk_id=chunk_id,
                repo=repo,
                file_path=str(file_path),
                doc_title=doc_title,
                section_title=doc_title,
                command_name=file_path.stem,
                signature="",
                parameters="",
                content=content[:1000],
                code_blocks="",
                breadcrumbs=breadcrumbs,
                token_estimate=max(1, len(content[:1000].split()))
            ))

        return chunks

