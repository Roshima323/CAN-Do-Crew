import subprocess,sys
import json
import os

def Check_Install(package):
    installed_packages = [r.decode().split('==')[0] for r in subprocess.check_output([sys.executable, '-m', 'pip', 'freeze']).split()]
    if package not in installed_packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])  #Package not found ! Installing is ongoing ...  


#To read input json file
def ReadConfig(ConfigFilePath):
    local_cfg = None
    with open(ConfigFilePath) as json_file:
        local_cfg = json.load(json_file)
    return local_cfg

#to get relative path
def getRelativePath(rpath):
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)

    return os.path.join(application_path, rpath)  
