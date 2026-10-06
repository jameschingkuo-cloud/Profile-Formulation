# Saves the day's schedule PDFs from Johanna Vallejo's emails to Downloads (James Kuo, 6 Oct 2026: "check my email
# everyday for schedule from JVallejo@wpjk.inteplast.com. usually there are two, one for extrusion and one for
# converting"). The Microsoft 365 connector finds the emails but cannot hand over an attachment's bytes, so this goes
# through the Outlook installed on James's PC (classic Outlook over COM; it starts in the background if not running).
#
#   powershell -ExecutionPolicy Bypass -File daily/fetch_schedule_mail.ps1 [-Date 2026-10-06[,2026-10-05]] [-WaitSeconds 60]
#
# Where the emails are: James's Outlook rule "Move all messages from Johanna Vallejo to Production Schedule" (6 Oct 2026:
# "I move the email to new folder and set new rule where is will always be in that folder") puts them in
# Inbox\Complete\Production Schedule. The Inbox is looked at too, for one the rule has not moved yet.
# Only PDF attachments of emails from the sender received on that date. A file already in Downloads with the same bytes
# is left as it is; a different file under the same name (a re-sent schedule) is saved beside it as "<name> (HHmm).pdf".
# Nothing is deleted, moved or sent. One line per attachment: status | file | subject | received.
param([string]$Date = (Get-Date -Format 'yyyy-MM-dd'), [int]$WaitSeconds = 60, [string]$Sender = 'VALLEJO',
      [string]$Folder = 'Complete\Production Schedule')

# -Date takes one date or several, comma-separated (one Outlook pass for all of them)
$days = $Date.Split(',') | Where-Object { $_.Trim() } | ForEach-Object { [datetime]::ParseExact($_.Trim(), 'yyyy-MM-dd', $null) }
$day = ($days | Measure-Object -Minimum).Minimum
$end = (($days | Measure-Object -Maximum).Maximum).AddDays(1)
$dl = Join-Path $env:USERPROFILE 'Downloads'
$ol = New-Object -ComObject Outlook.Application
$ns = $ol.GetNamespace('MAPI')
$inbox = $ns.GetDefaultFolder(6)
$folders = @()
try { $f = $inbox; foreach ($n in $Folder.Split('\')) { $f = $f.Folders.Item($n) }; $folders += $f }
catch { "warning | | folder Inbox\$Folder not found (rule changed?): looking in the Inbox only" }
$folders += $inbox
try { $ns.SendAndReceive($false) } catch {}

function Get-Mails {
    $found = @(); $ids = @{}
    foreach ($fo in $folders) {
        $items = $fo.Items
        $items.Sort('[ReceivedTime]', $true)
        foreach ($m in $items) {
            try { $t = $m.ReceivedTime } catch { continue }
            if ($t -lt $day) { break }
            if ($t -ge $end -or -not ($days | Where-Object { $_ -eq $t.Date })) { continue }
            $s = ''; try { $s = "$($m.SenderEmailAddress) $($m.SenderName)" } catch {}
            if ($s -match $Sender -and -not $ids.ContainsKey($m.EntryID)) { $ids[$m.EntryID] = 1; $found += $m }
        }
    }
    , $found
}

# Outlook may still be catching up after it starts: wait for the newest mail to be at least as new as the server's.
$mails = Get-Mails
$waited = 0
while ($waited -lt $WaitSeconds) {
    Start-Sleep -Seconds 10; $waited += 10
    $again = Get-Mails
    if ($again.Count -eq $mails.Count -and $waited -ge 20) { $mails = $again; break }
    $mails = $again
}

if ($mails.Count -eq 0) { "none | | no email from $Sender received $Date (Outlook waited ${waited}s)"; exit 0 }
foreach ($m in $mails) {
    foreach ($a in $m.Attachments) {
        if ($a.FileName -notmatch '\.pdf$') { continue }
        $dest = Join-Path $dl $a.FileName
        $tmp = Join-Path $env:TEMP ("sched_" + [guid]::NewGuid().ToString('N') + '.pdf')
        $a.SaveAsFile($tmp)
        $status = 'saved'
        if (Test-Path -LiteralPath $dest) {
            if ((Get-FileHash -LiteralPath $dest).Hash -eq (Get-FileHash -LiteralPath $tmp).Hash) {
                $status = 'already'
            } else {
                $dest = Join-Path $dl ('{0} ({1}){2}' -f [IO.Path]::GetFileNameWithoutExtension($a.FileName), $m.ReceivedTime.ToString('HHmm'), [IO.Path]::GetExtension($a.FileName))
                if ((Test-Path -LiteralPath $dest) -and (Get-FileHash -LiteralPath $dest).Hash -eq (Get-FileHash -LiteralPath $tmp).Hash) { $status = 'already' } else { $status = 'saved-resent' }
            }
        }
        if ($status -eq 'already') { Remove-Item -LiteralPath $tmp } else { Move-Item -LiteralPath $tmp -Destination $dest }
        '{0} | {1} | {2} | {3}' -f $status, $dest, $m.Subject, $m.ReceivedTime.ToString('yyyy-MM-dd HH:mm')
    }
}
