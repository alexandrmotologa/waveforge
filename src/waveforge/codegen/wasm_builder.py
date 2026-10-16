"""Compiler driver for compiling generated C headers to native executables or WebAssembly."""

from __future__ import annotations
import os
import shutil
import subprocess
from typing import Tuple, Optional


class CCompilerDriver:
    """Invokes clang or gcc to compile and verify WaveForge generated C synthesis code."""

    @staticmethod
    def find_c_compiler() -> Optional[str]:
        """Locate clang or gcc on the system PATH."""
        for c in ["clang", "gcc"]:
            path = shutil.which(c)
            if path:
                return path
        return None

    @classmethod
    def compile_standalone_c(
        cls,
        c_code_or_path: str,
        output_exe: str,
        compiler: Optional[str] = None,
        extra_flags: Optional[list[str]] = None,
    ) -> Tuple[bool, str]:
        """Compile generated C header with standalone flag into native executable."""
        comp = compiler or cls.find_c_compiler()
        if not comp:
            return False, "No C compiler (clang or gcc) found on system PATH."

        # If c_code_or_path is raw C code, write to temp file
        temp_src = None
        if os.path.exists(c_code_or_path):
            src_file = c_code_or_path
        else:
            temp_src = output_exe + ".c"
            with open(temp_src, "w", encoding="utf-8") as f:
                f.write(c_code_or_path)
            src_file = temp_src

        cmd = [
            comp,
            "-O3",
            "-DWAVEFORGE_STANDALONE",
            src_file,
            "-o",
            output_exe,
            "-lm",
        ]
        if extra_flags:
            cmd.extend(extra_flags)

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return True, output_exe
            else:
                return False, f"Compilation failed (code {res.returncode}):\n{res.stderr}"
        except Exception as e:
            return False, f"Subprocess error: {str(e)}"
        finally:
            if temp_src and os.path.exists(temp_src):
                try:
                    os.remove(temp_src)
                except OSError:
                    pass

    @classmethod
    def run_standalone_exe(cls, exe_path: str, cwd: Optional[str] = None) -> Tuple[int, str]:
        """Execute compiled native synth binary."""
        try:
            res = subprocess.run(
                [exe_path],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=10,
                check=False,
            )
            return res.returncode, res.stdout + res.stderr
        except Exception as e:
            return -1, str(e)
