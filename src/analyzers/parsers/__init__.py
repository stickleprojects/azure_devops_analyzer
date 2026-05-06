"""
Manifest file parsers for dependency extraction.

This module provides parsers for various package manager manifest files
across different ecosystems (Python, Node.js, Java, .NET, Go, Ruby, Rust).
"""

from src.analyzers.parsers.base import ManifestParser, ParserRegistry

# Import all parsers to register them
from src.analyzers.parsers.python_parser import PythonParser
from src.analyzers.parsers.node_js_parser import NodeJsParser
from src.analyzers.parsers.java_parser import JavaParser
from src.analyzers.parsers.dot_net_parser import DotNetParser
from src.analyzers.parsers.go_parser import GoParser
from src.analyzers.parsers.ruby_parser import RubyParser
from src.analyzers.parsers.rust_parser import RustParser

__all__ = [
    "ManifestParser",
    "ParserRegistry",
    "PythonParser",
    "NodeJsParser",
    "JavaParser",
    "DotNetParser",
    "GoParser",
    "RubyParser",
    "RustParser",
]
