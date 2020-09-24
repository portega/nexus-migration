import os, sys, requests, argparse, shutil

FILE_TYPES = {
    "maven2" : [".jar", ".pom"],
    "npm"    : [".tgz"]
}
source_repo = 'http://localhost:8081'
dest_repo = 'http://localhost:8081'

##### Save current token to file #####
def saveToken():
    with open('migration.properties', 'w') as fd:
        fd.write('last.token=' + token)
        fd.close()

##### Validate folders in path function #####
def checkPath(path):
    if os.path.exists(path) and os.path.isdir(path):
        return
    dirList = path.split("/")
    checkedPath = ""
    for x in dirList:
        if checkedPath == "":
            checkedPath = x
        else:
            checkedPath = checkedPath +  "/" + x
        if os.path.exists(checkedPath) and not os.path.isdir(checkedPath):
            print("Removing wrong file: " + checkedPath)
            os.remove(checkedPath)
            break

##### Filter valid file types according to repo type #####
def isValidFileType(filePath, format):
    isTypeOK = False
    extension = os.path.splitext(filePath)[1]

    if format in FILE_TYPES and extension:
        isTypeOK = extension in FILE_TYPES[format]

    return isTypeOK

##### Download file from repo #####
def download_file(filePath, fileUrl):
    filename = os.path.split(filePath)[1]
    if not isValidFileType(filePath, repoType):
        #print("Discarded file: " + filename)
        return False

    # DOWNLOAD
    print("Getting file " + filename)
    if os.path.isdir(filePath):
        print("Wrong file, skipping")
        return False

    r = requests.get(fileUrl)
    pathFolders = os.path.dirname(filePath)

    checkPath(pathFolders)
    if not os.path.exists(pathFolders):
        os.makedirs(pathFolders)
    with open(filePath, 'wb') as fd:
        fd.write(r.content)
        fd.close()
    return True

##### Maven Download function #####
def downloadMaven(repo, token, targetRepoName):
    url = source_repo + '/service/rest/beta/components?repository=' + repo
    uploadUrl = dest_repo + '/service/rest/v1/components?repository=' + targetRepoName

    if token != "":
        url = url + "&continuationToken=" + token
        print("Token: " + token)

    print("Getting components list")
    r = requests.get(url)
    r.raise_for_status()

    jsonData = r.json()

    for x in jsonData["items"]:
        group = x["group"]
        name = x["name"]
        version = x["version"]
        print ("Component " + group + ":" + name + ":" + version)
        payload = {
                "maven2.groupId": (None, group),
                "maven2.artifactId": (None, name),
                "maven2.version": (None, version),
        }
        nfiles = 0
        for y in x["assets"]:
            filePath = repo + "/" + y["path"]
            fileUrl = y["downloadUrl"]

            if not download_file(filePath, fileUrl):
                continue
            nfiles += 1
            extension = os.path.splitext(filePath)[1]
            filename = os.path.split(filePath)[1]
            nasset = "maven2.asset" + str(nfiles)
            payload[nasset] = (filename, open(filePath, 'rb'))
            payload[nasset + ".extension"] = (None, extension[1:])
            if extension == ".jar":
                if filename.endswith("sources.jar"):
                    payload[nasset + ".classifier"] = (None, "sources")
                elif filename.endswith("javadoc.jar"):
                    payload[nasset + ".classifier"] = (None, "javadoc")

        # UPLOAD
        print("Uploading: ", end=' ')
        r = requests.post(uploadUrl,
            auth = ('admin', 'admin123'),
            files = payload
        )
        print(r.status_code)
        if r.status_code in [200, 204, 400]:
            shutil.rmtree(os.path.split(filePath)[0])

    return jsonData["continuationToken"]


##### NPM Download function #####
def downloadNPM(repo, token, targetRepoName):
    url = source_repo + '/service/rest/beta/assets?repository=' + repo
    uploadUrl = dest_repo + '/service/rest/v1/components?repository=' + targetRepoName

    if token != "":
        url = url + "&continuationToken=" + token
        print("Token: " + token)

    print("Getting asset list")
    r = requests.get(url)
    r.raise_for_status()

    jsonData = r.json()

    for x in jsonData["items"]:
        filePath = repo + "/" + x["path"]
        fileUrl = x["downloadUrl"]

        if not download_file(filePath, fileUrl):
            continue

        # UPLOAD
        print("Uploading: ", end=' ')
        r = requests.post(uploadUrl,
            auth=('admin', 'admin'),
            files={'npm-asset': open(filePath, 'rb')}
        )
        print(r.status_code)
        if r.status_code in [200, 204, 400]:
            os.remove(filePath)

    return jsonData["continuationToken"]

##### MAIN #####
ap = argparse.ArgumentParser(description="Nexus repository migration through assets API")
ap.add_argument("repo", type=str, help="name of the origin repo")
ap.add_argument("-t", "--token", required=False,
   help="continuation token from asset list")
ap.add_argument("-d", "--destination", required=False,
   help="destination repo (if it has a different name than origin)")
ap.add_argument("type", type=str, help="type of repo (maven2, npm)")

args = vars(ap.parse_args())
repo = args['repo']
targetRepoName = args['destination']
repoType = args['type']

if not os.path.exists(repo):
    os.mkdir(repo)
    os.chdir(repo)

token = ""
if args['token']:
    token = args['token']

if not targetRepoName:
    targetRepoName = repo

while token is not None:
    saveToken()
    if repoType == "npm":
        token = downloadNPM(repo, token, targetRepoName)
    elif repoType == "maven2":
        token = downloadMaven(repo, token, targetRepoName)
    else:
        print("Repo type not implemented")
