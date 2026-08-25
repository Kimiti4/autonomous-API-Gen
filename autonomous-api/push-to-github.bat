@echo off
echo ========================================
echo   Pushing to GitHub Repository
echo ========================================
echo.
echo Repository: Kimiti4/EvoAPI-Autonomous-Architecture-Engine
echo.
echo STEP 1: Create repository on GitHub first!
echo   - Go to: https://github.com/new
echo   - Name: EvoAPI-Autonomous-Architecture-Engine
echo   - Description: Production-grade autonomous API architecture discovery
echo   - DO NOT initialize with README
echo   - Click "Create repository"
echo.
pause
echo.
echo STEP 2: Pushing to GitHub...
echo.

cd /d "%~dp0"

git config user.name "Kimiti4"
git config user.email "karamos473@gmail.com"

git remote remove origin 2>nul
git remote add origin https://github.com/Kimiti4/EvoAPI-Autonomous-Architecture-Engine.git

git branch -M main

echo.
echo Pushing to GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   SUCCESS! Repository pushed to GitHub
    echo ========================================
    echo.
    echo Visit: https://github.com/Kimiti4/EvoAPI-Autonomous-Architecture-Engine
    echo.
) else (
    echo.
    echo ========================================
    echo   ERROR: Push failed
    echo ========================================
    echo.
    echo Possible reasons:
    echo   1. Repository not created on GitHub yet
    echo   2. Authentication required (use GitHub token or SSH)
    echo   3. Network connection issue
    echo.
    echo To authenticate, you may need a personal access token:
    echo   https://github.com/settings/tokens
    echo.
)

pause
