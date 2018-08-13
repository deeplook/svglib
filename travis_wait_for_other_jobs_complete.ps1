function Get-TravisBuild {
    param()

    if (-not ($env:TRAVIS_API_TOKEN)) {
        throw "missing api token for Travis."
    }

    Invoke-RestMethod -Uri "https://TODO/api/projects/$env:APPVEYOR_ACCOUNT_NAME/$env:APPVEYOR_PROJECT_SLUG" -Method GET -Headers @{
        "Authorization" = "Bearer $env:TRAVIS_API_TOKEN"
        "Content-type"  = "application/json"
    }
}

function Get-AppveyorBuild {
    param()

    if (-not ($env:APPVEYOR_API_TOKEN)) {
        throw "missing api token for Travis."
    }

    Invoke-RestMethod -Uri "https://ci.appveyor.com/api/projects/$env:APPVEYOR_ACCOUNT_NAME/$env:APPVEYOR_PROJECT_SLUG" -Method GET -Headers @{
        "Authorization" = "Bearer $env:APPVEYOR_API_TOKEN"
        "Content-type"  = "application/json"
    }
}

function allJobsFinished {
    param()
    $buildData = Get-AppVeyorBuild
    $lastJob = ($buildData.build.jobs | Select-Object -Last 1).jobId

    if ($lastJob -ne $env:APPVEYOR_JOB_ID) {
        return $false
    }

    write-host "Waiting for other jobs to complete"

    [datetime]$stop = ([datetime]::Now).AddMinutes($env:TimeOutMins)

    do {
        (Get-AppVeyorBuild).build.jobs | Where-Object {$_.jobId -ne $env:APPVEYOR_JOB_ID} | Foreach-Object `
            -Begin { $continue = @() } `
            -Progress {
                $job = $_
                switch ($job.status) {
                    "failed" { throw "AppVeyor's Job ($($job.jobId)) failed." }
                    "success" { $continue += $true; continue }
                    Default { $continue += $false; Write-Host "new state: $_.status" }
                }
            } `
            -End { if ($false -notin $continue) { return $true } }
        Start-sleep 5
    } while (([datetime]::Now) -lt $stop)

    throw "Test jobs were not finished in $env:TimeOutMins minutes"
}
