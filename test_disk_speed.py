import os
import time
import shutil

def test_write_speed(file_path, size_mb=100):
    """Test write speed by writing a file of size_mb MB."""
    print(f"Testing write speed ({size_mb} MB)...")
    data = os.urandom(1024 * 1024)  # 1 MB of random data
    start_time = time.time()
    
    with open(file_path, 'wb') as f:
        for _ in range(size_mb):
            f.write(data)
            
    end_time = time.time()
    duration = end_time - start_time
    speed = size_mb / duration
    print(f"Write Speed: {speed:.2f} MB/s")
    return speed

def test_read_speed(file_path, size_mb=100):
    """Test read speed by reading the file."""
    print(f"Testing read speed ({size_mb} MB)...")
    start_time = time.time()
    
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(1024 * 1024)
            if not data:
                break
                
    end_time = time.time()
    duration = end_time - start_time
    speed = size_mb / duration
    print(f"Read Speed: {speed:.2f} MB/s")
    return speed

import argparse

def main():
    parser = argparse.ArgumentParser(description="Test disk speed")
    parser.add_argument("--path", type=str, default=os.getcwd(), help="Path to the directory to test (default: current directory)")
    parser.add_argument("--size", type=int, default=1000, help="Size in MB to write/read (default: 1000)")
    args = parser.parse_args()

    # Use the provided path
    base_dir = args.path
    if not os.path.exists(base_dir):
        print(f"Error: Path '{base_dir}' does not exist.")
        return

    filename = "test_disk_speed_temp.dat"
    file_path = os.path.join(base_dir, filename)
    size_mb = args.size 
    
    print(f"Testing disk speed at: {file_path}")
    
    try:
        write_bps = test_write_speed(file_path, size_mb)
        
        # Clear OS cache to ensure we are reading from disk
        if os.name == 'posix':
            # This requires root, skipping clear cache for user script
            # print("Clearing disk cache (requires sudo)...")
            # os.system('sync; echo 3 > /proc/sys/vm/drop_caches') 
            pass
            
        read_bps = test_read_speed(file_path, size_mb)
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            print("Temporary file removed.")

if __name__ == "__main__":
    main()
