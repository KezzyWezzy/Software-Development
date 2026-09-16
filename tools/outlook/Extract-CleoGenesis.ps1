<#
    Extract-CleoGenesis.ps1
    Sweeps every Outlook store/folder for mail relating to the Cleo project
    for Genesis Energy and writes a CSV + JSON export for downstream analysis.

    Run on the workstation that has the Outlook profile (PHATCOD01).
    Outlook must be installed. It will be started if not already running.

    Usage:
      powershell -ExecutionPolicy Bypass -File .\Extract-CleoGenesis.ps1
      powershell -ExecutionPolicy Bypass -File .\Extract-CleoGenesis.ps1 -SaveAttachments
      powershell -ExecutionPolicy Bypass -File .\Extract-CleoGenesis.ps1 -RequireBoth
#>

[CmdletBinding()]
param(
    [string]   $OutDir          = "$env:USERPROFILE\Desktop\cleo-genesis-export",
    [string[]] $Terms           = @('cleo', 'genesis'),
    [string[]] $DomainTerms     = @('genesisenergy.com'),
    [switch]   $SaveAttachments,
    [switch]   $RequireBoth,     # only keep items matching Cleo AND Genesis
    [int]      $BodyExcerptChars = 800
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$attachDir = Join-Path $OutDir 'attachments'
if ($SaveAttachments) { New-Item -ItemType Directory -Force -Path $attachDir | Out-Null }

Write-Host "Connecting to Outlook..." -ForegroundColor Cyan
$outlook = New-Object -ComObject Outlook.Application
$ns      = $outlook.GetNamespace('MAPI')

# ---------------------------------------------------------------- DASL filter
# LIKE '%term%' is a case-insensitive substring match across subject + body.
$clauses = @()
foreach ($t in ($Terms + $DomainTerms)) {
    $e = $t -replace "'", "''"
    $clauses += "`"urn:schemas:httpmail:subject`" LIKE '%$e%'"
    $clauses += "`"urn:schemas:httpmail:textdescription`" LIKE '%$e%'"
    $clauses += "`"urn:schemas:httpmail:fromemail`" LIKE '%$e%'"
    $clauses += "`"urn:schemas:httpmail:displayto`" LIKE '%$e%'"
    $clauses += "`"urn:schemas:httpmail:displaycc`" LIKE '%$e%'"
}
$filter = '@SQL=' + ($clauses -join ' OR ')

# ------------------------------------------------------------------ helpers
function Get-Excerpt {
    param($Text, $Max)
    if (-not $Text) { return '' }
    $s = ($Text -replace '\s+', ' ').Trim()
    if ($s.Length -gt $Max) { return $s.Substring(0, $Max) + '...' }
    return $s
}

function Get-SenderAddress {
    param($Item)
    try {
        if ($Item.SenderEmailType -eq 'EX' -and $Item.Sender) {
            $ex = $Item.Sender.GetExchangeUser()
            if ($ex) { return $ex.PrimarySmtpAddress }
        }
        return $Item.SenderEmailAddress
    } catch { return $Item.SenderEmailAddress }
}

function Test-Relevant {
    param($Haystack)
    $h = $Haystack.ToLowerInvariant()
    $hitCleo    = $h.Contains('cleo')
    $hitGenesis = ($h.Contains('genesis')) -or ($DomainTerms | Where-Object { $h.Contains($_.ToLowerInvariant()) })
    if ($RequireBoth) { return ($hitCleo -and $hitGenesis) }
    return ($hitCleo -or $hitGenesis)
}

$records   = New-Object System.Collections.ArrayList
$seen      = @{}
$folderNum = 0

function Invoke-Folder {
    param($Folder, [string]$StoreName, [string]$Path)

    $script:folderNum++
    Write-Progress -Activity 'Scanning Outlook' -Status "$StoreName : $Path" -CurrentOperation "$($records.Count) matches"

    try {
        $items = $Folder.Items
        $hits  = $items.Restrict($filter)
    } catch {
        Write-Verbose "  skip (restrict failed): $Path -- $($_.Exception.Message)"
        $hits = $null
    }

    if ($hits) {
        foreach ($item in $hits) {
            try {
                # 43 = olMail, 53 = olMeetingRequest, 26 = olReport
                if ($item.Class -notin 43, 53, 26) { continue }

                $entryId = $item.EntryID
                if (-not $entryId -or $seen.ContainsKey($entryId)) { continue }

                $subject = [string]$item.Subject
                $body    = [string]$item.Body
                $from    = Get-SenderAddress -Item $item
                $to      = [string]$item.To
                $cc      = [string]$item.CC

                if (-not (Test-Relevant "$subject $body $from $to $cc")) { continue }
                $seen[$entryId] = $true

                $attNames = @()
                if ($item.Attachments.Count -gt 0) {
                    foreach ($a in $item.Attachments) {
                        $attNames += $a.FileName
                        if ($SaveAttachments) {
                            $stamp = (Get-Date $item.ReceivedTime -Format 'yyyyMMdd-HHmmss')
                            $safe  = ($a.FileName -replace '[\\/:*?"<>|]', '_')
                            try { $a.SaveAsFile((Join-Path $attachDir "$stamp`_$safe")) } catch {}
                        }
                    }
                }

                $lower = "$subject $body".ToLowerInvariant()
                $null = $records.Add([pscustomobject]@{
                    Date            = if ($item.ReceivedTime) { (Get-Date $item.ReceivedTime -Format 'yyyy-MM-dd HH:mm') } else { '' }
                    Store           = $StoreName
                    Folder          = $Path
                    Subject         = $subject
                    From            = $from
                    FromName        = [string]$item.SenderName
                    To              = $to
                    CC              = $cc
                    HasAttachments  = ($attNames.Count -gt 0)
                    AttachmentCount = $attNames.Count
                    Attachments     = ($attNames -join '; ')
                    MentionsCleo    = $lower.Contains('cleo')
                    MentionsGenesis = $lower.Contains('genesis')
                    ConversationID  = [string]$item.ConversationID
                    EntryID         = $entryId
                    BodyExcerpt     = (Get-Excerpt -Text $body -Max $BodyExcerptChars)
                })
            } catch {
                Write-Verbose "  item error in $Path : $($_.Exception.Message)"
            }
        }
    }

    foreach ($sub in $Folder.Folders) {
        Invoke-Folder -Folder $sub -StoreName $StoreName -Path "$Path\$($sub.Name)"
    }
}

