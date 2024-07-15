
import cupy.cuda.runtime as cuda_runtime
import cupy.cuda.stream as cuda_stream
import cupy.cuda.nvtx as nvtx
import numpy as np
import cupy as cp
import time
import os
import glob
import imageio.v3 as imageio
from tqdm import tqdm
import matplotlib.pyplot as plt
import math
import timeit

# Define the CUDA kernel code
kernel_code = """
extern "C" __global__
void svd_reconstruction_shared(const float* U, const float* S, const float* V, float* A, int M, int N, int K) {
    // Define the tile size
    const int TILE_SIZE = 32;

    // Shared memory arrays
    __shared__ float Us[TILE_SIZE][TILE_SIZE];
    __shared__ float Ss[TILE_SIZE];
    __shared__ float Vs[TILE_SIZE][TILE_SIZE];

    int tx = threadIdx.x, ty = threadIdx.y;
    int row = blockIdx.y * blockDim.y + ty;
    int col = blockIdx.x * blockDim.x + tx;
    float sum = 0.0f;

    // Loop over tiles
    for (int t = 0; t < (K + TILE_SIZE - 1) / TILE_SIZE; ++t) {
        int tiled_col = t * TILE_SIZE + tx;
        int tiled_row = t * TILE_SIZE + ty;

        // Load data into shared memory
        if (row < M && tiled_col < K) {
            Us[ty][tx] = U[row * K + tiled_col];
        } else {
            Us[ty][tx] = 0.0f;
        }

        if (ty == 0 && tiled_col < K) {
            Ss[tx] = S[tiled_col];
        }

        if (col < N && tiled_row < K) {
            Vs[ty][tx] = V[tiled_row * N + col];
        } else {
            Vs[ty][tx] = 0.0f;
        }
        __syncthreads();

        // Compute the dot product
        #pragma unroll
        for (int k = 0; k < TILE_SIZE; ++k) {
            sum += Us[ty][k] * Ss[k] * Vs[k][tx];
        }
        __syncthreads();
    }

    // Write the result
    if (row < M && col < N) {
        A[row * N + col] = sum;
    }
}
"""

reconstruct_svd_kernel = cp.RawKernel(kernel_code, "svd_reconstruction_shared")

