
import numpy as np
import cupy as cp
import os
import glob
import imageio.v3 as imageio
import time
import math
from tqdm import tqdm
import matplotlib.pyplot as plt
import subprocess
import cupy.cuda.nvtx as nvtx

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

def load_images_and_compute_svd(folder, pattern="*.png"):
    files = sorted(glob.glob(os.path.join(folder, pattern)))
    images = np.array([imageio.imread(f) for f in tqdm(files, desc="Loading images")])
    svd_results = [np.linalg.svd(im, full_matrices=False) for im in images]
    u_batch = np.array([u[:, :17] for u, s, vt in svd_results])
    s_batch = np.array([s[:17] for u, s, vt in svd_results])
    vt_batch = np.array([vt[:17, :] for u, s, vt in svd_results])
    return images, u_batch, s_batch, vt_batch

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

def reconstruct_multiple_images(images, u_batch, s_batch, vt_batch):
    streams = [cp.cuda.Stream() for _ in range(len(images))]
    C_gpu_results = []

    nvtx.RangePush("Reconstruction")
    start_event = cp.cuda.Event()
    end_event = cp.cuda.Event()
    start_event.record()

    # Launch kernels in parallel using multiple streams
    for i in range(len(images)):
        stream = streams[i]
        with stream.use():
            nvtx.RangePush(f"Image_{i}_Reconstruction")
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

def main(num_extensions=2):
    nvtx.RangePush("Main")
    # Load images and compute SVD
    subfolder = "001"
    nvtx.RangePush("Load_Images_And_Compute_SVD")
    images, u_batch, s_batch, vt_batch = load_images_and_compute_svd(
        os.path.join("adni_png", subfolder)
    )
    nvtx.RangePop()

    # Reconstruct the original set of images
    gpu_usages = []
    for _ in range(5):  # Run the reconstruction 5 times for averaging
        nvtx.RangePush("Reconstruct_Original_Images")
        reconstructed_images = reconstruct_multiple_images(images, u_batch, s_batch, vt_batch)
        nvtx.RangePop()

        nvtx.RangePush("Monitor_GPU_Usage")
        gpu_usage = monitor_gpu_usage(duration=5, interval=1)
        nvtx.RangePop()
        gpu_usages.append(gpu_usage)

    avg_gpu_usage = np.mean(gpu_usages, axis=0)
    print(f"Average GPU usage: {avg_gpu_usage}%")

    # Display all original and reconstructed images
    num_images = len(images)

    # Reconstruct with more images by reusing the same images
    extended_images = np.tile(images, (num_extensions, 1, 1))
    extended_u_batch = np.tile(u_batch, (num_extensions, 1, 1))
    extended_s_batch = np.tile(s_batch, (num_extensions, 1))
    extended_vt_batch = np.tile(vt_batch, (num_extensions, 1, 1))

    nvtx.RangePush("Reconstruct_Extended_Images")
    
    gpu_usages = []
    for _ in range(5):  # Run the reconstruction 5 times for averaging
        nvtx.RangePush("Reconstruct_Extended_Images")
        extended_reconstructed_images = reconstruct_multiple_images(
        extended_images, extended_u_batch, extended_s_batch, extended_vt_batch
        )
        nvtx.RangePop()

        nvtx.RangePush("Monitor_GPU_Usage")
        gpu_usage = monitor_gpu_usage(duration=5, interval=1)
        nvtx.RangePop()
        gpu_usages.append(gpu_usage)

    avg_gpu_usage = np.mean(gpu_usages, axis=0)
    print(f"Average GPU usage more images: {avg_gpu_usage}%")

    nvtx.RangePop()

    # Display all extended and reconstructed images
    num_extended_images = len(extended_images)

    
    nvtx.RangePop()

if __name__ == "__main__":
    num_extensions = 5  # Set this to the number of times you want to reuse the images
    main(num_extensions)
