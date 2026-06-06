from sklearn.datasets import load_wine, fetch_openml
from sklearn.utils import Bunch
import time, os
from datetime import datetime


def load_ds1():
    return load_wine()

def load_ds2():
    fmnist = fetch_openml(data_id=40996, as_frame=False, parser='auto')
    
    # Return as a Bunch object for that classic sklearn feel
    return Bunch(
        data=fmnist.data[:5000],
        target=fmnist.target.astype(int)[:5000],
        target_names=[
            "T-shirt/top", "Trouser", "Pullover", "Dress", "Coat",
            "Sandal", "Shirt", "Sneaker", "Bag", "Ankle boot"
        ],
        DESCR=fmnist.DESCR,
        feature_names=fmnist.feature_names
    )


class StudyLogger:
    def __init__(self, log_file="user_study_log1.txt"):
        self.log_file = log_file
        self.start_time = None
        # We don't rely only on run_count memory to allow restarts

    def start_timer(self):
        if self.start_time is None:
            self.start_time = time.time()

    def log(self, params, ari):
        # Read existing lines
        lines = []
        if os.path.exists(self.log_file):
            with open(self.log_file, "r") as f:
                lines = f.readlines()
        
        # Filter out old summary and find best ARI so far
        marker = "--- SUMMARY ---\n"
        data_lines = []
        best_ari = -1.0
        
        for line in lines:
            if line == marker:
                break
            data_lines.append(line)
            # Parse ARI for history
            if "ARI=" in line:
                try:
                    # distinct marker to safe split
                    part = line.split("ARI=")[1].strip()
                    # remove any trailing brace or newline if dict printing messed up
                    # but simple float parse usually works if it's the last item
                    val = float(part)
                    if val > best_ari:
                        best_ari = val
                except:
                    pass
        
        # Check current ARI
        if ari > best_ari:
            best_ari = ari
            
        # Append new entry
        new_line = f"{datetime.now()}: Params={params}, ARI={ari}\n"
        data_lines.append(new_line)
        
        # Count vars
        run_count = sum(1 for l in data_lines if 'ARI=' in l)
        
        # Write back
        with open(self.log_file, "w") as f:
            f.writelines(data_lines)
            f.write(marker)
            f.write(f"Best ARI: {best_ari}\n")
            f.write(f"Total Runs: {run_count}\n")

    def get_elapsed_time(self):
        if self.start_time is None:
            return "0:00"
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes}:{seconds:02d}"

    def get_run_count(self):
        # Check file for accurate count across restarts
        if os.path.exists(self.log_file):
            with open(self.log_file, "r") as f:
                content = f.read()
            return content.count("ARI=")
        return 0