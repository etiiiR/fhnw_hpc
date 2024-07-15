import numpy as np
import multiprocessing
import time

# Define colors for console output
process_colors = {
    0: "\033[91m",  # Red
    1: "\033[92m",  # Green
    2: "\033[93m",  # Yellow
    3: "\033[94m",  # Blue
}

def init_globals(lock_, shared_array_, size_, progress_, total_):
    global lock, shared_array, size, progress, total
    lock = lock_
    shared_array = shared_array_
    size = size_
    progress = progress_
    total = total_

def add_block(start_idx, end_idx, block):
    with lock:
        shared_array[start_idx:end_idx] = block

def update_progress():
    with progress.get_lock():
        progress.value += 1

def reconstruct_svd_multiprocessing(u, s, vt, k, start_row, end_row):
    """SVD reconstruction for k components using multiprocessing"""
    local_block = np.zeros((end_row - start_row, vt.shape[1]))
    for i, row_idx in enumerate(range(start_row, end_row)):
        local_block[i, :] = np.dot(u[row_idx, :k] * s[:k], vt[:k, :])
    start_idx = start_row * size[1]
    end_idx = end_row * size[1]
    add_block(start_idx, end_idx, local_block.flatten())
    update_progress()

def print_progress(progress, total):
    while True:
        with progress.get_lock():
            if progress.value >= total.value:
                break
            print(f"Progress: {progress.value}/{total.value}")
        time.sleep(1)
    print(f"Progress: {progress.value}/{total.value}")
    
    
def main(u, s, vt, k):
    size = (u.shape[0], vt.shape[1])

    # Shared array and lock for multiprocessing
    shared_array = multiprocessing.Array('d', size[0] * size[1])
    lock = multiprocessing.Lock()

    # Initialize the process pool
    n_processes = len(process_colors)

    # Progress tracking
    progress = multiprocessing.Value('i', 0)
    total = multiprocessing.Value('i', n_processes)

    pool = multiprocessing.Pool(processes=n_processes, initializer=init_globals, initargs=(lock, shared_array, size, progress, total))

    # Define the chunk size for each process
    chunk_size = size[0] // n_processes
    ranges = [(i * chunk_size, (i + 1) * chunk_size) for i in range(n_processes)]
    if size[0] % n_processes != 0:  # Handle remainder rows
        ranges[-1] = (ranges[-1][0], size[0])

    # Start progress printing in a separate process
    progress_printer = multiprocessing.Process(target=print_progress, args=(progress, total))
    progress_printer.start()

    # Start the multiprocessing pool and execute
    start_time = time.time()
    pool.starmap(reconstruct_svd_multiprocessing, [(u, s, vt, 20, start, end) for start, end in ranges])
    pool.close()
    pool.join()

    # Ensure progress printer finishes
    progress_printer.join()

    # Convert shared array back to numpy array
    reconstructed_matrix = np.frombuffer(shared_array.get_obj()).reshape(size)

    # Display results
    print("Reconstructed matrix with Multiprocessing:")
    print(reconstructed_matrix)
    print("Execution time: %s seconds" % (time.time() - start_time))
    return reconstructed_matrix, time.time() - start_time


if __name__ == "__main__":
    print("Running main function")