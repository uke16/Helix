"""
Symbol Extractor for Documentation as Code.

ADR-019: Extracts symbol information from Python source files using AST
parsing. This provides the ground truth for documentation validation.
"""

import ast
from pathlib import Path
from typing import Union

from helix.docs.schema import ExtractedSymbol, SymbolKind


class SymbolExtractor:
    """Extracts symbol information from Python source files."""

    def __init__(self, project_root: Path):
        """Initialize the extractor.

        Args:
            project_root: Root directory of the project.
        """
        self.root = project_root
        self.src_root = project_root / "src"

    def extract_module(self, module_path: str) -> ExtractedSymbol | None:
        """Extract all symbols from a module.

        Args:
            module_path: Dotted module path (e.g., 'helix.debug.stream_parser').

        Returns:
            ExtractedSymbol for the module, or None if not found.
        """
        file_path = self._module_to_path(module_path)
        if not file_path or not file_path.exists():
            return None

        with open(file_path) as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return None

        return self._extract_from_ast(tree, file_path, module_path)

    def extract_class(self, module: str, class_name: str) -> ExtractedSymbol | None:
        """Extract a specific class from a module.

        Args:
            module: Dotted module path.
            class_name: Name of the class to extract.

        Returns:
            ExtractedSymbol for the class, or None if not found.
        """
        module_info = self.extract_module(module)
        if not module_info:
            return None

        for child in module_info.children:
            if child.name == class_name and child.kind == SymbolKind.CLASS:
                return child
        return None

    def extract_function(self, module: str, func_name: str) -> ExtractedSymbol | None:
        """Extract a specific function from a module.

        Args:
            module: Dotted module path.
            func_name: Name of the function to extract.

        Returns:
            ExtractedSymbol for the function, or None if not found.
        """
        module_info = self.extract_module(module)
        if not module_info:
            return None

        for child in module_info.children:
            if child.name == func_name and child.kind == SymbolKind.FUNCTION:
                return child
        return None

    def extract_method(
        self, module: str, class_name: str, method: str
    ) -> ExtractedSymbol | None:
        """Extract a specific method from a class.

        Args:
            module: Dotted module path.
            class_name: Name of the class.
            method: Name of the method to extract.

        Returns:
            ExtractedSymbol for the method, or None if not found.
        """
        class_info = self.extract_class(module, class_name)
        if not class_info:
            return None

        for child in class_info.children:
            if child.name == method:
                return child
        return None

    def _module_to_path(self, module_path: str) -> Path | None:
        """Convert a dotted module path to a file path.

        Args:
            module_path: Dotted module path.

        Returns:
            Path to the Python file, or None if not determinable.
        """
        parts = module_path.split(".")

        # Try src/module/path.py
        file_path = self.src_root / "/".join(parts[:-1]) / f"{parts[-1]}.py"
        if file_path.exists():
            return file_path

        # Try src/module/path/__init__.py
        init_path = self.src_root / "/".join(parts) / "__init__.py"
        if init_path.exists():
            return init_path

        # Try without src prefix (for root-level modules)
        file_path = self.root / "/".join(parts[:-1]) / f"{parts[-1]}.py"
        if file_path.exists():
            return file_path

        return None

    def _extract_from_ast(
        self, tree: ast.Module, file: Path, module: str
    ) -> ExtractedSymbol:
        """Extract symbols from AST.

        Args:
            tree: Parsed AST module.
            file: Source file path.
            module: Module name.

        Returns:
            ExtractedSymbol for the module.
        """
        children = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                children.append(self._extract_class(node, file))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                children.append(self._extract_function(node, file))

        return ExtractedSymbol(
            name=module.split(".")[-1],
            kind=SymbolKind.MODULE,
            file=file,
            line=1,
            docstring=ast.get_docstring(tree),
            signature=None,
            children=children,
            decorators=[],
            bases=[],
        )

    def _extract_class(self, node: ast.ClassDef, file: Path) -> ExtractedSymbol:
        """Extract class information.

        Args:
            node: AST class definition node.
            file: Source file path.

        Returns:
            ExtractedSymbol for the class.
        """
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._extract_function(item, file)
                # Override kind to METHOD for class members
                method = ExtractedSymbol(
                    name=method.name,
                    kind=SymbolKind.METHOD,
                    file=method.file,
                    line=method.line,
                    docstring=method.docstring,
                    signature=method.signature,
                    children=method.children,
                    decorators=method.decorators,
                    bases=method.bases,
                )
                methods.append(method)

        return ExtractedSymbol(
            name=node.name,
            kind=SymbolKind.CLASS,
            file=file,
            line=node.lineno,
            docstring=ast.get_docstring(node),
            signature=None,
            children=methods,
            decorators=[self._decorator_name(d) for d in node.decorator_list],
            bases=[self._base_name(b) for b in node.bases],
        )

    def _extract_function(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], file: Path
    ) -> ExtractedSymbol:
        """Extract function/method information.

        Args:
            node: AST function definition node.
            file: Source file path.

        Returns:
            ExtractedSymbol for the function.
        """
        return ExtractedSymbol(
            name=node.name,
            kind=SymbolKind.FUNCTION,
            file=file,
            line=node.lineno,
            docstring=ast.get_docstring(node),
            signature=self._get_signature(node),
            children=[],
            decorators=[self._decorator_name(d) for d in node.decorator_list],
            bases=[],
        )

    def _get_signature(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> str:
        """Extract function signature.

        Args:
            node: AST function definition node.

        Returns:
            String representation of the signature.
        """
        args = []

        # Handle positional-only args (before /)
        for arg in node.args.posonlyargs:
            args.append(self._format_arg(arg))

        # Handle regular args
        num_defaults = len(node.args.defaults)
        num_args = len(node.args.args)
        non_default_count = num_args - num_defaults

        for i, arg in enumerate(node.args.args):
            arg_str = self._format_arg(arg)
            # Add default value if present
            if i >= non_default_count:
                default_idx = i - non_default_count
                try:
                    default = ast.unparse(node.args.defaults[default_idx])
                    arg_str += f" = {default}"
                except Exception:
                    pass
            args.append(arg_str)

        # Handle *args
        if node.args.vararg:
            args.append(f"*{self._format_arg(node.args.vararg)}")

        # Handle keyword-only args
        kw_defaults = node.args.kw_defaults
        for i, arg in enumerate(node.args.kwonlyargs):
            arg_str = self._format_arg(arg)
            if kw_defaults[i] is not None:
                try:
                    default = ast.unparse(kw_defaults[i])
                    arg_str += f" = {default}"
                except Exception:
                    pass
            args.append(arg_str)

        # Handle **kwargs
        if node.args.kwarg:
            args.append(f"**{self._format_arg(node.args.kwarg)}")

        sig = f"({', '.join(args)})"

        # Add return type
        if node.returns:
            try:
                sig += f" -> {ast.unparse(node.returns)}"
            except Exception:
                pass

        return sig

    def _format_arg(self, arg: ast.arg) -> str:
        """Format a function argument.

        Args:
            arg: AST argument node.

        Returns:
            String representation of the argument.
        """
        arg_str = arg.arg
        if arg.annotation:
            try:
                arg_str += f": {ast.unparse(arg.annotation)}"
            except Exception:
                pass
        return arg_str

    def _decorator_name(self, node: ast.expr) -> str:
        """Extract decorator name.

        Args:
            node: AST expression node for decorator.

        Returns:
            String representation of the decorator.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._decorator_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._decorator_name(node.func)
        else:
            try:
                return ast.unparse(node)
            except Exception:
                return "<unknown>"

    def _base_name(self, node: ast.expr) -> str:
        """Extract base class name.

        Args:
            node: AST expression node for base class.

        Returns:
            String representation of the base class.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._base_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            # Handle Generic types like List[str]
            try:
                return ast.unparse(node)
            except Exception:
                return "<generic>"
        else:
            try:
                return ast.unparse(node)
            except Exception:
                return "<unknown>"
