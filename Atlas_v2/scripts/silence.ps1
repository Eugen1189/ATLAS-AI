$processes = Get-Process python -ErrorAction SilentlyContinue
foreach ($p in $processes) {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)").CommandLine
        if ($cmd -like "*Atlas*" -or $p.Path -like "*Atlas*") {
            Write-Host "Killing process $($p.Id): $($p.Name) - $cmd"
            Stop-Process -Id $p.Id -Force
        }
    } catch {
        # Access denied or process exited
    }
}
Write-Host "Silence protocols complete."
