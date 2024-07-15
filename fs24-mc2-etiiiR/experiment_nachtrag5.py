
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
from skimage.transform import resize

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

scale_factor = 5
def scale_image(image, scale_factor):
    new_shape = tuple(int(dim * scale_factor) for dim in image.shape)
    return resize(image, new_shape, mode="reflect", anti_aliasing=True)

def reconstruct_svd_batch_gpu(u_batch, s_batch, vt_batch, k, block_size):
    batch_size, rows_u, cols_u = u_batch.shape
    rows_vt, cols_vt = vt_batch.shape[1:]

    # Allocate GPU memory for the result
    C_gpu = cp.zeros((batch_size, rows_u, cols_vt), dtype=cp.float32)

    # Configure kernel execution parameters
    threads_per_block = (block_size[0], block_size[1])
    blocks_per_grid_x = math.ceil(rows_u / threads_per_block[0])
    blocks_per_grid_y = math.ceil(cols_vt / threads_per_block[1])
    blocks_per_grid_z = batch_size
    blocks_per_grid = (blocks_per_grid_x, blocks_per_grid_y, blocks_per_grid_z)

    # Create streams
    streams = [cp.cuda.Stream() for _ in range(batch_size)]

    # Launch kernel in each stream with async H2D memory transfers
    for i in range(batch_size):
        with streams[i]:
            # Start NVTX range for the H2D transfer
            nvtx.RangePush(f"H2D transfer batch {i}")

            # Asynchronous H2D transfer
            u_gpu = cp.asarray(u_batch[i], dtype=cp.float32)
            s_gpu = cp.asarray(s_batch[i], dtype=cp.float32)
            vt_gpu = cp.asarray(vt_batch[i], dtype=cp.float32)

            # End NVTX range for the H2D transfer
            nvtx.RangePop()

            # Start NVTX range for the kernel execution
            nvtx.RangePush(f"Kernel execution batch {i}")

            # Launch the kernel
            reconstruct_svd_kernel(
                blocks_per_grid,
                threads_per_block,
                (u_gpu.data.ptr, s_gpu.data.ptr, vt_gpu.data.ptr, C_gpu[i].data.ptr, rows_u, cols_u, rows_vt, cols_vt, k),
                stream=streams[i]
            )

            # End NVTX range for the kernel execution
            nvtx.RangePop()

            # Start NVTX range for the D2H transfer
            nvtx.RangePush(f"D2H transfer batch {i}")

            # Asynchronous D2H transfer
            cp.asnumpy(C_gpu[i], stream=streams[i])

            # End NVTX range for the D2H transfer
            nvtx.RangePop()

    # Wait for all streams to finish
    for stream in streams:
        stream.synchronize()

    # Copy result back to CPU
    return cp.asnumpy(C_gpu)

def load_images_and_compute_svd(folder, pattern="*.png"):
    files = sorted(glob.glob(os.path.join(folder, pattern)))
    images = np.array([scale_image(imageio.imread(f), scale_factor) for f in tqdm(files, desc="Loading images")])
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
block_size = (16, 16)
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

#plt.tight_layout()
#plt.show()

# Print benchmarking results
print(f"Reconstruction time: {end_time - start_time:.2f} seconds")
