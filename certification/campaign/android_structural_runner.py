"""Native Android structural execution.

Runs Gradle/APK/emulator checks for a STRUCTURAL backend without changing its
certification class or converting these checks into behavioral certification.
Every evidence record is bound to revision, plan, and repository hashes.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

from compiler.core.repository import GeneratedRepository, build_repository


@dataclass(frozen=True)
class AndroidStageEvidence:
    stage: str
    passed: bool
    command: tuple[str, ...]
    exit_code: int | None
    output_hash: str
    detail: str


@dataclass(frozen=True)
class AndroidStructuralExecution:
    backend_class: str
    revision_hash: str
    plan_hash: str
    candidate_hash: str
    apk_hash: str
    evidence: tuple[AndroidStageEvidence, ...]
    verdict: str = "STRUCTURAL_CHECKS_ONLY"

    @property
    def passed(self) -> bool:
        return bool(self.evidence) and all(item.passed for item in self.evidence)

    def to_dict(self) -> dict:
        return {
            "backend_class": self.backend_class,
            "revision_hash": self.revision_hash,
            "plan_hash": self.plan_hash,
            "candidate_hash": self.candidate_hash,
            "apk_hash": self.apk_hash,
            "verdict": self.verdict,
            "passed": self.passed,
            "evidence": [asdict(item) for item in self.evidence],
        }


class NativeAndroidStructuralRunner:
    """Execute real native checks; never returns a campaign CERTIFIED verdict."""

    def __init__(
        self,
        command_runner: Callable = subprocess.run,
        timeout_seconds: int = 1800,
    ) -> None:
        self._run = command_runner
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _write_candidate(repository: GeneratedRepository, root: Path) -> None:
        for relative, content in repository.files.items():
            if (
                not relative or "\x00" in relative or "\\" in relative
                or Path(relative).is_absolute()
                or ".." in Path(relative).parts
            ):
                raise ValueError(f"unsafe candidate path: {relative!r}")
            target = (root / relative).resolve()
            if root.resolve() not in target.parents:
                raise ValueError(f"candidate path escapes root: {relative!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def _command(
        self, stage: str, command: Sequence[str], cwd: Path
    ) -> AndroidStageEvidence:
        try:
            result = self._run(
                list(command), cwd=str(cwd), capture_output=True, text=True,
                timeout=self.timeout_seconds, check=False,
            )
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            output = stdout + "\n" + stderr
            code = result.returncode
            passed = code == 0
            detail = f"exit_code={code}; output_tail={output[-2000:]!r}"
        except subprocess.TimeoutExpired as exc:
            code, passed = None, False
            output = repr(exc)
            detail = f"timeout_after={self.timeout_seconds}s"
        except OSError as exc:
            code, passed = None, False
            output = repr(exc)
            detail = f"command_start_failed={type(exc).__name__}: {exc}"
        return AndroidStageEvidence(
            stage=stage, passed=passed, command=tuple(command), exit_code=code,
            output_hash=hashlib.sha256(output.encode("utf-8", errors="replace")).hexdigest(),
            detail=detail,
        )

    def execute(
        self,
        repository: GeneratedRepository,
        candidate_root: str | Path,
        revision_hash: str,
        plan_hash: str,
        require_emulator: bool = True,
    ) -> AndroidStructuralExecution:
        if not revision_hash or not plan_hash:
            raise ValueError("revision_hash and plan_hash are mandatory")
        canonical = build_repository(repository.files)
        if canonical.content_hash != repository.content_hash:
            raise ValueError("repository content hash does not match its files")
        root = Path(candidate_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._write_candidate(repository, root)

        evidence: list[AndroidStageEvidence] = []
        build = self._command(
            "gradle_build", ("gradle", ":app:assembleDebug", "--no-daemon"), root
        )
        evidence.append(build)
        apk_hash = ""
        apk_path = root / "app/build/outputs/apk/debug/app-debug.apk"
        if build.passed:
            if not apk_path.is_file():
                evidence.append(AndroidStageEvidence(
                    stage="apk_inspection", passed=False, command=(),
                    exit_code=None, output_hash=hashlib.sha256(b"missing-apk").hexdigest(),
                    detail="Gradle succeeded but expected debug APK is missing",
                ))
            else:
                apk_bytes = apk_path.read_bytes()
                apk_hash = hashlib.sha256(apk_bytes).hexdigest()
                try:
                    with zipfile.ZipFile(apk_path) as apk:
                        names = set(apk.namelist())
                        valid = (
                            "AndroidManifest.xml" in names
                            and any(n.startswith("classes") and n.endswith(".dex") for n in names)
                        )
                    detail = "APK ZIP, manifest, and DEX entries verified" if valid else "APK missing manifest or DEX"
                except (zipfile.BadZipFile, OSError) as exc:
                    valid, detail = False, f"APK inspection failed: {type(exc).__name__}: {exc}"
                evidence.append(AndroidStageEvidence(
                    stage="apk_inspection", passed=valid, command=(), exit_code=0 if valid else 1,
                    output_hash=hashlib.sha256(detail.encode()).hexdigest(), detail=detail,
                ))
        else:
            evidence.append(AndroidStageEvidence(
                stage="apk_inspection", passed=False, command=(), exit_code=None,
                output_hash=hashlib.sha256(b"build-not-passed").hexdigest(),
                detail="Skipped because Gradle build did not pass",
            ))

        if require_emulator and evidence[-1].passed:
            install = self._command("emulator_install", ("adb", "install", "-r", str(apk_path)), root)
            evidence.append(install)
            if install.passed:
                launch = self._command(
                    "emulator_launch",
                    ("adb", "shell", "am", "start", "-n", "generated.app/.MainActivity"),
                    root,
                )
                evidence.append(launch)
            else:
                evidence.append(AndroidStageEvidence(
                    stage="emulator_launch", passed=False, command=(), exit_code=None,
                    output_hash=hashlib.sha256(b"install-not-passed").hexdigest(),
                    detail="Skipped because APK installation did not pass",
                ))
        elif require_emulator:
            evidence.extend((
                AndroidStageEvidence(
                    stage="emulator_install", passed=False, command=(), exit_code=None,
                    output_hash=hashlib.sha256(b"apk-not-passed").hexdigest(),
                    detail="Skipped because APK build/inspection did not pass",
                ),
                AndroidStageEvidence(
                    stage="emulator_launch", passed=False, command=(), exit_code=None,
                    output_hash=hashlib.sha256(b"install-not-passed").hexdigest(),
                    detail="Skipped because APK installation did not pass",
                ),
            ))

        result = AndroidStructuralExecution(
            backend_class="structural", revision_hash=revision_hash,
            plan_hash=plan_hash, candidate_hash=repository.content_hash,
            apk_hash=apk_hash, evidence=tuple(evidence),
        )
        binding = result.to_dict()
        (root / "android-structural-evidence.json").write_text(
            json.dumps(binding, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        return result
