
import numpy as np
import cupy as cp
import time

print('start')

matmul_kernel_shared = cp.RawKernel(
    r"""
extern "C" __global__
void matmul_shared(const float* A, const float* B, float* C, int M, int N, int K) {
    __shared__ float As[32][32];
    __shared__ float Bs[32][32];

    int tx = threadIdx.x, ty = threadIdx.y;
    int row = blockIdx.y * blockDim.y + ty;
    int col = blockIdx.x * blockDim.x + tx;
    float sum = 0.0f;

    for (int t = 0; t < (K + 32 - 1) / 32; ++t) {
        if (row < M && t * 32 + tx < K) {
            As[ty][tx] = A[row * K + t * 32 + tx];
        } else {
            As[ty][tx] = 0.0;
        }
        if (col < N && t * 32 + ty < K) {
            Bs[ty][tx] = B[(t * 32 + ty) * N + col];
        } else {
            Bs[ty][tx] = 0.0;
        }
        __syncthreads();

        #pragma unroll
        for (int k = 0; k < 32; ++k) {
            sum += As[ty][k] * Bs[k][tx];
        }
        __syncthreads();
    }

    if (row < M && col < N) {
        C[row * N + col] = sum;
    }
}
""",
    "matmul_shared",
)


def gpu_matmul_shared(A, B):
    A_gpu = cp.asarray(A)
    B_gpu = cp.asarray(B)
    C_gpu = cp.zeros((A.shape[0], B.shape[1]), dtype=cp.float32)

    threadsperblock = (32, 32)
    blockspergrid_x = int(np.ceil(A.shape[1] / threadsperblock[0]))
    blockspergrid_y = int(np.ceil(A.shape[0] / threadsperblock[1]))
    blockspergrid = (blockspergrid_x, blockspergrid_y)

    start_event = cp.cuda.Event()
    end_event = cp.cuda.Event()

    start_event.record()
    nvtx.RangePush("Matrix Multiplication Shared")
    matmul_kernel_shared(
        (blockspergrid_x, blockspergrid_y),
        threadsperblock,
        (A_gpu, B_gpu, C_gpu, A.shape[0], B.shape[1], A.shape[1]),
    )
    nvtx.RangePop()
    end_event.record()
    cp.cuda.Device().synchronize()

    elapsed_time = cp.cuda.get_elapsed_time(start_event, end_event)  # in milliseconds

    return C_gpu, elapsed_time


import cupy.cuda.nvtx as nvtx

def experiment_shared(input_sizes):
    results = {"cpu": [], "gpu_shared": []}
    for size in input_sizes:
        m, n, k = size, size, size
        A = np.random.rand(m, k).astype(np.float32)
        B = np.random.rand(k, n).astype(np.float32)

        # Timing the shared memory GPU implementation
        nvtx.RangePush(f"Size {size}")
        C_gpu, gpu_time_shared = gpu_matmul_shared(A, B)
        nvtx.RangePop()
        results["gpu_shared"].append(gpu_time_shared)

    return results

# Define different input sizes
input_sizes = [256, 512, 1024, 2048, 4096, 8192]

# Run the experiments
results_shared = experiment_shared(input_sizes)
print('stop')
