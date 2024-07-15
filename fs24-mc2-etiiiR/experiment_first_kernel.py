
import cupy as cp
import numpy as np
import math
import matplotlib.pyplot as plt
import timeit
import cupy.cuda.runtime as cuda_runtime
import cupy.cuda.stream as cuda_stream
import cupy.cuda.nvtx as nvtx
import os
import imageio.v2 as imageio
import glob


subfolder = "001"
folders = os.path.join("adni_png", subfolder)

# Get all PNGs from 001 with 145 in the name
files = sorted(glob.glob(f"{folders}/*145.png"))

# Load all images using ImageIO and create a numpy array from them
images = np.array([imageio.imread(f) for f in files])

# Get all the names of the files
names = [f[-17:-4] for f in files]

im = images[0]

# Kernel implementiert in CUDA C
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

# Beispielbild, ersetzt durch tatsächliches Bild
im_cpu = images[0]
im_gpu = cp.asarray(im_cpu, dtype=cp.float32)

# CUDA Events und NVTX Bereiche hinzufügen
start_event = cuda_runtime.eventCreate()
stop_event = cuda_runtime.eventCreate()
copy_to_gpu_start_event = cuda_runtime.eventCreate()
copy_to_gpu_stop_event = cuda_runtime.eventCreate()
copy_to_cpu_start_event = cuda_runtime.eventCreate()
copy_to_cpu_stop_event = cuda_runtime.eventCreate()
stream = cuda_stream.Stream.null

# GPU SVD durchführen
nvtx.RangePush("GPU SVD")
cuda_runtime.eventRecord(start_event, stream.ptr)
begin_gpu_svd = timeit.default_timer()
u_gpu, s_gpu, vt_gpu = cp.linalg.svd(im_gpu, full_matrices=False)
end_gpu_svd = timeit.default_timer()
cuda_runtime.eventRecord(stop_event, stream.ptr)
nvtx.RangePop()

# Synchronisiere und berechne die GPU SVD-Zeit
cuda_runtime.eventSynchronize(stop_event)
gpu_svd_time = cuda_runtime.eventElapsedTime(start_event, stop_event)
print(f"GPU SVD: {gpu_svd_time:.2f} ms")

# CPU SVD zum Vergleich durchführen
begin_cpu_svd = timeit.default_timer()
u_cpu, s_cpu, vt_cpu = np.linalg.svd(im_cpu, full_matrices=False)
end_cpu_svd = timeit.default_timer()
print("CPU SVD: ", end_cpu_svd - begin_cpu_svd)

k = 50
u = u_cpu[:, :k]
s = s_cpu[:k]
vt = vt_cpu[:k, :]

C = np.zeros((u.shape[0], vt.shape[1]), dtype=np.float32)

u_gpu = cp.asarray(u, dtype=cp.float32)
s_gpu = cp.asarray(s, dtype=cp.float32)
vt_gpu = cp.asarray(vt, dtype=cp.float32)
C_gpu = cp.asarray(C, dtype=cp.float32)

threads_per_block = (16, 16)
blocks_per_grid_x = math.ceil(u.shape[0] / threads_per_block[0])
blocks_per_grid_y = math.ceil(vt.shape[1] / threads_per_block[1])
blocks_per_grid = (blocks_per_grid_x, blocks_per_grid_y)

# Rekonstruktion mit verschiedenen Methoden auf der GPU
def reconstruct_svd_gpu(u, s, vt, k):
    s_gpu = cp.diag(cp.asarray(s[:k]))
    us_gpu = cp.dot(u[:, :k], s_gpu)
    reco_gpu = cp.dot(us_gpu, vt[:k, :])
    return reco_gpu

def reconstruct_svd_cp_einsum(u, s, vt, k):
    return cp.einsum("ij,j,jk", u[:, :k], s[:k], vt[:k, :])

def reconstruct_svd_cp_broadcast(u, s, vt, k):
    return cp.dot(u[:, :k], cp.multiply(s[:k].reshape(-1, 1), vt[:k, :]))

def reconstruct_svd_cp_broadcast_cpu(u, s, vt, k):
    return np.dot(u[:, :k], np.multiply(s[:k].reshape(-1, 1), vt[:k, :]))

print("\nReconstruction:")

