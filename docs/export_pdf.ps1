$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Resolve-Path "$scriptDir\.."
$pptxPath = Join-Path $projectDir "CampusAssist_Project_Presentation.pptx"
$pdfPath = Join-Path $projectDir "CampusAssist_Project_Presentation.pdf"

Write-Host "[*] PPTX source: $pptxPath"
Write-Host "[*] Target PDF:  $pdfPath"

try {
    $pptApp = New-Object -ComObject PowerPoint.Application
    # Open presentation hidden / read-only
    $pres = $pptApp.Presentations.Open($pptxPath, 2, 0, 0)
    # Format 32 = ppSaveAsPDF
    $pres.SaveAs($pdfPath, 32)
    $pres.Close()
    $pptApp.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($pptApp) | Out-Null
    Write-Host "[+] Successfully exported to PDF via PowerPoint COM!"
} catch {
    Write-Host "[!] PowerPoint COM export error: $($_.Exception.Message)"
    exit 1
}

