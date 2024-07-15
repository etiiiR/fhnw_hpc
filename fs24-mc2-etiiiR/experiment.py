

import numpy as np
import cupy as cp
import time
import matplotlib.pyplot as plt
import math
import cupy.cuda.nvtx as nvtx

print('start')
# clean gpu memory
cp.get_default_memory_pool().free_all_blocks()

kernel_code = """
extern "C" __global__
void reconstruct_svd(const float* u, const float* s, const float* vt, float* C,
            int rows_u, int cols_u, int rows_vt, int cols_vt, int k)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int j = blockIdx.y * blockDim.y + threadIdx.y;

    // check if k is in range
    if (k > rows_u || k > cols_vt || k > rows_vt || k > cols_u) {
        return;
    }
    if (k < 0) {
        return;
    }
    // check if i and j are in bounds
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

def reconstruct_svd_cp_einsum(u, s, vt, k):
    return cp.einsum("ij,j,jk", u[:, :k], s[:k], vt[:k, :])

def reconstruct_svd_cp_broadcast(u, s, vt, k):
    return cp.dot(u[:, :k], cp.multiply(s[:k].reshape(-1, 1), vt[:k, :]))

def reconstruct_svd_numpy(u, s, vt, k):
    u_k = u[:, :k]
    s_k = np.diag(s[:k])
    vt_k = vt[:k, :]
    return u_k @ s_k @ vt_k

def cpu_matmul(A, B):
    start = time.time()
    C = np.dot(A, B)
    end = time.time()
    return C, end - start

def reconstruct_svd_gpu(u, s, vt, k, block_size):
    rows_u, cols_u = u.shape
    rows_vt, cols_vt = vt.shape

    u_gpu = cp.asarray(u[:, :k], dtype=cp.float32)
    s_gpu = cp.asarray(s[:k], dtype=cp.float32)
    vt_gpu = cp.asarray(vt[:k, :], dtype=cp.float32)
    C_gpu = cp.zeros((rows_u, cols_vt), dtype=cp.float32)

    threads_per_block = (block_size[0], block_size[1])
    blocks_per_grid_x = math.ceil(rows_u / threads_per_block[0])
    blocks_per_grid_y = math.ceil(cols_vt / threads_per_block[1])
    blocks_per_grid = (blocks_per_grid_x, blocks_per_grid_y)

    nvtx.RangePush("Kernel Launch")
    reconstruct_svd_kernel(
        blocks_per_grid,
        threads_per_block,
        (u_gpu, s_gpu, vt_gpu, C_gpu, rows_u, cols_u, rows_vt, cols_vt, k),
    )
    cp.cuda.Stream.null.synchronize()
    nvtx.RangePop()

    reco_cpu = cp.asnumpy(C_gpu)
    return reco_cpu

# Function to perform experiments with different sizes
def experiment(input_sizes, block_sizes):
    results = {"cpu": [], "gpu": []}
    for size in input_sizes:
        m, n, k = size, size, 50
        A = np.random.rand(m, k).astype(np.float32)
        B = np.random.rand(k, n).astype(np.float32)

        # Perform SVD on the matrix A
        u, s, vt = np.linalg.svd(A, full_matrices=False)

        for block_size in block_sizes:
            # Timing the GPU implementation
            nvtx.RangePush(f"Size {size}, Block Size {block_size}")
            start_gpu = time.time()
            _ = reconstruct_svd_gpu(u, s, vt, k, block_size)
            end_gpu = time.time()
            nvtx.RangePop()
            results["gpu"].append(end_gpu - start_gpu)

    return results

# Define different input sizes
input_sizes = [1, 64, 128, 256, 512, 1024, 2048, 4096, 8192]
# my gpu rtx 3080 only supports block sizes up to 32
block_configurations = []
for i in range(2, 6):
    block_configurations.append((2**i, 2**i))
    block_configurations.append((2**i, 2 ** (i - 1)))
    block_configurations.append((2 ** (i - 1), 2**i))
    block_configurations.append((2 ** (i - 1), 2 ** (i + 1)))
    block_configurations.append((2 ** (i - 2), 2 ** (i + 1)))
    block_configurations.append((2 ** (i - 2), 2 ** (i + 2)))

# Run the experiments
results = experiment(input_sizes, block_sizes=block_configurations)
print('stop')
