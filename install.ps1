# One-command installer for skills-manager (PyPI: skill-control-plane), Windows.
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/udayvarmora07/skills-manager/main/install.ps1 | iex"
#
# With options:
#
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/udayvarmora07/skills-manager/main/install.ps1))) -WithTiktoken
#
# Order of preference: `uv tool install` (uv also supplies Python), then
# `pipx install`, then a private virtual environment under
# %LOCALAPPDATA%\skill-control-plane\venv using the first Python >= 3.11.
#
# It never edits your PATH or profile, downloads another installer, or touches
# your skills or the manager's data directory. Uninstall leaves that data alone.

[CmdletBinding()]
param(
    [string]$Method = $env:SKILLS_MGR_INSTALL_METHOD,
    [string]$Version = '',
    [switch]$Source,
    [string]$From = '',
    [switch]$WithTiktoken,
    [string]$Prefix = $env:SKILLS_MGR_INSTALL_PREFIX,
    [switch]$DryRun,
    [switch]$Uninstall,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3

$Dist = 'skill-control-plane'
$Command = 'skills-mgr'
$SourceArchive = 'https://github.com/udayvarmora07/skills-manager/archive/refs/heads/main.tar.gz'
$VenvOwner = "skill-control-plane venv 1`n"

function Say([string]$Text) { Write-Host "skills-mgr install: $Text" }
function Fail([string]$Text) { throw "skills-mgr install: error: $Text" }
function Have([string]$Name) { [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Invoke-Step {
    param([string]$Exe, [string[]]$Arguments)
    Write-Host ('+ ' + (@($Exe) + $Arguments -join ' '))
    if (-not $DryRun) {
        & $Exe @Arguments
        if ($LASTEXITCODE -ne 0) { Fail "'$Exe' exited with code $LASTEXITCODE" }
    }
}

function Find-Python {
    # Windows PowerShell 5.1 turns redirected native stderr into an error
    # record; under 'Stop' that would abort the probe instead of skipping it.
    $ErrorActionPreference = 'Continue'
    $check = 'import sys; sys.exit(sys.version_info < (3, 11))'
    if (Have 'py') {
        foreach ($v in '3.14', '3.13', '3.12', '3.11') {
            & py "-$v" -c $check 2>$null
            if ($LASTEXITCODE -eq 0) {
                return (& py "-$v" -c 'import sys; print(sys.executable)').Trim()
            }
        }
    }
    foreach ($name in 'python', 'python3') {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) {
            & $cmd.Source -c $check 2>$null
            if ($LASTEXITCODE -eq 0) { return $cmd.Source }
        }
    }
    return $null
}

function Get-Exe([string]$Dir, [string]$Name) {
    $exe = Join-Path $Dir "$Name.exe"
    if (Test-Path -LiteralPath $exe -PathType Leaf) { return $exe }
    return (Join-Path $Dir $Name)
}

function Get-VenvBin([string]$Root) {
    if (Test-Path -LiteralPath (Join-Path $Root 'Scripts') -PathType Container) { return (Join-Path $Root 'Scripts') }
    return (Join-Path $Root 'bin')
}

function Get-PathItem([string]$Path) {
    Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
}

function Test-PlainFile([string]$Path) {
    $item = Get-PathItem $Path
    return ($item -is [System.IO.FileInfo] -and -not ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint))
}

function Test-PlainDirectory([string]$Path) {
    $item = Get-PathItem $Path
    return ($item -is [System.IO.DirectoryInfo] -and -not ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint))
}

function Test-MarkedVenv {
    return ((Test-PlainFile $OwnerPath) -and (Get-PathItem $OwnerPath).Length -eq $VenvOwner.Length -and
            [System.IO.File]::ReadAllText($OwnerPath) -ceq $VenvOwner)
}

function Test-ProductMetadata([string]$Path) {
    if (-not (Test-PlainFile $Path) -or (Get-PathItem $Path).Length -gt 1048576) { return $false }
    foreach ($line in [System.IO.File]::ReadLines($Path)) {
        if (-not $line) { break }
        if ($line -match '^Name: ') { return ($line -eq "Name: $Dist") }
    }
    return $false
}

