<#
  Make-Previews.ps1   —   balanced 20-row previews
  Handles Transaction_Ledger files that have 2-line pre-ambles.
#>

param(
    [string]$SourceDir     = ".\data",
    [int]   $RowsPerPerson = 10
)

function Get-CleanCsvRows {
    param([string]$Path)

    $all = Get-Content $Path
    # Find the first line that looks like the real header
    $headerLine = $all |
        Select-Object -First 20 |
        Where-Object { $_ -match '^"?Name"?,' -and $_ -match 'Date of Purchase' } |
        Select-Object -First 1

    if (-not $headerLine) { return $null }          # not found

    $startIdx = [Array]::IndexOf($all, $headerLine)
    return $all[$startIdx..($all.Count-1)]
}

function Find-PersonColumn ($Rows) {
    foreach ($col in $Rows[0].PSObject.Properties.Name) {
        if ($Rows | Select-Object -First 50 |
            Where-Object { $_.$col -match '^(Ryan|Jordyn)$' }) { return $col }
    }
    return $null
}

$previewDir = Join-Path $SourceDir "_samples"
if (-not (Test-Path $previewDir)) { New-Item -ItemType Directory -Path $previewDir | Out-Null }

Get-ChildItem $SourceDir -Filter "*.csv" | ForEach-Object {

    $src  = $_.FullName
    $dest = Join-Path $previewDir ("preview_" + $_.Name)

    if ($_.Name -match '^(Expense_History|Transaction_Ledger)') {

        $raw = Get-CleanCsvRows -Path $src
        if (-not $raw) {
            Write-Warning "$($_.Name) – could not detect a proper header. Skipped."
            return
        }

        $rows    = $raw | ConvertFrom-Csv
        $personC = Find-PersonColumn $rows
        if (-not $personC) {
            Write-Warning "$($_.Name) – no Ryan/Jordyn column found. Skipped."
            return
        }

        $sample = foreach ($p in @('Ryan','Jordyn')) {
            $rows | Where-Object { $_.$personC -eq $p } |
                   Select-Object -First $RowsPerPerson
        }

        $sample | Export-Csv -Path $dest -NoTypeInformation
        Write-Host ("✓  {0}  →  {1}" -f $_.Name, (Split-Path $dest -Leaf))

    } else {
        # simple 20-row slice for everything else
        Get-Content $src -TotalCount 21 | Set-Content $dest
        Write-Host ("✓  {0}  →  {1}" -f $_.Name, (Split-Path $dest -Leaf))
    }
}
