param(
  [Parameter(Mandatory=$true)][string]$InputPath,
  [Parameter(Mandatory=$true)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\logs\dcf-validation'))
$inputFile = (Resolve-Path -LiteralPath $InputPath).Path
$output = [IO.Path]::GetFullPath($OutputDirectory)
$prefix = $root.TrimEnd('\') + '\'
if (-not $inputFile.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
    -not $output.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
    [IO.Path]::GetExtension($inputFile) -ne '.xlsx') {
  throw 'Only generated XLSX validation artifacts inside logs/dcf-validation are accepted.'
}
if (Test-Path -LiteralPath $output) { throw 'Output directory must be new; existing evidence is never overwritten.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead($inputFile)
try {
  foreach ($entry in $archive.Entries) {
    if ($entry.FullName -match 'vbaProject|macrosheets|externalLinks|connections\.xml|queryTables|embeddings') {
      throw 'Active content or external workbook connections are not permitted.'
    }
  }
} finally { $archive.Dispose() }
[void](New-Item -ItemType Directory -Path $output)
$excel = $null
$books = $null
$book = $null
try {
  $excel = New-Object -ComObject Excel.Application
  $excel.Visible = $false
  $excel.DisplayAlerts = $false
  $excel.EnableEvents = $false
  $excel.AskToUpdateLinks = $false
  $excel.AutomationSecurity = 3
  $books = $excel.Workbooks
  $book = $books.Open($inputFile, 0, $true, [Type]::Missing, '', '', $true)
  if ($book.Connections.Count -ne 0) { throw 'Unexpected workbook connections.' }
  $excel.CalculateFullRebuild()
  $book.SaveAs((Join-Path $output 'recalculated.xlsx'), 51)
  $book.ExportAsFixedFormat(0, (Join-Path $output 'rendered.pdf'))
  [PSCustomObject]@{Status='RECALCULATED'; ExcelVersion=$excel.Version; Output=$output} | ConvertTo-Json -Compress
} finally {
  if ($null -ne $book) { $book.Close($false); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book) }
  if ($null -ne $books) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($books) }
  if ($null -ne $excel) { $excel.Quit(); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel) }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