function Test-LegacyVenv {
    # Previous releases kept no ownership record. Only their dedicated app
    # directory is eligible, with both the launcher and distribution metadata.
    if ($Prefix -ne $DefaultPrefix -or -not (Test-PlainFile $VenvConfig)) { return $false }
    $bin = Get-VenvBin $Prefix
    if (-not (Test-PlainDirectory $bin) -or -not (Test-PlainFile (Get-Exe $bin $Command))) { return $false }
    $lib = Join-Path $Prefix 'Lib'
    $site = Join-Path $lib 'site-packages'
    if (-not (Test-PlainDirectory $lib) -or -not (Test-PlainDirectory $site)) { return $false }
    foreach ($metadata in (Get-ChildItem -LiteralPath $site -Directory -Filter 'skill_control_plane-*.dist-info' -ErrorAction SilentlyContinue)) {
        if ($metadata.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { continue }
        if (Test-ProductMetadata (Join-Path $metadata.FullName 'METADATA')) { return $true }
    }
    return $false
}

function Write-VenvOwner {
    Say "recording virtual environment ownership in $OwnerPath"
    if ($DryRun) { return }
    $marker = [System.IO.File]::Open($OwnerPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($VenvOwner)
        $marker.Write($bytes, 0, $bytes.Length)
    } finally { $marker.Dispose() }
}

function Open-VenvLock {
    if ($DryRun) { return $null }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Prefix.ToUpperInvariant()))
    } finally { $sha.Dispose() }
    $mutex = [System.Threading.Mutex]::new($false, 'SkillsManager-Venv-' + [System.BitConverter]::ToString($digest))
    try {
        if ($mutex.WaitOne(0)) { return $mutex }
    } catch [System.Threading.AbandonedMutexException] {
        return $mutex
    } catch {
        $mutex.Dispose()
        throw
    }
    $mutex.Dispose()
    Fail "could not lock $Prefix; another installer is using this directory"
}

function Close-VenvLock($Mutex) {
    if ($Mutex) {
        try { $Mutex.ReleaseMutex() }
        finally { $Mutex.Dispose() }
    }
}

