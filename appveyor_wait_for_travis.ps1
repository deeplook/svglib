function Get-TravisBuild {
    param()

    if (-not ($env:TRAVIS_API_TOKEN)) {
        throw "missing api token for Travis-CI."
    }
    if (-not ($env:APPVEYOR_ACCOUNT_NAME)) {
        throw "not an appveyor build."
    }

    Invoke-RestMethod -Uri "https://api.travis-ci.org/builds?limit=10" -Method Get -Headers @{
        "Authorization"      = "token $env:TRAVIS_API_TOKEN"
        "Travis-API-Version" = "3"
    }
}
function allCIsFinished {
    param()

    if (-not ($env:APPVEYOR_REPO_COMMIT)) {
        return $true
    }

    Write-Host "waiting on travis to finish"

    [datetime]$stop = ([datetime]::Now).AddMinutes($env:TimeOutMins)

    do {
        $builds = Get-TravisBuild
        $currentBuild = $builds.builds | Where-Object {$_.commit.sha -eq $env:APPVEYOR_REPO_COMMIT}
        switch -regex ($currentBuild.state) {
            "^passed$" {
                return $true
            }
            "^(errored|failed|canceled)" {
                throw "Travis Job ($($builds.builds.id)) failed"
            }
        }

        Start-sleep 5
    } while (([datetime]::Now) -lt $stop)
    if (!$currentBuild) {
        throw "Could not get information about Travis build with sha $REPO_COMMIT"
    }

    throw "Travis build did not finished in $env:TimeOutMins minutes"
}
