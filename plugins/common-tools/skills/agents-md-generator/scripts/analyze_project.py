#!/usr/bin/env python3
"""Analyze a project/library and print a JSON fact sheet used to generate AGENTS.md.

Usage:
    analyze_project.py [PROJECT_PATH]

Detects (read-only, stdlib only): build systems and commands, language/runtime
versions, monorepo modules, test layout, CI pipelines and the commands they run,
code-style configs, docs and existing agent-instruction files. Output is a single
JSON object on stdout.

Every command carries a provenance, so the caller knows what it may write down as is:
    "declared"     - read from a file the project owns (package.json scripts,
                     Makefile targets, a CI step): safe to list.
    "conventional" - the usual command of that build tool, NOT stated by the
                     project: check it (or ask) before listing it.
"""

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

MAX_MAKE_TARGETS = 30
MAX_CI_COMMANDS = 20


def cmd(command, source):
    return {"command": command, "source": source}


def exists(root, *parts):
    return os.path.exists(os.path.join(root, *parts))


def read(root, *parts):
    try:
        with open(os.path.join(root, *parts), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def git_info(root):
    info = {}
    def run(*args):
        try:
            out = subprocess.run(["git", "-C", root, *args], capture_output=True,
                                 text=True, timeout=10)
            return out.stdout.strip() if out.returncode == 0 else None
        except Exception:
            return None
    if run("rev-parse", "--is-inside-work-tree") != "true":
        return None
    info["remote"] = run("remote", "get-url", "origin")
    info["current_branch"] = run("symbolic-ref", "--short", "HEAD")
    info["last_tag"] = run("describe", "--tags", "--abbrev=0")
    return info


def strip_ns(tag):
    return tag.split("}", 1)[-1]


def analyze_maven(root):
    text = read(root, "pom.xml")
    if text is None:
        return None
    facts = {"tool": "maven", "wrapper": exists(root, "mvnw")}
    try:
        tree = ET.fromstring(text)
    except ET.ParseError:
        return facts
    def child(elem, name):
        for c in elem:
            if strip_ns(c.tag) == name:
                return c
        return None
    def text_of(elem, name):
        c = child(elem, name)
        return c.text.strip() if c is not None and c.text else None
    facts["artifactId"] = text_of(tree, "artifactId")
    facts["groupId"] = text_of(tree, "groupId")
    facts["version"] = text_of(tree, "version")
    facts["name"] = text_of(tree, "name")
    facts["description"] = text_of(tree, "description")
    facts["license"] = [text_of(l, "name") for l in child(tree, "licenses")] \
        if child(tree, "licenses") is not None else None
    facts["packaging"] = text_of(tree, "packaging") or "jar"
    parent = child(tree, "parent")
    if parent is not None:
        facts["parent"] = {
            "groupId": text_of(parent, "groupId"),
            "artifactId": text_of(parent, "artifactId"),
            "version": text_of(parent, "version"),
        }
    modules = child(tree, "modules")
    if modules is not None:
        facts["modules"] = [m.text.strip() for m in modules if m.text]
    props = child(tree, "properties")
    if props is not None:
        wanted = ("maven.compiler.source", "maven.compiler.target",
                  "maven.compiler.release", "java.version")
        facts["properties"] = {strip_ns(p.tag): (p.text or "").strip()
                               for p in props if strip_ns(p.tag) in wanted}
    mvn = "./mvnw" if facts["wrapper"] else "mvn"
    facts["commands"] = {"build": cmd(f"{mvn} clean install", "conventional"),
                         "test": cmd(f"{mvn} test", "conventional"),
                         "package": cmd(f"{mvn} package", "conventional")}
    return facts


def analyze_gradle(root):
    build = "build.gradle" if exists(root, "build.gradle") else (
        "build.gradle.kts" if exists(root, "build.gradle.kts") else None)
    if build is None:
        return None
    gradle = "./gradlew" if exists(root, "gradlew") else "gradle"
    facts = {"tool": "gradle", "build_file": build, "wrapper": gradle == "./gradlew",
             "commands": {"build": cmd(f"{gradle} build", "conventional"),
                          "test": cmd(f"{gradle} test", "conventional")}}
    settings = read(root, "settings.gradle") or read(root, "settings.gradle.kts")
    if settings:
        facts["modules"] = re.findall(r"include\s*[('\"]+\s*:?([\w:-]+)", settings)
    return facts


def analyze_node(root):
    text = read(root, "package.json")
    if text is None:
        return None
    facts = {"tool": "node"}
    try:
        pkg = json.loads(text)
    except json.JSONDecodeError:
        return facts
    pm = "npm"
    if exists(root, "pnpm-lock.yaml"):
        pm = "pnpm"
    elif exists(root, "yarn.lock"):
        pm = "yarn"
    elif exists(root, "bun.lockb") or exists(root, "bun.lock"):
        pm = "bun"
    if isinstance(pkg.get("packageManager"), str):
        pm = pkg["packageManager"].split("@", 1)[0]
    facts.update({
        "package_manager": pm,
        "name": pkg.get("name"),
        "version": pkg.get("version"),
        "description": pkg.get("description"),
        "scripts": {k: cmd(f"{pm} run {k}", "declared") for k in pkg.get("scripts", {})},
        "script_bodies": pkg.get("scripts", {}),
        "engines": pkg.get("engines"),
        "workspaces": pkg.get("workspaces"),
        "typescript": exists(root, "tsconfig.json"),
    })
    return facts


def analyze_python(root):
    facts = None
    text = read(root, "pyproject.toml")
    if text is not None:
        facts = {"tool": "python", "config": "pyproject.toml"}
        try:
            import tomllib
            data = tomllib.loads(text)
            proj = data.get("project", {})
            facts["name"] = proj.get("name")
            facts["version"] = proj.get("version")
            facts["description"] = proj.get("description")
            facts["requires_python"] = proj.get("requires-python")
            tools = data.get("tool", {})
            facts["managers"] = [t for t in ("poetry", "uv", "hatch", "pdm", "setuptools")
                                 if t in tools]
            facts["linters"] = [t for t in ("ruff", "black", "isort", "mypy", "pytest")
                                if t in tools]
        except Exception:
            pass
    elif exists(root, "setup.py") or exists(root, "setup.cfg"):
        facts = {"tool": "python", "config": "setup.py/setup.cfg"}
    if facts is not None:
        facts["has_requirements_txt"] = exists(root, "requirements.txt")
        facts["has_tox"] = exists(root, "tox.ini")
        if text is not None and "name" not in facts:
            facts["note"] = "pyproject.toml not parsed (needs Python >= 3.11): read it directly"
        for lock, mgr in (("uv.lock", "uv"), ("poetry.lock", "poetry"), ("pdm.lock", "pdm")):
            if exists(root, lock):
                facts["lockfile"] = lock
                facts["manager_from_lock"] = mgr
    return facts


def analyze_make(root):
    text = read(root, "Makefile")
    if text is None:
        return None
    targets = re.findall(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", text, re.MULTILINE)
    targets = [t for t in dict.fromkeys(targets) if not t.startswith(".")]
    shown = targets[:MAX_MAKE_TARGETS]
    return {"tool": "make", "targets": {t: cmd(f"make {t}", "declared") for t in shown}}


def detect_ci(root):
    ci = {}
    wf_dir = os.path.join(root, ".github", "workflows")
    if os.path.isdir(wf_dir):
        ci["github_actions"] = sorted(
            f for f in os.listdir(wf_dir) if f.endswith((".yml", ".yaml")))
    for name, key in (("Jenkinsfile", "jenkins"), (".gitlab-ci.yml", "gitlab"),
                      (".travis.yml", "travis"), ("azure-pipelines.yml", "azure")):
        if exists(root, name):
            ci[key] = name
    return ci or None


def ci_commands(root):
    """Shell commands that CI really runs: GitHub Actions `run:` steps, Jenkins `sh` steps."""
    found = []
    wf_dir = os.path.join(root, ".github", "workflows")
    if os.path.isdir(wf_dir):
        for f in sorted(os.listdir(wf_dir)):
            if not f.endswith((".yml", ".yaml")):
                continue
            for line in (read(wf_dir, f) or "").splitlines():
                m = re.match(r"\s*-?\s*run:\s*(.+)$", line)
                if m and m.group(1).strip() not in ("|", ">", "|-", ">-"):
                    found.append({"file": f".github/workflows/{f}", "command": m.group(1).strip()})
    jf = read(root, "Jenkinsfile")
    if jf:
        for m in re.finditer(r"\bsh\s*(?:\(|\s)\s*['\"]{1,3}([^'\"\n]+)", jf):
            found.append({"file": "Jenkinsfile", "command": m.group(1).strip()})
    return found[:MAX_CI_COMMANDS] or None


def detect_runtime_pins(root):
    pins = {}
    for name in (".tool-versions", ".nvmrc", ".node-version", ".python-version",
                 ".java-version", ".sdkmanrc", "rust-toolchain.toml", "rust-toolchain"):
        text = read(root, name)
        if text is not None:
            pins[name] = text.strip().splitlines()[0] if text.strip() else ""
    return pins or None


def detect_style(root):
    found = []
    patterns = [".editorconfig", "checkstyle.xml", "pmd.xml", "spotbugs.xml",
                ".prettierrc", ".prettierrc.json", ".prettierrc.yml", "prettier.config.js",
                ".eslintrc", ".eslintrc.json", ".eslintrc.js", "eslint.config.js",
                "eslint.config.mjs", "biome.json", ".flake8", ".pylintrc",
                "ruff.toml", ".rustfmt.toml", ".clang-format", ".scalafmt.conf"]
    for p in patterns:
        if exists(root, p):
            found.append(p)
    return found or None


def detect_docs(root):
    docs = {}
    for name in ("README.md", "CHANGELOG.md", "LICENSE.md", "LICENSE",
                 "CONTRIBUTING.md", "CITATION.cff", "FUNDING.md"):
        if exists(root, name):
            docs[name] = True
    if os.path.isdir(os.path.join(root, "docs")):
        docs["docs_dir"] = True
    return docs or None


def detect_agent_files(root):
    found = {}
    for name in ("AGENTS.md", "CLAUDE.md", ".cursorrules", "GEMINI.md",
                 ".github/copilot-instructions.md", ".windsurfrules", "CONVENTIONS.md"):
        if exists(root, *name.split("/")):
            found[name] = True
    for d in (".kilo", ".claude", ".roo", ".cursor"):
        if os.path.isdir(os.path.join(root, d)):
            found[d + "/"] = True
    return found or None


def detect_tests(root):
    layout = []
    for d in ("src/test", "test", "tests", "__tests__", "spec"):
        if os.path.isdir(os.path.join(root, d)):
            layout.append(d)
    return layout or None


def detect_docker(root):
    found = [f for f in ("Dockerfile", "compose.yml", "compose.yaml",
                         "docker-compose.yml", "docker-compose.yaml", "docker")
             if exists(root, f)]
    return found or None


def top_level_layout(root):
    entries = []
    try:
        for e in sorted(os.listdir(root)):
            if e.startswith(".") or e in ("node_modules", "target", "build",
                                          "dist", "__pycache__", "venv", ".venv"):
                continue
            entries.append(e + "/" if os.path.isdir(os.path.join(root, e)) else e)
    except OSError:
        pass
    return entries


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    if not os.path.isdir(root):
        print(json.dumps({"error": f"not a directory: {root}"}))
        sys.exit(1)
    build_systems = [f for f in (analyze_maven(root), analyze_gradle(root),
                                 analyze_node(root), analyze_python(root),
                                 analyze_make(root)) if f]
    for name, tool, cmds in (
            ("Cargo.toml", "cargo", {"build": "cargo build", "test": "cargo test"}),
            ("go.mod", "go", {"build": "go build ./...", "test": "go test ./..."}),
            ("mix.exs", "mix", {"test": "mix test"}),
            ("Gemfile", "bundler", {}), ("composer.json", "composer", {})):
        if exists(root, name):
            build_systems.append({"tool": tool, "config": name,
                                  "commands": {k: cmd(v, "conventional") for k, v in cmds.items()}})
    result = {
        "root": root,
        "git": git_info(root),
        "build_systems": build_systems,
        "ci": detect_ci(root),
        "ci_commands": ci_commands(root),
        "runtime_pins": detect_runtime_pins(root),
        "code_style_configs": detect_style(root),
        "docs": detect_docs(root),
        "existing_agent_files": detect_agent_files(root),
        "test_layout": detect_tests(root),
        "docker": detect_docker(root),
        "top_level": top_level_layout(root),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
