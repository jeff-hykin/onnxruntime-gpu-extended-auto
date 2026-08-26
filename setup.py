"""Metadata-only package that resolves to the onnxruntime-gpu-extended build
matching the CUDA/cuDNN majors present on the machine running pip."""

import glob
import os
import re
import subprocess
import sys

from setuptools import setup

DISPATCHER_VERSION = "1.23.2"
DISTRIBUTION = "onnxruntime-gpu-extended"

# Published wheel versions are <ort_version>.<cuda_major>.<cudnn_major>, so the
# ABI lives in the version rather than in the project name.
# (cuda_major, cudnn_major) -> version
VARIANTS = {
    (12, 8): "1.22.2.12.8",
    (12, 9): "1.23.2.12.9",
}

LIBRARY_DIRECTORIES = [
    "/usr/lib/aarch64-linux-gnu",
    "/usr/lib/x86_64-linux-gnu",
    "/usr/local/cuda/lib64",
    "/usr/local/cuda/targets/aarch64-linux/lib",
    "/usr/local/cuda/targets/x86_64-linux/lib",
    "/usr/lib64",
    "/usr/lib",
]


def soname_majors(library_stem):
    """Every N for which libFOO.so.N is visible to the dynamic linker."""
    pattern = re.compile(re.escape(library_stem) + r"\.so\.(\d+)")
    majors = set()

    try:
        ldconfig_output = subprocess.run(
            ["/sbin/ldconfig", "-p"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        majors.update(int(match) for match in pattern.findall(ldconfig_output))
    except (OSError, subprocess.SubprocessError):
        pass

    search_directories = list(LIBRARY_DIRECTORIES)
    search_directories += [
        directory
        for directory in os.environ.get("LD_LIBRARY_PATH", "").split(":")
        if directory
    ]
    for directory in search_directories:
        for path in glob.glob(os.path.join(directory, library_stem + ".so.*")):
            match = pattern.search(os.path.basename(path))
            if match:
                majors.add(int(match.group(1)))

    return majors


def detect_requirement():
    override = os.environ.get("ORT_GPU_EXTENDED_VARIANT")
    if override:
        return override, "ORT_GPU_EXTENDED_VARIANT"

    cuda_majors = soname_majors("libcudart")
    cudnn_majors = soname_majors("libcudnn")
    if not cuda_majors or not cudnn_majors:
        raise SystemExit(
            "onnxruntime-gpu-extended-auto: could not find CUDA and cuDNN on this "
            "machine.\n"
            "  libcudart.so.N found: %s\n"
            "  libcudnn.so.N found:  %s\n"
            "This package must be installed on the target device (a Jetson with "
            "JetPack installed), not cross-built.\n"
            "To bypass detection, set ORT_GPU_EXTENDED_VARIANT to a pip "
            "requirement, e.g.\n"
            "  ORT_GPU_EXTENDED_VARIANT='onnxruntime-gpu-extended==1.23.2'"
            % (sorted(cuda_majors) or "none", sorted(cudnn_majors) or "none")
        )

    # A box carrying several cuDNN majors can run the build for the newest one.
    key = (max(cuda_majors), max(cudnn_majors))
    if key not in VARIANTS:
        raise SystemExit(
            "onnxruntime-gpu-extended-auto: no build published for CUDA %d / "
            "cuDNN %d.\nPublished combinations: %s\n"
            "Please open an issue at "
            "https://github.com/jeff-hykin/onnxruntime-gpu-extended-auto/issues"
            % (key[0], key[1], ", ".join("CUDA %d / cuDNN %d" % k for k in sorted(VARIANTS)))
        )

    return "%s==%s" % (DISTRIBUTION, VARIANTS[key]), "CUDA %d / cuDNN %d" % key


requirement, detection_source = detect_requirement()
sys.stderr.write(
    "onnxruntime-gpu-extended-auto: detected %s -> installing %s\n"
    % (detection_source, requirement)
)

setup(
    name="onnxruntime-gpu-extended-auto",
    version=DISPATCHER_VERSION,
    description=(
        "Installs the onnxruntime-gpu-extended build matching this machine's "
        "CUDA and cuDNN versions"
    ),
    long_description=open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
    ).read(),
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/jeff-hykin/onnxruntime-gpu-extended-auto",
    python_requires=">=3.10",
    install_requires=[requirement],
    py_modules=[],
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "Environment :: GPU :: NVIDIA CUDA",
        "Topic :: Scientific/Engineering",
    ],
)
