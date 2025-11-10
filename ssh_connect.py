import time
import hashlib
import argparse
import HelperFunctions as Hf

Hf.Check_Install("paramiko")
import paramiko      


ssh_ConfigFile = 'ssh_connect.json' #Inputs for ssh connection
ssh_Cfg = None
ssh_Cfg = Hf.ReadConfig(Hf.getRelativePath(ssh_ConfigFile))

parser = argparse.ArgumentParser(description="SSH ECU Utility")
parser.add_argument("--deploy", help="Path to application to deploy")
parser.add_argument("--start-recording", action="store_true", help="Start ByteSoup recording")
parser.add_argument("--stop-recording", action="store_true", help="Stop ByteSoup recording")
parser.add_argument("--transfer", action="store_true", help="Transfer .bytesoup file")
args = parser.parse_args()

def connect_to_ecu():
    """Establish SSH connection to QNX ECU with retry logic."""
    ssh = paramiko.SSHClient()
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

def deploy_application(ssh, app_path):
    """Deploy application to ECU and run multiple shell scripts with retries and error handling."""
    try:
        sftp = ssh.open_sftp()
        sftp.put(app_path, ssh_Cfg["remote_app_path"])
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
        sftp.put(app_path, ssh_Cfg["remote_app_path"])
        sftp.close()

        shell_script_path = ssh_Cfg.get(ssh_Cfg["recording_script"])
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


def stop_recording():
    for attempt in range(ssh_Cfg["MAX_RETRIES"]):
        try:
            print(f"🔁 Attempt {attempt+1} to stop recording...")
            ssh = connect_to_ecu()
            channel = ssh.get_transport().open_session()
            channel.get_pty()
            channel.invoke_shell()

            print("Sending Ctrl+C...")
            channel.send('\x03')  # Ctrl+C
            time.sleep(1)

            output = channel.recv(1024).decode()
            print("📋 Command output after Ctrl+C:\n", output)

            channel.close()
            ssh.close()
            print("✅ Recording stopped and SSH connection closed.")
            return
        except Exception as e:
            print(f"❌ Attempt {attempt+1} failed: {e}")
            time.sleep(ssh_Cfg["RETRY_DELAY"])

    print("❌ All attempts to stop recording failed.")

def transfer_file(ssh):
    """Transfer .bytesoup file with retry, integrity check, and user-defined copy path."""
    custom_path = ssh_Cfg["COPY_DESTINATION"]

    for attempt in range(ssh_Cfg["MAX_RETRIES"]):
        try:
            sftp = ssh.open_sftp()
            sftp.get(ssh_Cfg["REMOTE_FILE"], ssh_Cfg["LOCAL_FILE"])
            sftp.close()
            print("✅ File transferred successfully.")

            verify_file_integrity(ssh_Cfg["LOCAL_FILE"])

            if custom_path:
                shutil.copy2(ssh_Cfg["LOCAL_FILE"], custom_path)
                print(f"✅ File copied to {custom_path}")
            else:
                print("⚠️ No destination path provided. Skipping copy.")
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
            deploy_application(ssh, ssh_Cfg["remote_app_path"])
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



