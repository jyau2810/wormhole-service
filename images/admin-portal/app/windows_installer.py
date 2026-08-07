from __future__ import annotations

import base64
import re
from collections.abc import Iterable

from .settings import Gateway

L2TP_PROTOCOL = "l2tp-ipsec-psk"


def _powershell_literal(value: str) -> str:
    if "\x00" in value:
        raise ValueError("Windows VPN installer values cannot contain NUL bytes")
    return "'" + value.replace("'", "''") + "'"


def _safe_filename_part(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return sanitized or "account"


def build_windows_installer(
    username: str,
    password: str,
    vpn_shared_psk: str,
    gateways: Iterable[Gateway],
) -> bytes:
    l2tp_gateways = tuple(gateway for gateway in gateways if gateway.protocol == L2TP_PROTOCOL)
    if not l2tp_gateways:
        raise ValueError("no L2TP/IPSec gateway configured")

    multiple_gateways = len(l2tp_gateways) > 1
    connection_rows = []
    for gateway in l2tp_gateways:
        connection_name = f"Wormhole - {gateway.name}" if multiple_gateways else "Wormhole VPN"
        connection_rows.append(
            "    [PSCustomObject]@{ Name = "
            f"{_powershell_literal(connection_name)}; ServerAddress = {_powershell_literal(gateway.address)} }}"
        )

    powershell = fr"""$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$username = {_powershell_literal(username)}
$password = {_powershell_literal(password)}
$sharedSecret = {_powershell_literal(vpn_shared_psk)}
$rasdial = Join-Path $env:SystemRoot 'System32\rasdial.exe'
$connections = @(
{chr(10).join(connection_rows)}
)

try {{
    foreach ($connection in $connections) {{
        $existing = Get-VpnConnection -Name $connection.Name -ErrorAction SilentlyContinue
        if ($null -ne $existing) {{
            if ($existing.ConnectionStatus -eq 'Connected') {{
                & $rasdial $connection.Name /disconnect
                if ($LASTEXITCODE -ne 0) {{
                    throw "Could not disconnect existing VPN connection: $($connection.Name)"
                }}
            }}
            Remove-VpnConnection -Name $connection.Name -Force
        }}
        Add-VpnConnection `
            -Name $connection.Name `
            -ServerAddress $connection.ServerAddress `
            -TunnelType L2tp `
            -L2tpPsk $sharedSecret `
            -AuthenticationMethod MSChapv2 `
            -EncryptionLevel Optional `
            -RememberCredential `
            -Force
        Write-Host ("Created VPN connection: " + $connection.Name)
    }}

    $primary = $connections[0]
    Write-Host ("Connecting to " + $primary.Name + "...")
    & $rasdial $primary.Name $username $password
    if ($LASTEXITCODE -ne 0) {{
        throw "VPN connection failed with rasdial exit code $LASTEXITCODE"
    }}

    Write-Host ""
    Write-Host "VPN installation and first connection completed." -ForegroundColor Green
    Write-Host "Windows has saved the credentials for future connections."
    exit 0
}} catch {{
    Write-Host ""
    Write-Host ("VPN installation failed: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}}
"""
    encoded_command = base64.b64encode(powershell.encode("utf-16-le")).decode("ascii")
    batch = f"""@echo off
setlocal
title Wormhole VPN Installer
echo Installing Wormhole VPN...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_command}
set "installer_exit_code=%errorlevel%"
echo.
pause
exit /b %installer_exit_code%
"""
    return batch.replace("\n", "\r\n").encode("utf-8")


def windows_installer_filename(username: str) -> str:
    return f"wormhole-{_safe_filename_part(username)}-windows.bat"
