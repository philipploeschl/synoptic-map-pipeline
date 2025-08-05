import os, sys
from datetime import datetime
import config
import subprocess
import glob



def create_session_folder():
    """
    Creates a session folder named CRXXXX_<timestamp>, writes the path to a file,
    and returns the full path.
    """

    # Set this to your project’s output base directory
    root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    output_base = os.path.join(root_path, config.output_path)
    session_path_file = os.path.join(output_base, "session_path.txt")

    cr_str = f"{config.cr:04d}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    id = f"{config.id}"
    folder_name = f"CR{cr_str}_{id}_{timestamp}"
    session_folder = os.path.join(output_base, folder_name)

    script_folder = os.path.join(session_folder, config.script_path)
    log_folder    = os.path.join(session_folder, config.log_path)
    data_folder   = os.path.join(session_folder, config.data_path)
    jsd_folder    = os.path.join(session_folder, config.jsd_path)

    os.makedirs(script_folder, exist_ok=True)       
    os.makedirs(log_folder,    exist_ok=True)
    os.makedirs(data_folder,   exist_ok=True)
    os.makedirs(jsd_folder,    exist_ok=True)
    
    # Save path to session_path.txt
    with open(session_path_file, "w") as f:
        f.write(session_folder)

    return session_folder


def get_current_session_folder():
    """
    Returns the most recently created session folder, or None if not found.
    """

    root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    output_base = os.path.join(root_path, config.output_path)
    session_path_file = os.path.join(output_base, "session_path.txt")

    if not os.path.exists(session_path_file):
        return None
    with open(session_path_file) as f:
        return f.read().strip()
    


    
def run_script_with_nohup(session_path, script_name):
    script_path = os.path.join(session_path, config.script_path, script_name)
    log_path    = os.path.join(session_path, config.log_path, script_name.replace('.sh', '.log'))
    pid_path    = os.path.join(session_path, config.log_path, script_name.replace('.sh', '.pid'))

    # Ensure the script is executable
    subprocess.call(['chmod', '755', script_path])

    # Run the script in background with nohup and capture its PID
    cmd = f'nohup {script_path} > {log_path} 2>&1 & echo $! > {pid_path}'
    subprocess.call(cmd, shell=True)



def find_sh_scripts(directory, prefix=''):
    """Find all .sh files in the given directory."""
    return sorted(glob.glob(os.path.join(directory, '%s*.sh'%prefix)))


def run_all_scripts(verbose=False, prefix=''):


    session_folder = get_current_session_folder()
    outpath_scripts = os.path.join(session_folder, config.script_path)
    outpath_logs    = os.path.join(session_folder, config.log_path)

    # --- Find all .sh scripts in the directory ---
    scripts = find_sh_scripts(outpath_scripts, prefix)
    processes = []

    try:
        for script_path in scripts:
            script_name = os.path.basename(script_path)
            log_path = os.path.join(outpath_logs, script_name.replace('.sh', '.log'))
            pid_path = os.path.join(outpath_logs, script_name.replace('.sh', '.pid'))

            # Make script executable
            subprocess.call(['chmod', '755', script_path])

            # Open log file
            log_file = open(log_path, 'w')

            # Launch script
            if verbose: print('Running %s... Check %s for progress.' %(script_name, config.log_path))
            p = subprocess.Popen([script_path], stdout=log_file, stderr=subprocess.STDOUT)
            processes.append(p)

            # Save PID
            with open(pid_path, 'w') as f:
                f.write(str(p.pid))

        # Optional: wait for all to complete
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("Caught Ctrl+C! Terminating subprocesses...")
        for p in processes:
            p.terminate()  # Or p.kill() if needed
            
        print("All subprocesses terminated.")


if __name__ == "__main__":
    # Example usage
    #create_cr_session_folder()
    session = get_current_session_folder()
    print(session)