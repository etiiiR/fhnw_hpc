
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

# Define the kernel for batch SVD reconstruction
kernel_code = """
extern "C" __global__
void reconstruct_svd(const float* u, const float* s, const float* vt, float* C,
            int rows_u, int cols_u, int rows_vt, int cols_vt, int k)
{
    extern __shared__ float shared_data[];

    float* shared_u = shared_data;
    float* shared_vt = shared_data + rows_u * k;
    float* shared_s = shared_data + rows_u * k + k * cols_vt;

    int img_id = blockIdx.z;
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int j = blockIdx.y * blockDim.y + threadIdx.y;

    const float* u_img = u + img_id * rows_u * cols_u;
    const float* s_img = s + img_id * k;
    const float* vt_img = vt + img_id * rows_vt * cols_vt;
    float* C_img = C + img_id * rows_u * cols_vt;

    // Load u, s, and vt into shared memory
    if (threadIdx.x < rows_u && threadIdx.y < k) {
        shared_u[threadIdx.x * k + threadIdx.y] = u_img[threadIdx.x * cols_u + threadIdx.y];
    }
    if (threadIdx.x < k && threadIdx.y < cols_vt) {
        shared_vt[threadIdx.x * cols_vt + threadIdx.y] = vt_img[threadIdx.x * cols_vt + threadIdx.y];
    }
    if (threadIdx.x == 0 && threadIdx.y < k) {
        shared_s[threadIdx.y] = s_img[threadIdx.y];
    }

    __syncthreads();

    if (i >= rows_u || j >= cols_vt) {
        return;
    }

    float sum = 0;
    for (int l = 0; l < k; ++l) {
        sum += shared_u[i * k + l] * shared_s[l] * shared_vt[l * cols_vt + j];
    }
    C_img[i * cols_vt + j] = sum;
}
"""

reconstruct_svd_kernel = cp.RawKernel(kernel_code, "reconstruct_svd")


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
    blocks_per_grid_x = math.ceil(rows_u / threads_per_block[0])
    blocks_per_grid_y = math.ceil(cols_vt / threads_per_block[1])
    blocks_per_grid_z = batch_size
    blocks_per_grid = (blocks_per_grid_x, blocks_per_grid_y, blocks_per_grid_z)

    # Calculate shared memory size
    shared_mem_size = (rows_u * k + k * cols_vt + k) * np.dtype(cp.float32).itemsize

    # Start a new NVTX range for the kernel execution
    nvtx.RangePush("SVD Reconstruction")

    # Record the start event for kernel execution
    cuda_runtime.eventRecord(start_event, stream.ptr)

    # Launch kernel
    with stream:
        reconstruct_svd_kernel(
            blocks_per_grid,
            threads_per_block,
            (u_gpu, s_gpu, vt_gpu, C_gpu, rows_u, cols_u, rows_vt, cols_vt, k),
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
