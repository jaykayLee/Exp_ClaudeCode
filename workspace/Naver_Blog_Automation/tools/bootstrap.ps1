# Windows PowerShell 5.1. Run only through the bundled install.bat.
$ErrorActionPreference = 'Stop'
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $Root
$LogDir = Join-Path $Root '09_LOGS'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ('install_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.log')
Start-Transcript -Path $Log -Force | Out-Null
try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw '64-bit Windows is required.' }
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw 'This baseline installer targets x64 Windows. ARM64 installation has not been validated.' }
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    function Test-Python([string]$Path) {
        if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $false }
        try {
            & $Path -c 'import sys,struct; sys.exit(0 if (3,11)<=sys.version_info[:2]<(3,14) and struct.calcsize(chr(80))==8 else 1)' 2>$null
            return ($LASTEXITCODE -eq 0)
        } catch { return $false }
    }
    function Find-Python {
        $candidates = @()
        $candidates += (Join-Path $Root '.venv\Scripts\python.exe')
        foreach ($v in @('313','312','311')) {
            $candidates += (Join-Path $env:LOCALAPPDATA ('Programs\Python\Python'+$v+'\python.exe'))
        }
        $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($launcher) {
            foreach ($v in @('-3.13','-3.12','-3.11')) {
                try {
                    $result = & $launcher.Source $v -c 'import sys; print(sys.executable)' 2>$null
                    if ($LASTEXITCODE -eq 0 -and $result) { $candidates += [string]($result | Select-Object -Last 1) }
                } catch { }
            }
        }
        $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notmatch 'WindowsApps') { $candidates += $cmd.Source }
        foreach ($candidate in $candidates) { if (Test-Python $candidate) { return $candidate } }
        return $null
    }
    $Python = Find-Python
    if (-not $Python) {
        Write-Host 'Python 3.11-3.13 x64 was not found. The preferred runtime is Python 3.13.'
        $answer = Read-Host 'Install Python from an official distribution? [Y/N]'
        if ($answer -notmatch '^[Yy]$') { throw 'Python installation was declined; no runtime was installed.' }
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Host 'Trying Windows Package Manager...'
            & $winget.Source install --exact --id Python.Python.3.13 --source winget --scope user --accept-source-agreements --accept-package-agreements
            if ($LASTEXITCODE -ne 0) { Write-Host 'WinGet did not complete. Trying the signed python.org installer.' }
            $Python = Find-Python
        }
        if (-not $Python) {
            $Cache = Join-Path $LogDir 'installer_cache'
            New-Item -ItemType Directory -Force -Path $Cache | Out-Null
            $Installer = Join-Path $Cache 'python-3.13.16-amd64.exe'
            $Uri = 'https://www.python.org/ftp/python/3.13.16/python-3.13.16-amd64.exe'
            Write-Host "Downloading $Uri"
            Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Installer
            $Signature = Get-AuthenticodeSignature -FilePath $Installer
            if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
                throw 'Python installer signature validation failed. Installation stopped.'
            }
            $Target = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313'
            $Arguments = '/passive InstallAllUsers=0 Include_launcher=1 InstallLauncherAllUsers=0 Include_test=0 Include_pip=1 PrependPath=0 TargetDir="'+$Target+'"'
            $Process = Start-Process -FilePath $Installer -ArgumentList $Arguments -Wait -PassThru
            if ($Process.ExitCode -notin @(0,3010)) { throw ('Python installer exit code: '+$Process.ExitCode) }
            $Python = Find-Python
        }
    }
    if (-not $Python) { throw 'Python detection failed. See the install log and the official Windows setup guide.' }
    Write-Host "Selected Python: $Python"
    $Venv = Join-Path $Root '.venv'
    $VenvPython = Join-Path $Venv 'Scripts\python.exe'
    if (Test-Path -LiteralPath $Venv) {
        if (-not (Test-Python $VenvPython)) { throw 'Existing .venv is incompatible. Rename it to .venv_backup manually, then run install.bat again. User data is unchanged.' }
    } else {
        & $Python -m venv $Venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    & $VenvPython -m pip install --disable-pip-version-check --only-binary=:all: -r (Join-Path $Root 'tools\dependencies.lock')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Do not disable SSL checks; inspect proxy/network settings.' }
    & $VenvPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'pip check failed.' }
    & $VenvPython (Join-Path $Root 'tools\doctor.py')
    if ($LASTEXITCODE -ne 0) { throw 'Environment diagnosis failed.' }
    & $VenvPython (Join-Path $Root 'tools\qa_runner.py')
    if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed.' }
    & $VenvPython -m pip freeze | Set-Content -Encoding UTF8 -Path (Join-Path $LogDir 'installed_packages.lock')
    Write-Host 'Setup completed. Double-click start_panel.bat. No task or blog post was created.'
} catch {
    Write-Host ('[FAILED] '+$_.Exception.Message)
    Write-Host "Log: $Log"
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
