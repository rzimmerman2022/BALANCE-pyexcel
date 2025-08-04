# This script consolidates all analysis files into one directory
# Run this from your BALANCE-pyexcel directory

Write-Host "Consolidating analysis files..." -ForegroundColor Green

# Check if full_column_analysis.json exists in comprehensive_analysis_results
if (Test-Path "comprehensive_analysis_results\full_column_analysis.json") {
    Write-Host "Found full_column_analysis.json in comprehensive_analysis_results" -ForegroundColor Yellow
    
    # Copy it to transaction_analysis_results
    Copy-Item "comprehensive_analysis_results\full_column_analysis.json" -Destination "transaction_analysis_results\" -Force
    Write-Host "Copied full_column_analysis.json to transaction_analysis_results" -ForegroundColor Green
} else {
    Write-Host "WARNING: full_column_analysis.json not found in comprehensive_analysis_results" -ForegroundColor Red
}

# Verify all files are now in transaction_analysis_results
Write-Host "`nVerifying all required files are present:" -ForegroundColor Green
$requiredFiles = @(
    "full_column_analysis.json",
    "cleaning_recommendations.json", 
    "merchant_variations.json",
    "pattern_analysis.json"
)

$allPresent = $true
foreach ($file in $requiredFiles) {
    if (Test-Path "transaction_analysis_results\$file") {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file MISSING" -ForegroundColor Red
        $allPresent = $false
    }
}

if ($allPresent) {
    Write-Host "`nAll files consolidated successfully! You can now run your pipeline." -ForegroundColor Green
} else {
    Write-Host "`nSome files are missing. Please check your analysis directories." -ForegroundColor Red
}