def reconstruct_svd_batch_gpu(u_batch, s_batch, vt_batch, k, block_size):
    batch_size, rows_u, cols_u = u_batch.shape
    rows_vt, cols_vt = vt_batch.shape[1:]

    # Create CUDA events and stream
    start_event = cuda_runtime.eventCreate()
    stop_event = cuda_runtime.eventCreate()
    copy_to_gpu_start_event = cuda_runtime.eventCreate()
    copy_to_gpu_stop_event = cuda_runtime.eventCreate()
    copy_to_cpu_start_event = cuda_runtime.eventCreate()
    copy_to_cpu_stop_event = cuda_runtime.eventCreate()
    stream = cuda_stream.Stream.null

    # Allocate GPU memory and record time for CPU to GPU communication
    nvtx.RangePush("CPU to GPU Communication")
    cuda_runtime.eventRecord(copy_to_gpu_start_event, stream.ptr)
    u_gpu = cp.asarray(u_batch, dtype=cp.float32)
    s_gpu = cp.asarray(s_batch, dtype=cp.float32)
    vt_gpu = cp.asarray(vt_batch, dtype=cp.float32)
    C_gpu = cp.zeros((batch_size, rows_u, cols_vt), dtype=cp.float32)
    cuda_runtime.eventRecord(copy_to_gpu_stop_event, stream.ptr)
    nvtx.RangePop()

    # Synchronize the events
    cuda_runtime.eventSynchronize(copy_to_gpu_stop_event)

    # Calculate CPU to GPU communication time
    cpu_to_gpu_time = cuda_runtime.eventElapsedTime(copy_to_gpu_start_event, copy_to_gpu_stop_event)
    print(f"CPU to GPU communication time: {cpu_to_gpu_time:.2f} ms")

    # Configure kernel execution parameters
    threads_per_block = (block_size[0], block_size[1])
    blocks_per_grid_x = math.ceil(cols_vt / threads_per_block[0])
    blocks_per_grid_y = math.ceil(rows_u / threads_per_block[1])
    blocks_per_grid_z = batch_size
    blocks_per_grid = (blocks_per_grid_x, blocks_per_grid_y, blocks_per_grid_z)

    # Calculate shared memory size
    shared_mem_size = (block_size[0] * block_size[1] * 2 + block_size[0]) * np.dtype(cp.float32).itemsize

    # Start a new NVTX range for the kernel execution
    nvtx.RangePush("SVD Reconstruction")

    # Record the start event for kernel execution
    cuda_runtime.eventRecord(start_event, stream.ptr)

    # Launch kernel
    with stream:
        reconstruct_svd_kernel(
            blocks_per_grid,
            threads_per_block,
            (u_gpu, s_gpu, vt_gpu, C_gpu, rows_u, cols_vt, k),
            stream=stream,
            shared_mem=shared_mem_size
        )

    # Record the stop event for kernel execution and synchronize
    cuda_runtime.eventRecord(stop_event, stream.ptr)
    stream.synchronize()
    nvtx.RangePop()

    # Synchronize the events
    cuda_runtime.eventSynchronize(stop_event)

    # Calculate kernel execution time
    kernel_time = cuda_runtime.eventElapsedTime(start_event, stop_event)
    print(f"Kernel execution time: {kernel_time:.2f} ms")

    # Record time for GPU to CPU communication
    nvtx.RangePush("GPU to CPU Communication")
    cuda_runtime.eventRecord(copy_to_cpu_start_event, stream.ptr)
    C_result = cp.asnumpy(C_gpu)
    cuda_runtime.eventRecord(copy_to_cpu_stop_event, stream.ptr)
    nvtx.RangePop()

    # Synchronize the events
    cuda_runtime.eventSynchronize(copy_to_cpu_stop_event)

    # Calculate GPU to CPU communication time
    gpu_to_cpu_time = cuda_runtime.eventElapsedTime(copy_to_cpu_start_event, copy_to_cpu_stop_event)
    print(f"GPU to CPU communication time: {gpu_to_cpu_time:.2f} ms")

    return C_result

def load_images_and_compute_svd(folder, pattern="*.png"):
    files = sorted(glob.glob(os.path.join(folder, pattern)))
    images = np.array([imageio.imread(f) for f in tqdm(files, desc="Loading images")])
    svd_results = [cp.linalg.svd(cp.asarray(im), full_matrices=False) for im in images]
    u_batch = cp.array([u[:, :17] for u, s, vt in svd_results])
    s_batch = cp.array([s[:17] for u, s, vt in svd_results])
    vt_batch = cp.array([vt[:17, :] for u, s, vt in svd_results])
    return images, u_batch, s_batch, vt_batch

# Load images and compute SVD
subfolder = "001"
images, u_batch, s_batch, vt_batch = load_images_and_compute_svd(
    os.path.join("adni_png", subfolder)
)

# Perform batch SVD reconstruction on GPU
block_size = (32, 32)
start_time = timeit.default_timer()
reconstructed_images = reconstruct_svd_batch_gpu(
    u_batch, s_batch, vt_batch, 17, block_size
)
end_time = timeit.default_timer()

# Display all original and reconstructed images
num_images = len(images)
#fig, axes = plt.subplots(num_images, 2, figsize=(10, 5 * num_images))

#for i in range(num_images):
#    axes[i, 0].imshow(images[i], cmap='gray')
#    axes[i, 0].set_title(f"Original Image {i + 1}")
#    axes[i, 1].imshow(reconstructed_images[i], cmap='gray')
#    axes[i, 1].set_title(f"Reconstructed Image {i + 1}")
#
#plt.tight_layout()
#plt.show()

# Print benchmarking results
print(f"Reconstruction time: {end_time - start_time:.2f} seconds")
