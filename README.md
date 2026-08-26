# onnxruntime-gpu-extended-auto

```
pip install onnxruntime-gpu-extended-auto
```

That is the whole thing. It looks at which CUDA and cuDNN are installed on the
machine you are running `pip` on, then pulls the matching
[onnxruntime-gpu-extended](https://pypi.org/project/onnxruntime-gpu-extended/)
build.

## Why this exists

A wheel filename can say "Python 3.12, aarch64, glibc 2.34". It cannot say
"cuDNN 8" or "cuDNN 9". Both JetPack 6.0 and JetPack 6.2 produce the exact same
tag, `cp312-cp312-manylinux_2_34_aarch64`, so PyPI has no way to hand each one a
different file. An onnxruntime built against cuDNN 8 will not load on cuDNN 9,
and vice versa.

This package resolves that at install time instead.

Published versions are `<onnxruntime version>.<cuda major>.<cudnn major>`, so the
ABI that the filename cannot express lives in the version number instead.

| Detected | Installs |
|---|---|
| CUDA 12 / cuDNN 8 (JetPack 6.0, L4T r36.3) | `onnxruntime-gpu-extended==1.22.2.12.8` |
| CUDA 12 / cuDNN 9 (JetPack 6.1 / 6.2, L4T r36.4) | `onnxruntime-gpu-extended==1.23.2.12.9` |

Check what you have with `head -1 /etc/nv_tegra_release`.

## Install it on the device

Detection reads the machine running `pip`. Building a lockfile or a container
image on one JetPack and deploying to another will bake in the wrong choice.

pip caches the wheel it builds from this package, keyed on the source archive
rather than on the machine. After upgrading JetPack on a box, reinstall with
`--no-cache-dir` so detection runs again.

To pick explicitly instead of detecting:

```
ORT_GPU_EXTENDED_VARIANT='onnxruntime-gpu-extended==1.23.2.12.9' pip install onnxruntime-gpu-extended-auto
```

The same variable is how this package's own source archive gets built off-device,
since detection otherwise refuses to run on a non-Jetson machine.

## Verify

```python
import onnxruntime
print(onnxruntime.get_available_providers())
```

`get_available_providers()` lists what was compiled in, not what loads. To prove
CUDA actually works, build a session and ask it:

```python
session = onnxruntime.InferenceSession("model.onnx", providers=["CUDAExecutionProvider"])
print(session.get_providers())
```
