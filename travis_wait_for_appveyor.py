import os
import requests
import time

def fetch_appveyor_build(url, headers, params, commit_sha):
    res = requests.get(url, headers=headers, params=params)
    assert res.status_code == 200, 'Could not fetch appveyor build. Code %d. Reason %s' % (res.status_code, res.json())

    # Identify proper appveyor build
    body = res.json()
    appveyor_builds = body['builds']
    build = [b for b in appveyor_builds if commit_sha in b['commitId']]

    assert len(build) != 0, 'Found no appveyor builds with SHA %s' % commit_sha
    # Keep only most recent build for given commit
    build = build[0]
    print('Syncing with Appveyor build %s' % build['version'])
    return build

def main():
    assert os.environ['TRAVIS'] == 'true'
    assert 'APPVEYOR_AUTH_TOKEN' in os.environ and os.environ['APPVEYOR_AUTH_TOKEN'] is not None
    assert 'APPVEYOR_USER' in os.environ and os.environ['APPVEYOR_USER'] is not None

    TRAVIS_JOB_NUMBER = os.environ['TRAVIS_JOB_NUMBER'] # Something like '42.1'
    APPVEYOR_AUTH_TOKEN = os.environ['APPVEYOR_AUTH_TOKEN']
    COMMIT_SHA = os.environ['TRAVIS_COMMIT'] # Something like '542c7f62'
    BRANCH = os.environ['TRAVIS_BRANCH']

    APPVEYOR_USER = os.environ['APPVEYOR_USER']
    APPVEYOR_PROJECT = os.environ['TRAVIS_REPO_SLUG'].split('/')[-1]

    job_index = int(TRAVIS_JOB_NUMBER.split('.')[1])

    if job_index != 1:
        print('Job index is %d not 1. Not waiting for appveyor here.' % job_index)
        return

    url = "https://ci.appveyor.com/api/projects/%s/%s/history" % (APPVEYOR_USER, APPVEYOR_PROJECT)
    params = {
        'recordsNumber': '100',
        'branch': BRANCH
    }
    headers = {
        'Authorization': 'Bearer %s' % APPVEYOR_AUTH_TOKEN,
        "Content-type": "application/json"
    }

    print('Searching lastest build for commit SHA %s in appveyor project %s' % (COMMIT_SHA, APPVEYOR_PROJECT))

    for i in range(30):
        build = fetch_appveyor_build(url, headers, params, COMMIT_SHA)

        if build['status'] == 'success':
            print('Build has finished with %s' % build['finished'])
            return
        elif build['status'] == 'failure':
            raise RuntimeError('Appveyor build has failed.')
        else:
            print('Appveyor build status: %s' % build['status'])
            print('Retrying in 60 secs')
            time.sleep(60)

if __name__ == '__main__':
    main()
