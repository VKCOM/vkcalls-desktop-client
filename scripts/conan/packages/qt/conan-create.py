import getopt
import os
import shutil
import sys
import yaml
import patch


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def addCustomVersions(originalFilePath, customFilePath):
    def getPatchesRecursively(version):
        if version in cache:
            return cache[version]
        if version in versionToBase:
            patches = getPatchesRecursively(versionToBase[version]) + customData['patches'][version]
        else:
            patches = originalData['patches'][version]
        cache[version] = patches
        return patches

    with open(originalFilePath) as originalFile:
        originalData = yaml.load(originalFile, Loader=yaml.FullLoader)
    with open(customFilePath) as customFile:
        customData = yaml.load(customFile, Loader=yaml.FullLoader)

    versionToBase = customData['base_version']
    cache = dict()
    for version in customData['patches']:
        # updated values
        patches = getPatchesRecursively(version)
        sources = originalData['sources'][baseVersion]

        # update original data
        originalData['patches'][version] = patches
        originalData['sources'][version] = sources

    with open(originalFilePath, 'w') as outfile:
        outfile.write(yaml.dump(originalData, Dumper=NoAliasDumper))


class Defaults:
    @staticmethod
    def version():
        return "5.15.2-p1"

    @staticmethod
    def baseVersion():
        return "5.15.2"

    @staticmethod
    def remote():
        return "conancenter"

    @staticmethod
    def profile():
        return "macos-clang12-debug"

    @staticmethod
    def buildDir():
        return os.path.abspath(os.path.join(".", "build-qt"))

    @staticmethod
    def customDir():
        return os.path.abspath(".")


class Params:
    def __init__(self):
        self.version = Defaults.version()
        self.baseVersion = Defaults.baseVersion()
        self.remote = Defaults.remote()
        self.profile = Defaults.profile()
        self.buildDir = Defaults.buildDir()
        self.customDir = Defaults.customDir()
        self.parse()

    @staticmethod
    def printHelp():
        print("This script dowloads and builds Qt from source with custom patches")
        print("Options:")
        print("-v, --version - target version to build. default is:", Defaults.version())
        print("-r, --remote - conan remote, default is:", Defaults.remote())
        print("-p, --profile - target profile, default is:", Defaults.profile())
        print("-h, --help - print help and exit")
        print("-b, --build-dir - build directory. default is:", Defaults.buildDir())
        print("-c, --custom-dir - directory, containing custom patches. default is:", Defaults.customDir())
        print("-w, --base-version - version to apply custom patches to. default is:", Defaults.baseVersion())

    def parse(self):
        options, arguments = getopt.getopt(
            sys.argv[1:],  # Arguments
            'p:v:r:hb:c:w:',  # Short option definitions
            ["profile=", "version=", "remote=", "help", "build-dir=", "custom-dir=", "base-version="])  # Long option definitions
        for opt, arg in options:
            if opt in ("-v", "--version"):
                self.version = arg
            elif opt in ("-r", "--remote"):
                self.remote = arg
            elif opt in ("-p", "--profile"):
                self.profile = arg
            elif opt in ("-h", "--help"):
                self.printHelp()
                exit()
            elif opt in ("-b", "--build-dir"):
                self.buildDir = arg
            elif opt in ("-c", "--custom-dir"):
                self.customDir = arg
            elif opt in ("-w", "--base-version"):
                self.baseVersion = arg


def downloadConanRecipe(version, remote):
    print("Download conan recipe version = {version}, remote = {remote}".format(version=version, remote=remote))
    cmd = "conan download --recipe qt/{version}@ --remote={remote}".format(version=version, remote=remote)
    assert os.system(cmd) == 0


def copyConanRecipeTo(version, channel):
    print("Copy conan recipe version = {version} to channel = {channel}".format(version=version, channel=channel))
    cmd = "conan copy qt/{version}@ {channel} --force".format(version=version, channel=channel)
    assert os.system(cmd) == 0


