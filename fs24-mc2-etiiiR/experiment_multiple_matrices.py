
import numpy as np
import cupy as cp
import time
import matplotlib.pyplot as plt
import subprocess
import cupy.cuda.nvtx as nvtx
from tqdm import tqdm

# Define the kernel for batch SVD reconstruction
kernel_code = """
extern "C" __global__
void reconstruct_svd(const float* u, const float* s, const float* vt, float* C,
            int rows_u, int cols_u, int rows_vt, int cols_vt, int k)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int j = blockIdx.y * blockDim.y + threadIdx.y;

    if (i >= rows_u || j >= cols_vt) {
        return;
    }

    float sum = 0;
    for (int l = 0; l < k; ++l) {
        sum += u[i * cols_u + l] * s[l] * vt[l * cols_vt + j];
    }
    C[i * cols_vt + j] = sum;
}
"""

reconstruct_svd_kernel = cp.RawKernel(kernel_code, "reconstruct_svd")

def reconstruct_svd_gpu_parallel(u, s, vt, k, stream):
    rows_u, cols_u = u.shape
    rows_vt, cols_vt = vt.shape

    with stream:
        u_gpu = cp.asarray(u, dtype=cp.float32)
        s_gpu = cp.asarray(s, dtype=cp.float32)
        vt_gpu = cp.asarray(vt, dtype=cp.float32)
        C_gpu = cp.zeros((rows_u, cols_vt), dtype=cp.float32)

        threads_per_block = (32, 32)
        blocks_per_grid_x = math.ceil(rows_u / threads_per_block[0])
        blocks_per_grid_y = math.ceil(cols_vt / threads_per_block[1])
        blocks_per_grid = (blocks_per_grid_x, blocks_per_grid_y)

        reconstruct_svd_kernel(
            blocks_per_grid,
            threads_per_block,
            (u_gpu, s_gpu, vt_gpu, C_gpu, rows_u, cols_u, rows_vt, cols_vt, k),
            stream=stream
        )

    return C_gpu

def generate_random_matrices(matrix_size, num_matrices):
    matrices = [np.random.rand(matrix_size, matrix_size).astype(np.float32) for _ in range(num_matrices)]
    svd_results = [np.linalg.svd(matrix, full_matrices=False) for matrix in matrices]
    u_batch = np.array([u[:, :17] for u, s, vt in svd_results])
    s_batch = np.array([s[:17] for u, s, vt in svd_results])
    vt_batch = np.array([vt[:17, :] for u, s, vt in svd_results])
    return matrices, u_batch, s_batch, vt_batch

def monitor_gpu_usage(duration=10, interval=1):
    gpu_usage = []
    start_time = time.time()
    while time.time() - start_time < duration:
        usage = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ]
        )
        gpu_usage.append(int(usage.decode("utf-8").strip()))
        time.sleep(interval)
    return gpu_usage

def reconstruct_multiple_matrices(matrices, u_batch, s_batch, vt_batch):
    streams = [cp.cuda.Stream() for _ in range(len(matrices))]
    C_gpu_results = []

    nvtx.RangePush("Reconstruction")
    start_event = cp.cuda.Event()
    end_event = cp.cuda.Event()
    start_event.record()

    # Launch kernels in parallel using multiple streams
    for i in range(len(matrices)):
        stream = streams[i]
        with stream.use():
            nvtx.RangePush(f"Matrix_{i}_Reconstruction")
            C_gpu = reconstruct_svd_gpu_parallel(u_batch[i], s_batch[i], vt_batch[i], 17, stream)
            C_gpu_results.append(C_gpu)
            nvtx.RangePop()

    # Wait for all streams to finish
    for stream in streams:
        stream.synchronize()

    end_event.record()
    end_event.synchronize()
    reconstruction_time = cp.cuda.get_elapsed_time(start_event, end_event)
    nvtx.RangePop()

    print(f"Reconstruction time: {reconstruction_time / 1000:.2f} seconds")  # convert ms to seconds
    return C_gpu_results

def main():
    matrix_sizes = [256, 512, 1024, 2048, 4096]  # Define different matrix sizes
    num_matrices = 10  # Number of matrices to generate for each size
    gpu_usages = []

    for size in matrix_sizes:
        print(f"Processing matrices of size {size}x{size}")
        matrices, u_batch, s_batch, vt_batch = generate_random_matrices(size, num_matrices)
        for _ in range(5):  # Run the reconstruction 5 times for averaging
            nvtx.RangePush(f"Reconstruct_Matrices_Size_{size}")
            reconstructed_matrices = reconstruct_multiple_matrices(matrices, u_batch, s_batch, vt_batch)
            nvtx.RangePop()

            nvtx.RangePush("Monitor_GPU_Usage")
            gpu_usage = monitor_gpu_usage(duration=5, interval=1)
            nvtx.RangePop()
            gpu_usages.append((size, gpu_usage))

    # Plot GPU usage
    plt.figure(figsize=(12, 6))
    for size, usage in gpu_usages:
        plt.plot(range(len(usage)), usage, label=f'Matrix Size: {size}x{size}')

    plt.xlabel('Time (s)')
    plt.ylabel('GPU Usage (%)')
    plt.title('GPU Usage by Matrix Size')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()