function Remove-OwnedVenv {
    $mutex = Open-VenvLock
    try {
        $current = Get-PathItem $Prefix
        if (-not $current) { return $false }
        if ($current -isnot [System.IO.DirectoryInfo] -or
            ($current.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
            (-not (Test-MarkedVenv) -and -not (Test-LegacyVenv))) {
            Say "leaving $Prefix alone: ownership could not be verified"
            return $false
        }
        Write-Host "+ remove virtual environment $Prefix"
        # Directory.Delete treats the path literally and does not recurse
        # through reparse points on Windows, including in .NET Framework.
        if (-not $DryRun) { [System.IO.Directory]::Delete($Prefix, $true) }
        return $true
    } finally { Close-VenvLock $mutex }
}

if ($Help) {
    @'
Install skills-manager (the skills-mgr command) in one step.

  -Method M       uv, pipx or venv (default: the first one available)
  -Version V      install this PyPI release instead of the latest
  -Source         install the current GitHub main branch instead of PyPI
  -From SPEC      install from any pip spec: a local checkout, a URL, a wheel
  -WithTiktoken   also install tiktoken for exact token counts
  -Prefix DIR     venv method: where the environment lives
  -DryRun         print the commands, change nothing
  -Uninstall      remove what this script installed (your skills stay)
'@ | Write-Host
    return
}

if ($Method -and @('uv', 'pipx', 'venv') -notcontains $Method) {
    Fail "-Method must be uv, pipx or venv, got '$Method'"
}

$installBase = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $HOME '.local/share' }
$DefaultPrefix = [System.IO.Path]::GetFullPath((Join-Path $installBase 'skill-control-plane/venv'))
if (-not $Prefix) { $Prefix = $DefaultPrefix }
$Prefix = [System.IO.Path]::GetFullPath($Prefix)
if ($Prefix -eq [System.IO.Path]::GetPathRoot($Prefix)) { Fail '-Prefix needs a virtual environment directory' }
$Prefix = $Prefix.TrimEnd([char[]] @([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar))
$VenvConfig = Join-Path $Prefix 'pyvenv.cfg'
$OwnerPath = Join-Path $Prefix '.skills-manager-install'

$Spec = $Dist
if ($Source) { $Spec = $SourceArchive }
if ($From) { $Spec = $From }
if ($Version) {
    if ($Source -or $From) { Fail '-Version cannot be combined with -Source or -From' }
    if ($Version -notmatch '^[0-9A-Za-z][0-9A-Za-z.+!-]*$') { Fail "invalid -Version '$Version'" }
    $Spec = "$Dist==$Version"
}
if ($Spec.StartsWith('-')) { Fail "a package spec cannot start with '-'" }

if ($Uninstall) {
    $ErrorActionPreference = 'Continue'
    $removed = $false
    if ((-not $Method -or $Method -eq 'uv') -and (Have 'uv')) {
        if ((& uv tool list 2>$null) -match "^$Dist ") { Invoke-Step 'uv' @('tool', 'uninstall', $Dist); $removed = $true }
    }
    if ((-not $Method -or $Method -eq 'pipx') -and (Have 'pipx')) {
        if ((& pipx list --short 2>$null) -match "^$Dist ") { Invoke-Step 'pipx' @('uninstall', $Dist); $removed = $true }
    }
    if (-not $Method -or $Method -eq 'venv') {
        $ErrorActionPreference = 'Stop'
        if (Remove-OwnedVenv) { $removed = $true }
    }
    if (-not $removed) { Say 'nothing installed by this script was found' }
    elseif ($DryRun) { Say 'dry run: nothing was changed' }
    else { Say "removed. Your skills and the manager's data directory were not touched." }
    return
}

if (-not $Method) {
    if (Have 'uv') { $Method = 'uv' } elseif (Have 'pipx') { $Method = 'pipx' } else { $Method = 'venv' }
}
Say "installing $Spec with $Method"

$installed = $null
switch ($Method) {
    'uv' {
        if (-not (Have 'uv')) { Fail 'uv is not on PATH' }
        $uvArgs = @('tool', 'install', '--force', '--python', '>=3.11')
        if ($WithTiktoken) { $uvArgs += @('--with', 'tiktoken') }
        Invoke-Step 'uv' ($uvArgs + @($Spec))
    }
    'pipx' {
        if (-not (Have 'pipx')) { Fail 'pipx is not on PATH' }
        $python = Find-Python
        $pipxArgs = @('install', '--force')
        if ($python) { $pipxArgs += @('--python', $python) }
        Invoke-Step 'pipx' ($pipxArgs + @($Spec))
        if ($WithTiktoken) { Invoke-Step 'pipx' @('inject', $Dist, 'tiktoken') }
    }
    'venv' {
        $python = Find-Python
        if (-not $python) {
            Fail 'no Python 3.11 or newer found. Install one from python.org, or install uv (https://docs.astral.sh/uv/) and run this again: uv fetches Python for you.'
        }
        Say "using $python"
        $mutex = Open-VenvLock
        try {
            $current = Get-PathItem $Prefix
            if ($current) {
                if ($current -isnot [System.IO.DirectoryInfo] -or ($current.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
                    Fail "$Prefix is not an ordinary directory; choose another -Prefix"
                }
                if (-not (Test-MarkedVenv)) {
                    if (-not (Test-LegacyVenv)) { Fail "$Prefix does not belong to Skills Manager; choose another -Prefix" }
                    Write-VenvOwner
                }
            } else {
                if (-not $DryRun) { [void] [System.IO.Directory]::CreateDirectory($Prefix) }
                Write-VenvOwner
            }
            if (-not (Test-PlainFile $VenvConfig)) {
                if (Get-PathItem $VenvConfig) { Fail "$VenvConfig is not a regular file" }
                Invoke-Step $python @('-m', 'venv', $Prefix)
            }
            $bin = Get-VenvBin $Prefix
            if (-not $DryRun -and -not (Test-PlainDirectory $bin)) { Fail "$bin is not an ordinary directory" }
            $venvPython = Get-Exe $bin 'python'
            $pipArgs = @('-m', 'pip', 'install', '--upgrade', '--disable-pip-version-check', $Spec)
            if ($WithTiktoken) { $pipArgs += 'tiktoken' }
            Invoke-Step $venvPython $pipArgs
            $installed = Get-Exe $bin $Command
            if (-not $DryRun) {
                if (-not (Test-PlainFile $installed)) { Fail "the package did not install a $Command launcher" }
                $installedVersion = & $installed --version
                if ($LASTEXITCODE -ne 0) { Fail "$installed failed its version check" }
                Say "installed: $installedVersion"
            }
        } finally { Close-VenvLock $mutex }
    }
}

if ($DryRun) { Say 'dry run: nothing was changed'; return }

if (-not $installed) {
    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if ($cmd) { $installed = $cmd.Source }
}
if ($installed -and $Method -ne 'venv') {
    Say ('installed: ' + (& $installed --version))
}
if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
    switch ($Method) {
        'uv' { Say "run 'uv tool update-shell' once, then open a new terminal" }
        'pipx' { Say "run 'pipx ensurepath' once, then open a new terminal" }
        'venv' { Say "skills-mgr is in $(Get-VenvBin $Prefix); add that folder to your PATH" }
    }
}
@'

Next steps:
  skills-mgr scopes        # see every agent's skill folder this tool found
  skills-mgr doctor        # health check, changes nothing
  skills-mgr webui         # open the local web UI on 127.0.0.1

Docs: https://github.com/udayvarmora07/skills-manager#readme
'@ | Write-Host