def copyFilesFromFolder(fromDir, toDir):
    if not os.path.exists(toDir):
        os.mkdir(toDir)
    for fileName in os.listdir(fromDir):
        fromFile = os.path.join(fromDir, fileName)

        toFile = os.path.join(toDir, fileName)
        if os.path.isfile(fromFile):
            print("from", fromFile, "to", toFile)
            shutil.copy(fromFile, toFile)
        else:
            copyFilesFromFolder(os.path.join(fromDir, fileName), os.path.join(toDir, fileName))


def createBuildDir(buildDir, version):
    print("Create buildDir = {buildDir} for version = {version}".format(buildDir=buildDir, version=version))
    if os.path.exists(buildDir):
        os.remove(buildDir)
    os.mkdir(buildDir)
    homeDir = os.path.expanduser("~")
    fromDir = os.path.join(homeDir, ".conan", "data", "qt", version, "_", "_", "export")
    copyFilesFromFolder(fromDir, buildDir)


def patchConanFile(buildDir, customDir):
    # patch is applied to a file in current working directory
    os.chdir(buildDir)

    patchesDir = os.path.join(customDir, "conanfile-patches")
    for patchFileName in sorted(os.listdir(patchesDir)):
        print("Applying conanfile patch: {patch}".format(patch=patchFileName))
        patchSet = patch.fromfile(os.path.join(patchesDir, patchFileName));
        patchSet.apply()


def addCustomPatches(buildDir, customDir):
    print("Add custom patches to buildDir = {buildDir} from customDir = {customDir}".format(buildDir=buildDir, customDir=customDir))
    copyFilesFromFolder(os.path.join(customDir, "patches"), os.path.join(buildDir, "patches"))
    originalYmlPath = os.path.join(buildDir, "conandata.yml")
    customYmlPath = os.path.join(customDir, "custom-versions.yml")
    addCustomVersions(originalYmlPath, customYmlPath)


def configByVersion(version):
    return "qtmodules{}.conf".format(version)


def conanCreate(buildDir, version, profile):
    shutil.copy(os.path.join(buildDir, configByVersion(baseVersion)), os.path.join(buildDir, configByVersion(version)))
    print("Call conan create with buildDir = {buildDir} version = {version} profile = {profile}".format(buildDir=buildDir, version=version, profile=profile))
    if sys.platform.startswith('win32'):
        formatStr = ("conan create {buildDir} qt/{version}@vkcalls/stable --profile={profile} --json info.json"
            " -o qt:shared=True"
            " -o qt:qtmultimedia=True"
            " -o qt:qtsvg=True"
            " -o qt:qttools=True"
            " -o qt:qttranslations=True"
            " -o qt:with_glib=False"
            " -o qt:with_harfbuzz=False"
            " -o qt:opengl=dynamic"
            " -o qt:qtwinextras=True")
    else:
        formatStr = ("conan create {buildDir} qt/{version}@vkcalls/stable --profile={profile} --json info.json"
            " -o qt:shared=True"
            " -o qt:qtmultimedia=True"
            " -o qt:qtsvg=True"
            " -o qt:qttools=True"
            " -o qt:qttranslations=True"
            " -o qt:qtmacextras=True")
    cmd = formatStr.format(buildDir=buildDir, version=version, profile=profile)
    assert os.system(cmd) == 0


if __name__ == "__main__":
    # parse params
    params = Params()
    version = params.version
    remote = params.remote
    profile = params.profile
    buildDir = params.buildDir
    customDir = params.customDir
    baseVersion = params.baseVersion

    # do job
    downloadConanRecipe(baseVersion, remote)
    copyConanRecipeTo(baseVersion, "vkcalls/stable")
    createBuildDir(buildDir, baseVersion)
    patchConanFile(buildDir, customDir)
    addCustomPatches(buildDir, customDir)
    conanCreate(buildDir, version, profile)
