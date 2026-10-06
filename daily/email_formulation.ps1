# Emails the day's Word formulation to James (James Kuo, 6 Oct 2026: "whenever this happen (aka schedule from my
# outlook), can you email me the formulation for that day"). The Microsoft 365 connector sends mail but takes no
# attachment, so this goes through the classic Outlook on James's PC over COM, like fetch_schedule_mail.ps1.
#
#   powershell -ExecutionPolicy Bypass -File daily/email_formulation.ps1 -Date 2026-10-06 [-Body "<summary>"] [-Replaces]
#
# Only to James (the address is fixed here, not a parameter). Sent once per version of the file: work/emailed_<date>.txt
# keeps the hash of what was sent; the same file again is not re-sent, a rebuilt one is (say -Replaces so the subject
# says it replaces the earlier copy).
param([Parameter(Mandatory = $true)][string]$Date, [string]$Body = '', [switch]$Replaces)

$To = 'JKUO@wpjk.inteplast.com'
$root = Split-Path -Parent $PSScriptRoot
$doc = Join-Path $root "out\FRM Formulation $Date.docx"
if (-not (Test-Path -LiteralPath $doc)) { "not sent | no $doc"; exit 1 }
$hash = (Get-FileHash -LiteralPath $doc).Hash
$mark = Join-Path $root "work\emailed_$Date.txt"
if ((Test-Path -LiteralPath $mark) -and ((Get-Content -LiteralPath $mark -TotalCount 1) -eq $hash)) {
    "already | $doc was emailed to $To ($((Get-Item -LiteralPath $mark).LastWriteTime.ToString('yyyy-MM-dd HH:mm')))"; exit 0
}

$day = [datetime]::ParseExact($Date, 'yyyy-MM-dd', $null)
$subject = 'FRM Formulation {0} ({1})' -f $Date, $day.ToString('ddd d MMM')
if ($Replaces) { $subject += ' - REPLACES the earlier copy' }
if (-not $Body) { $Body = "The Word formulation for $Date, built from the day's schedule email, is attached." }
$Body += "`r`n`r`nSent by the scheduled schedule run (Claude Code on James's PC). Rows marked ENGINEER TO COMPLETE need an engineer's formula before the copy is issued."

$ol = New-Object -ComObject Outlook.Application
$m = $ol.CreateItem(0)
$m.To = $To
$m.Subject = $subject
$m.Body = $Body
[void]$m.Attachments.Add($doc)
$m.Send()
try { $ol.GetNamespace('MAPI').SendAndReceive($false) } catch {}
Set-Content -LiteralPath $mark -Value @($hash, (Get-Date -Format 'yyyy-MM-dd HH:mm'), $subject) -Encoding utf8
"sent | $subject | to $To | $doc"
