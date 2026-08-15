@echo off
REM Pre-commit hook: Constitutional Validation
REM Runs the ConstitutionValidator against staged files.
REM Skip with: git commit --no-verify

echo Running Constitutional Validation...

REM Find the constitutional_architecture root
set "REPO_ROOT=%~dp0.."
set "CA_DIR=%REPO_ROOT%\constitutional_architecture"

if not exist "%CA_DIR%" (
    echo WARNING: constitutional_architecture directory not found
    exit /b 0
)

cd /d "%CA_DIR%"

python -m validators.run_precommit
if %ERRORLEVEL% neq 0 (
    echo.
    echo CONSTITUTIONAL VIOLATION DETECTED.
    echo Commit rejected. Review violations above and fix before committing.
    echo Use 'git commit --no-verify' to bypass (not recommended).
    exit /b 1
)

exit /b 0
