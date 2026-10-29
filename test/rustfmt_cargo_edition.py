#!/usr/bin/env python3
"""Run with Python 3, Neovim, rustup, and a Rust toolchain supporting 2024."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SOURCE = "use  tokio::time::{ Duration,sleep };\n"


class CargoEditionFormatting(unittest.TestCase):
    def test_cargo_editions(self):
        toolchain = subprocess.check_output(
            ["rustup", "show", "active-toolchain"], text=True
        ).split()[0]
        editor_env = os.environ.copy()
        editor_env.pop("RUSTUP_TOOLCHAIN", None)
        cases = [
            ("edition-" + e, 'edition = "' + e + '"', "max_width = 120\n", None, e)
            for e in ("2015", "2018", "2021", "2024")
        ]
        cases += [
            ("old-config", 'edition = "2024"', 'edition = "2021"\n', None, "2024"),
            ("no-config", 'edition = "2024"', None, None, "2024"),
            ("cargo-default", "", "max_width = 120\n", None, "2015"),
            ("inherited edition", "edition.workspace = true", "max_width = 120\n", "2024", "2024"),
            ("member-edition", 'edition = "2021"', None, "2024", "2021"),
        ]
        with tempfile.TemporaryDirectory(prefix="rustvim-format-") as tmp:
            root = Path(tmp)
            init = root / "init.vim"
            init.write_text(
                "execute 'set rtp^=' . fnameescape('" + str(PLUGIN_ROOT) + "')\n"
                "filetype plugin on\nlet g:rustfmt_autosave = 1\n"
            )
            for name, edition, config, workspace_edition, expected_edition in cases:
                with self.subTest(name=name):
                    project = root / name
                    project.mkdir()
                    (project / "rust-toolchain.toml").write_text(
                        '[toolchain]\nchannel = "' + toolchain + '"\n'
                    )
                    if workspace_edition:
                        (project / "Cargo.toml").write_text(
                            '[workspace]\nmembers = ["member"]\n'
                            '[workspace.package]\nedition = "' + workspace_edition + '"\n'
                        )
                        project = project / "member"
                        project.mkdir()
                    manifest = project / "Cargo.toml"
                    manifest.write_text(
                        '[package]\nname = "fixture"\nversion = "0.1.0"\n' + edition + "\n"
                    )
                    if config is not None:
                        (project / ".rustfmt.toml").write_text(config)
                    source = project / "src" / "lib.rs"
                    source.parent.mkdir()
                    source.write_text(SOURCE)
                    subprocess.run(
                        ["cargo", "fmt", "--manifest-path", str(manifest)],
                        cwd=project, env=editor_env, check=True, capture_output=True,
                    )
                    expected = source.read_text()
                    source.write_text(SOURCE)
                    manual = project / "manual.txt"
                    command = project / "command.txt"
                    result = subprocess.run(
                        ["nvim", "--headless", "-i", "NONE", "-u", str(init), str(source),
                         "+RustFmt", "+call writefile(getline(1, '$'), '" + str(manual) + "')",
                         "+call writefile([rustfmt#Cmd()], '" + str(command) + "')",
                         "+call setline(1, '" + SOURCE.strip() + "')",
                         "+write", "+write", "+qa!"],
                        cwd=root, env=editor_env, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(manual.read_text(), expected, result.stderr)
                    self.assertEqual(source.read_text(), expected, result.stderr)
                    self.assertIn("--edition '" + expected_edition + "'", command.read_text())


if __name__ == "__main__":
    unittest.main()
