$prs = 4..16
git checkout main
git pull

foreach ($pr in $prs) {
    Write-Host "`n=================================="
    Write-Host "Processing PR $pr"
    Write-Host "=================================="
    
    gh pr checkout $pr
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to checkout PR $pr or it is already closed/merged."
        continue
    }
    
    Write-Host "Running tests..."
    pytest -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Tests passed for PR $pr. Merging..."
        git checkout main
        gh pr merge $pr --merge --delete-branch
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Successfully merged PR $pr."
        } else {
            Write-Host "Failed to merge PR $pr (maybe conflicts?)."
        }
        git pull
    } else {
        Write-Host "Tests failed for PR $pr, skipping merge."
        git checkout main
    }
}
