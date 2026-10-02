# Windows CUDA binary redistribution audit

Audited 2026-10-02 against the **rebuilt, not yet published** `dist/v0.4.1/LocalCaption`
from PyTorch **2.10.0+cu128** (CUDA 12.8; cuDNN 9.10.2). The existing v0.4.1
GitHub CUDA download is a **different, older bundle** and does not pass this audit.
This is a technical inventory against the published terms, **not legal advice or a
blanket authorization to redistribute future builds**.

## Primary sources and conditions

- [NVIDIA CUDA 12.8 SDK agreement](https://docs.nvidia.com/cuda/archive/12.8.0/eula/index.html):
  section 1.1.1 (limited distribution grant), 1.1.2 (application must add
  material functionality; distributables accessed by the app; not a standalone
  SDK or unlisted developer tool), section 2.2 and [Attachment A](https://docs.nvidia.com/cuda/archive/12.8.0/eula/index.html#attachment-a)
  (the specific Windows redistributable components, including version/architecture
  filename variants). MIT applies only to Local Caption, **not** NVIDIA code.
  Respect the agreement's no-endorsement, no-removal-of-notices and export terms.
- [NVIDIA cuDNN 9.10.2 agreement and supplement](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html):
  distribution grant for cuDNN runtime `.dll` files, for applications used on
  systems with NVIDIA GPUs, subject to its additional application-distribution
  conditions.
- [NVIDIA CUDA 12.8 Windows component manifest](https://developer.download.nvidia.com/compute/cuda/redist/redistrib_12.8.0.json):
  package inventories corroborate the named components. A file's presence in
  an SDK or wheel is **not**, by itself, a distribution license.

## DLLs in the revised CUDA build

All paths below are relative to `_internal/torch/lib/` in the **new** CUDA build.
These are the **21 NVIDIA DLLs that remain**, grouped by the published grant:

| Grant / component | Files |
|---|---|
| CUDA 12.8 Attachment A, runtime and math | `cudart64_12.dll`, `cublas64_12.dll`, `cublasLt64_12.dll`, `cufft64_11.dll`, `cufftw64_11.dll`, `curand64_10.dll`, `cusolver64_11.dll`, `cusparse64_12.dll` |
| CUDA 12.8 Attachment A, compiler and profiling libraries | `nvrtc64_120_0.dll`, `nvrtc-builtins64_128.dll`, `cupti64_2025.1.1.dll`, `nvToolsExt64_1.dll` |
| CUDA 12.8 Attachment A, JIT linking component | `nvJitLink_120_0.dll` — required by this PyTorch CUDA build. Attachment A calls the component `libnvJitLink.dll`; [NVIDIA's own 12.8 Windows libnvjitlink redist archive](https://developer.download.nvidia.com/compute/cuda/redist/libnvjitlink/windows-x86_64/libnvjitlink-windows-x86_64-12.8.61-archive.zip) contains **the exact `nvJitLink_120_0.dll` filename**. This strongly indicates the file belongs to the named redistributable component, but the prefix differs; seek NVIDIA clarification if an unambiguous filename-level grant is required. This link corroborates the filename, **not** a byte-for-byte match to the PyTorch wheel. |
| cuDNN 9.10.2 runtime `.dll` grant | `cudnn64_9.dll`, `cudnn_adv64_9.dll`, `cudnn_cnn64_9.dll`, `cudnn_engines_precompiled64_9.dll`, `cudnn_engines_runtime_compiled64_9.dll`, `cudnn_graph64_9.dll`, `cudnn_heuristic64_9.dll`, `cudnn_ops64_9.dll` |

PyTorch's `c10_cuda.dll`, `torch_cuda.dll`, `caffe2_nvrtc.dll` etc. are PyTorch
binaries, **not** individual CUDA Toolkit libraries. Intel OpenMP and zlib DLLs
have separate terms; their wheel notices are bundled by the build script.

Three **unneeded** DLLs in the original wheel are intentionally excluded from
new app bundles, rather than assuming every SDK file is redistributable:

- `nvperf_host.dll`: performance/profiling helper; **not named** in CUDA 12.8
  Attachment A (even though included in NVIDIA's CUPTI package).
- `cusolverMg64_11.dll`: auxiliary multi-GPU solver; Attachment A names
  `cusolver.dll`, but not this separate `Mg` DLL. Not needed by this app.
- `nvrtc64_120_0.alt.dll`: alternate compiler DLL; not named explicitly as a
  version/architecture variant in Attachment A. Not needed by this app.

The build script also rejects any changed NVIDIA DLL list or CUDA PyTorch wheel
version until this audit is revisited. The packaged CUDA worker passed a real
RTX 4070 Laptop GPU probe (matrix multiplication and FFT), plus an end-to-end
`medium.pt` speech transcription/burn test using `cuda:0` **without** those three
DLLs. This proves the tested workflow works; it cannot prove every possible
CUDA workload or driver configuration works.

**Release action:** merge the licensing PR, rebuild both editions from a *new*
tag, include `THIRD_PARTY_NOTICES.md` and `licenses/`, and replace/retire the
old CUDA asset. Do not treat the old v0.4.1 CUDA archive as covered by this
inventory. If keeping the `nvJitLink` naming ambiguity is unacceptable, seek
written clarification from NVIDIA at the contact in its cuDNN agreement before
publishing a new CUDA edition. Re-check the exact binary inventory and current
agreements for every subsequent dependency update.