# Validierung der Ergebnisse durch Plotting
nvtx.RangePush("Reconstruction Methods")

# CUDA Events für Rekonstruktion
recon_start_event = cuda_runtime.eventCreate()
recon_stop_event = cuda_runtime.eventCreate()

# CP GPU Rekonstruktion
nvtx.RangePush("CP GPU")
cuda_runtime.eventRecord(recon_start_event, stream.ptr)
start_gpu = timeit.default_timer()
reconstruct_svd_gpu_output = reconstruct_svd_gpu(u_gpu, s_gpu, vt_gpu, k)
end_gpu = timeit.default_timer()
cuda_runtime.eventRecord(recon_stop_event, stream.ptr)
nvtx.RangePop()
cuda_runtime.eventSynchronize(recon_stop_event)
cp_gpu_time = cuda_runtime.eventElapsedTime(recon_start_event, recon_stop_event)
print(f"CP GPU: {cp_gpu_time:.2f} ms")

# CP Einsum Rekonstruktion
nvtx.RangePush("CP Einsum")
start_einsum = timeit.default_timer()
reconstruct_svd_cp_einsum_output = reconstruct_svd_cp_einsum(u_gpu, s_gpu, vt_gpu, k)
end_einsum = timeit.default_timer()
nvtx.RangePop()
print("CP Einsum: ", end_einsum - start_einsum)

# CP Broadcast Rekonstruktion
nvtx.RangePush("CP Broadcast")
start_broadcast = timeit.default_timer()
reconstruct_svd_cp_broadcast_output = reconstruct_svd_cp_broadcast(u_gpu, s_gpu, vt_gpu, k)
end_broadcast = timeit.default_timer()
nvtx.RangePop()
print("CP Broadcast: ", end_broadcast - start_broadcast)

# CP Broadcast CPU Rekonstruktion
nvtx.RangePush("CP Broadcast CPU")
start_broadcast_cpu = timeit.default_timer()
reconstruct_svd_cp_broadcast_output_cpu = reconstruct_svd_cp_broadcast_cpu(u_cpu, s_cpu, vt_cpu, k)
end_broadcast_cpu = timeit.default_timer()
nvtx.RangePop()
print("CP Broadcast CPU: ", end_broadcast_cpu - start_broadcast_cpu)

# CP Kernel Rekonstruktion
nvtx.RangePush("CP Kernel")
cuda_runtime.eventRecord(recon_start_event, stream.ptr)
start_reconstruct_svd_kernel = timeit.default_timer()
# Launch the custom kernel
reconstruct_svd_kernel(
    blocks_per_grid,
    threads_per_block,
    (u_gpu, s_gpu, vt_gpu, C_gpu, u.shape[0], u.shape[1], vt.shape[0], vt.shape[1], k),
)
end_reconstruct_svd_kernel = timeit.default_timer()
cuda_runtime.eventRecord(recon_stop_event, stream.ptr)
nvtx.RangePop()
cuda_runtime.eventSynchronize(recon_stop_event)
cp_kernel_time = cuda_runtime.eventElapsedTime(recon_start_event, recon_stop_event)
print(f"CP Kernel: {cp_kernel_time:.2f} ms")

# Plotting der Ergebnisse
#fig, axes = plt.subplots(2, 3, figsize=(15, 10))
#axes = axes.ravel()

#axes[0].imshow(cp.asnumpy(reconstruct_svd_gpu_output), cmap="gray")
#axes[0].set_title(f"GPU Kernel: {k} components")

#axes[1].imshow(cp.asnumpy(reconstruct_svd_cp_einsum_output), cmap="gray")
#axes[1].set_title(f"Einsum: {k} components")
#
#axes[2].imshow(cp.asnumpy(reconstruct_svd_cp_broadcast_output), cmap="gray")
#axes[2].set_title(f"Broadcast: {k} components")
#
#axes[3].imshow(cp.asnumpy(reconstruct_svd_cp_broadcast_output_cpu), cmap="gray")
#axes[3].set_title(f"Broadcast CPU: {k} components")

#axes[4].imshow(cp.asnumpy(C_gpu), cmap="gray")
#axes[4].set_title(f"GPU Kernel: {k} components")

#axes[5].axis("off")

#plt.tight_layout()
#plt.show()
