import time
import hashlib
import argparse
import os
import shutil
import subprocess
import HelperFunctions as Hf
Hf.Check_Install("paramiko") # install paramiko python package if it is missing.
import paramiko      


ssh_ConfigFile = 'ssh_connect.json' #Inputs for ssh connection available in json
ssh_Cfg = None
ssh_Cfg = Hf.ReadConfig(Hf.getRelativePath(ssh_ConfigFile)) # read the json inputs to ssh_cfg

#arguments for ssh_connect 
parser = argparse.ArgumentParser(description="SSH Controller Utility")
parser.add_argument("--deploy", help="Copy and deploy applications to start bytesoup recording")
parser.add_argument("--start-recording", action="store_true", help="Start ByteSoup recording")
parser.add_argument("--stop-recording", action="store_true", help="Stop ByteSoup recording")
parser.add_argument("--transfer", action="store_true", help="Transfer .bytesoup file")
args = parser.parse_args()
KNOWN_HOSTS_PATH = os.path.expanduser(sh_Cfg["KNOWN_HOSTS_PATH"]) #path where known hosts are stored

def connect_to_ecu():
    """Establish SSH connection to QNX ECU with retry logic."""
    ssh = paramiko.SSHClient()
    ssh.load_host_keys(KNOWN_HOSTS_PATH) #load known hosts to avoid fingerprint issue when connecting to the IP   

    host_keys = ssh.get_host_keys()
    if ssh_Cfg["ECU_IP"] in host_keys:
        print(f"Host  found in known hosts. Using RejectPolicy.")
        ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        print(f"Host NOT found in known hosts. Using AutoAddPolicy.")
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


    for attempt in range(ssh_Cfg["MAX_RETRIES"]):
        try:
            ssh.connect(ssh_Cfg["ECU_IP"], port=ssh_Cfg["ECU_PORT"], username=ssh_Cfg["USERNAME"], password=ssh_Cfg["PASSWORD"] , timeout=10)
            print("✅ Connected to ECU successfully.")
            return ssh
        except Exception as e:
            print(f"❌ Connection attempt {attempt+1} failed: {e}")
            time.sleep(ssh_Cfg["RETRY_DELAY"])
    raise ConnectionError("Failed to connect to ECU after multiple attempts.")


def copy_applications(ssh):
    """Copy multiple application files to ECU before deployment."""
    try:
        sftp = ssh.open_sftp()
        remote_dir = ssh_Cfg["remote_app_dir"]
        
        # Ensure remote directory exists
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            ssh.exec_command(f"mkdir -p {remote_dir}")
            print(f"✅ Created remote directory: {remote_dir}")

        app_list = ssh_Cfg.get("applications", [])
        if not app_list:
            print("⚠️ No applications specified in config. Skipping copy.")
            return

        for app_path in app_list:
            if not os.path.exists(app_path):
                print(f"❌ Local file not found: {app_path}")
                continue

            remote_path = os.path.join(remote_dir, os.path.basename(app_path))
            for attempt in range(ssh_Cfg["MAX_RETRIES"]):
                try:
                    print(f"🔁 Copying {app_path} → {remote_path} (Attempt {attempt+1})")
                    sftp.put(app_path, remote_path)
                    print(f"✅ Copied {app_path} to {remote_path}")
                    break
                except Exception as e:
                    print(f"❌ Copy attempt {attempt+1} failed: {e}")
                    time.sleep(ssh_Cfg["RETRY_DELAY"])
            else:
                print(f"❌ Failed to copy {app_path} after multiple attempts.")
        sftp.close()
    except Exception as e:
        print(f"❌ Application copy failed: {e}")