# ------------------------------------------------------------------- sweep
foreach ($store in $ns.Folders) {
    Write-Host "Store: $($store.Name)" -ForegroundColor Yellow
    try {
        Invoke-Folder -Folder $store -StoreName $store.Name -Path $store.Name
    } catch {
        Write-Warning "Store '$($store.Name)' failed: $($_.Exception.Message)"
    }
}
Write-Progress -Activity 'Scanning Outlook' -Completed

# ------------------------------------------------------------------ output
$sorted  = $records | Sort-Object { [datetime]$_.Date }
$csvPath = Join-Path $OutDir 'cleo-genesis-emails.csv'
$jsonPath = Join-Path $OutDir 'cleo-genesis-emails.json'

$sorted | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
$sorted | ConvertTo-Json -Depth 4 | Out-File -FilePath $jsonPath -Encoding UTF8

Write-Host ""
Write-Host "Done. $($sorted.Count) messages across $folderNum folders." -ForegroundColor Green
Write-Host "  CSV : $csvPath"
Write-Host "  JSON: $jsonPath"
if ($SaveAttachments) { Write-Host "  Attachments: $attachDir" }
Write-Host ""
Write-Host "Breakdown:" -ForegroundColor Cyan
Write-Host ("  Cleo AND Genesis : {0}" -f ($sorted | Where-Object { $_.MentionsCleo -and $_.MentionsGenesis }).Count)
Write-Host ("  Cleo only        : {0}" -f ($sorted | Where-Object { $_.MentionsCleo -and -not $_.MentionsGenesis }).Count)
Write-Host ("  Genesis only     : {0}" -f ($sorted | Where-Object { $_.MentionsGenesis -and -not $_.MentionsCleo }).Count)
Write-Host ("  With attachments : {0}" -f ($sorted | Where-Object { $_.HasAttachments }).Count)