def deploy_application(ssh):
    """Deploy application to ECU and run multiple shell scripts with retries and error handling."""
    copy_applications(ssh) 
    try:
        sftp = ssh.open_sftp()    
        sftp.put(ssh_Cfg["start_script"], ssh_Cfg["start_app_path"])
        sftp.close()
        print("✅ Application deployed to remote path.")
        script_list = ssh_Cfg.get("start_scripts", [])

        if not isinstance(script_list, list) or not script_list:
            print("⚠️ No valid shell scripts found in configuration. Skipping execution.")
            return

        for script_path in script_list:
            if not script_path or not script_path.strip():
                print("⚠️ Skipping empty or invalid script path.")
                continue

            for attempt in range(ssh_Cfg["MAX_RETRIES"]):
                try:
                    command = f"chmod +x {script_path} && {script_path}"
                    stdin, stdout, stderr = ssh.exec_command(command)
                    output = stdout.read().decode()
                    error = stderr.read().decode()

                    if output:
                        print(f"✅ Output from {script_path} (attempt {attempt+1}):\n{output}")
                    if error:
                        print(f"⚠️ Error from {script_path} (attempt {attempt+1}):\n{error}")
                    else:
                        print(f"✅ Script {script_path} executed successfully on attempt {attempt+1}.")
                    break  # Exit retry loop on success
                except Exception as script_error:
                    print(f"❌ Attempt {attempt+1} failed for script {script_path}: {script_error}")
                    time.sleep(ssh_Cfg["RETRY_DELAY"])
            else:
                print(f"❌ All attempts failed for script {script_path}.")
    except Exception as e:
        print(f"❌ Deployment failed: {e}")

def start_recording(ssh):
    """Start ByteSoup recording with error handling."""
    try:
        sftp = ssh.open_sftp()
        sftp.put(ssh_Cfg["recording_script"], ssh_Cfg["recording_app_path"])
        sftp.close()

        shell_script_path = ssh_Cfg["recording_app_path"]
        if not shell_script_path or not shell_script_path.strip():
            print("⚠️ Shell script path is missing or invalid in configuration. Skipping execution.")
            return
        command = f"chmod +x {shell_script_path} && {shell_script_path}"
        stdin, stdout, stderr = ssh.exec_command(command)

        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"⚠️ Shell script warning: {err}")
        else:
            print("✅ Recording started.")
    except Exception as e:
        print(f"❌ Failed to start recording: {e}")

def kill_process_by_name(process_name):
    try:
        subprocess.run(['taskkill', '/F', '/IM', process_name], check=True)
        print(f"Process {process_name} has been successfully killed.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to kill process {process_name}. Error: {e}")

def stop_recording(ssh):
    for attempt in range(ssh_Cfg["MAX_RETRIES"]):
        try:
            print(f"🔁 Attempt {attempt+1} to stop recording...")
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.invoke_shell()

            # Send Ctrl+C to remote process
            print("Sending Ctrl+C to remote process...")
            channel.send('\x03')  # Ctrl+C
            time.sleep(1)

            output = channel.recv(1024).decode(errors='ignore')
            print("📋 Remote output after Ctrl+C:\n", output)

            channel.close()
            ssh.close()
            print("✅ SSH connection closed.")

            # Execute taskkill locally
            print("Executing taskkill locally...")
            kill_process_by_name("OpenConsole.exe")
            print("📋 Local taskkill output:\n", result.stdout or result.stderr)
            return
        except Exception as e:
            print(f"❌ Attempt {attempt+1} failed: {e}")
            time.sleep(ssh_Cfg["RETRY_DELAY"])

    print("❌ All attempts to stop recording failed.")


def transfer_file(ssh):
    """Transfer .bytesoup file with retry"""

    for attempt in range(ssh_Cfg["MAX_RETRIES"]):
        try:
            sftp = ssh.open_sftp()
            sftp.get(ssh_Cfg["REMOTE_FILE"], ssh_Cfg["LOCAL_FILE"])
            sftp.close()
            print("✅ File transferred successfully.")
            return
        except Exception as e:
            print(f"❌ File transfer attempt {attempt+1} failed: {e}")
            time.sleep(ssh_Cfg["RETRY_DELAY"])
    raise IOError("Failed to transfer file after multiple attempts.")


if __name__ == "__main__":
    ssh = None
    try:
        ssh = connect_to_ecu()
        if args.deploy:
            deploy_application(ssh)
        if args.start_recording:
            start_recording(ssh)
        if args.stop_recording:
            stop_recording(ssh)
        if args.transfer:
            transfer_file(ssh)
    except Exception as e:
        print(f"❌ Critical error: {e}")
    finally:
        if ssh:
            ssh.close()
            print("✅ SSH connection closed.")
