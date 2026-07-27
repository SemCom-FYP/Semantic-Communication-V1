# SwinJSCC Semantic Communication

End-to-end image transmission system over wireless channels using a Swin Transformer-based Joint Source-Channel Coding (JSCC) model. Images are encoded directly into channel symbols, transmitted as a compact binary file, and reconstructed at the receiver — no separate source and channel coding steps.

Key features:
- **Adaptive patching** — quadtree edge-detection selects informative patches, reducing transmitted data for smooth/uniform images
- **Codebook quantization** — vector quantization maps encoded features to discrete codewords (2d/4d/8d, 256–1024 clusters)
- **Hamming error correction** — redundant bit encoding on the 5-byte control header; Hamming codeword mapping on k=512 indices
- **Channel support** — Rayleigh fading and AWGN
- **Raspberry Pi transmitter** — `transmitter_pi.py` supports Pi Camera capture with a quantized (int8) model
- **Remote execution** — MATLAB launcher scripts run Python over SSH on a remote GPU server

---

## Quick Start

### Which script to use

| Script | Use when |
|---|---|
| `sim.py` | Testing the full pipeline in software (no hardware required) |
| `transmitter.py` | Encoding an image to `combined_binary.bin` for physical transmission |
| `receiver.py` | Decoding a received binary file back to an image |
| `transmitter_pi.py` | Encoding on a Raspberry Pi (quantized model, optional Pi Camera) |
| `download_kodek.py` | Downloading the 24 Kodak test images |
| `camera_testing.py` | Testing that Pi Camera (`libcamera-still`) is working |
| `Swin_Training.py` | Training the SwinJSCC model from scratch |

### Prerequisites

- Python 3.8+
- PyTorch with CUDA (GPU recommended; CPU works but is slow for inference)
- The pretrained model weight file (see step 3)

### 1. Install dependencies

```bash
pip install torch torchvision timm numpy pillow opencv-python matplotlib \
            pytorch-msssim lpips pandas openpyxl numba requests
```

> `openpyxl` is required for Excel metric logging. `numba` is required for adaptive patching coordinate reconstruction.

### 2. Download the Kodak dataset

```bash
python download_kodek.py
```

This downloads all 24 Kodak images (`kodim01.png` … `kodim24.png`) into `Datasets/Kodak/`.

### 3. Place model weights

Download the pretrained SwinJSCC weight file and place it at:

```
Weights/SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model
```

See [Getting Model Weights](#getting-model-weights) below for download instructions or how to train from scratch.

### 4. Verify with a simulated end-to-end test

The fastest way to confirm everything is working is to run `sim.py`, which simulates the full transmit → channel → receive pipeline in software without any physical hardware:

```bash
python sim.py --type both --image_path Datasets/Kodak/kodim23.png --noise 10
```

Expected output: PSNR, MS-SSIM, and LPIPS metrics printed to stdout, and a reconstructed image saved to `recon/simulated_image.png`.

To test with codebook quantization:

```bash
python sim.py --type both --image_path Datasets/Kodak/kodim23.png \
              --use_codebook --k 512 --chunk_size 4 --noise 10
```

### 5. Transmit an image

Once the model is confirmed working, use `transmitter.py` to produce a binary file ready for physical transmission:

```bash
# Auto mode: adaptive patching decided automatically, no codebook
python transmitter.py --image_path Datasets/Kodak/kodim23.png

# With codebook (recommended for lower bandwidth)
python transmitter.py --image_path Datasets/Kodak/kodim23.png --use_codebook

# Force adaptive patching on
python transmitter.py --image_path Datasets/Kodak/kodim23.png --use_codebook --adaptive true

# Force adaptive patching off
python transmitter.py --image_path Datasets/Kodak/kodim23.png --use_codebook --adaptive false

# Custom patch size and quadtree depth
python transmitter.py --image_path Datasets/Kodak/kodim23.png --use_codebook --patch_size 60 --depth 6
```

Output: `output/combined_binary.bin` — the file to transmit over the channel.

A labelled copy is also saved to `Binary/Transmitted_Binary/{image_stem}_combined_binary_{label}.bin`.

### 6. Transmit the binary over the channel

Send `output/combined_binary.bin` over your physical or simulated channel. The received file (possibly with bit errors) is the input to the next step.

For a loopback test with no channel (lossless), pass the transmitter output directly to the receiver.

### 7. Receive and reconstruct

```bash
# Basic receive (settings auto-detected from binary header)
python receiver.py --received_file output/combined_binary.bin --image_path Datasets/Kodak/kodim23.png

# Override codebook setting manually
python receiver.py --received_file output/combined_binary.bin \
                   --image_path Datasets/Kodak/kodim23.png \
                   --use_codebook true

# Override resolution if auto-detection fails
python receiver.py --received_file output/combined_binary.bin --res_h 512 --res_w 768
```

Reconstructed image is saved under `recon/` and quality metrics (PSNR, MS-SSIM, LPIPS) are printed and appended to an Excel file.

---

## Project Structure

```
swin-semantic-communication/
├── Codebook/                        # Pre-trained vector quantization codebooks (.npy)
│   ├── codebook_{D}d_{K}clusters_{type}.npy
│   ├── adaptive_patching_codebook_{D}d_{K}clusters_{type}.npy
│   └── index_to_codeword.pkl        # Codeword lookup table for Hamming encoding (k=512)
│
├── matlab/                          # MATLAB launcher scripts
│   ├── simulation.m                 # Local simulation launcher (calls sim.py locally)
│   └── simulation_remote.m          # Remote simulation launcher (SSH + SCP)
│
├── Testing/                         # Test notebooks
│   ├── ber.ipynb                    # BER analysis
│   └── error correction/
│       └── error-correction-testing.ipynb
│
├── transmitter.py                   # Transmitter (adaptive patching, codebook, Hamming encoding)
├── transmitter_pi.py                # Transmitter for Raspberry Pi (quantized model, Pi Camera)
├── receiver.py                      # Receiver (auto-detects settings from binary header)
├── sim.py                           # Full simulated pipeline (no physical channel)
│
├── swin_functions.py                # SwinJSCC model definition and encode/decode helpers
├── codebook_functions.py            # Codebook encoding/decoding functions
├── adaptive_functions.py            # Adaptive patching (quadtree, edge detection)
├── Swin_Training.py                 # Training script
├── download_kodek.py                # Downloads all 24 Kodak images into Datasets/kodak/
├── camera_testing.py                # Pi Camera smoke-test (libcamera-still)
│
├── Adaptive_patching.ipynb          # Adaptive patching experiments
├── SwinJSCC_Training.ipynb          # Training notebook
├── swinjscc-codebook-training.ipynb # Codebook training (VQ)
├── swinjscc-full.ipynb              # Full pipeline notebook (with error correction)
├── swinjscc-full-with-adaptive-patching.ipynb      # Full pipeline + adaptive patching
├── swinjscc-full-with-adaptive-patching-new.ipynb  # Updated version with channel sim
├── swinjscc-full-simulation_normal.ipynb           # Dataset-level simulation (standard)
├── swinjscc-full-simulation_exp.ipynb              # Dataset-level simulation (experimental)
└── plot_results.ipynb               # Results plotting
```

---

## Transmitter

### CLI arguments

| Argument | Default | Description |
|---|---|---|
| `--image_path` | required | Path to input image (JPEG/DNG auto-converted to PNG; images >3500 px on any side are downscaled) |
| `--use_codebook` | off | Enable codebook quantization |
| `--adaptive` | auto | `true` / `false` to override auto-detection |
| `--k` | `512` | Codebook size (clusters): `256`, `512`, `1024` |
| `--chunk_size` | `4` | Vector dimension: `2`, `4`, `8` |
| `--patch_size` | auto | Quadtree base patch size: `28` or `60` |
| `--depth` | auto | Quadtree depth: `4`, `5`, `6`, or `7` (auto = `round(log2(max(H,W)/32))`, capped at 7) |

### Codebook combinations

| `--chunk_size` | `--k` | Codebook dimension |
|---|---|---|
| `2` | `256` | 2d, 256 clusters |
| `2` | `512` | 2d, 512 clusters |
| `4` | `512` | 4d, 512 clusters *(default)* |
| `4` | `1024` | 4d, 1024 clusters |
| `8` | `1024` | 8d, 1024 clusters |

The transmitter always loads the `_mst` codebook variant (e.g. `codebook_4d_512clusters_mst.npy`). The `_rayleigh` and `_rayleigh_gray_mapped` variants in `Codebook/` are alternative codebooks that can be swapped in manually.

### Auto-adaptive decision logic

At runtime, the transmitter computes whether adaptive patching is beneficial:

```
adaptive = (data_pixels < 0.8 × H × W)  AND  (H_new × W_new < H × W)
```

where `data_pixels = min_patch_w × min_patch_h × num_patches`. Override with `--adaptive true/false`.

### Binary header format

The transmitter writes a 5-byte control header before the payload. Each byte uses redundant bit encoding (majority voting) so the receiver can recover settings even under bit errors:

| Byte | Content |
|---|---|
| 1 | Adaptive patching flag (7-bit redundant: 0x00=off, 0x7F=on) |
| 2 | Codebook enabled flag (7-bit redundant) |
| 3 | Chunk size (2-bit × 3 repetitions: `01`=2, `10`=4, `11`=8) |
| 4 | Codebook k size (2-bit × 3 repetitions: `01`=256, `10`=512, `11`=1024) |
| 5 | Patch size flag (7-bit redundant: 0x00=28, 0x7F=60) |

For `k=512`, codebook indices are additionally mapped through `index_to_codeword.pkl` (a Hamming codeword lookup table) and stored as `uint16`, providing bit-level error correction on the index stream.

The binary payload starts immediately after the 5-byte header. The coordinate/metadata section is prepended as a separate chunk with a 4-byte length prefix (produced by `combine_binary_files()`).

### Intermediate outputs

| File | Description |
|---|---|
| `output/patches_grid.png` | Grid of selected patches (adaptive mode) |
| `output/patch_coords.bin` | Compact coordinate file for patch reconstruction |
| `output/patch_boundaries.png` | Quadtree boundaries overlaid on the original image |
| `output/combined_binary.bin` | Final binary ready to transmit |

---

## Receiver

Settings (`chunk_size`, `k`, `use_codebook`, `patch_size`, adaptive mode) are **auto-detected from the binary header** by default. CLI flags override when needed.

### CLI arguments

| Argument | Default | Description |
|---|---|---|
| `--received_file` | `combined_binary_received.bin` | Path to received binary file |
| `--image_path` | none | Original image path (for PSNR/SSIM/LPIPS comparison) |
| `--use_codebook` | auto | `true` / `false` to override header detection |
| `--k` | auto | Override codebook size from header |
| `--chunk_size` | auto | Override vector dimension from header |
| `--patch_size` | auto | Override patch size: `28` or `60` |
| `--adaptive` | auto | Override adaptive flag: `true` / `false` |
| `--res_h`, `--res_w` | auto | Override resolution read from binary header |

### Output paths

Reconstructed images are saved under `recon/` using the following structure:

- Without codebook: `recon/without_codebook/adaptive={true|false}/reconstructed_{name}.png`
- With codebook: `recon/{chunk_size}d_{k}k/adaptive={true|false}/reconstructed_{chunk_size}d_{k}k_{name}.png`

Quality metrics are appended to an Excel file in the project root:

- Without codebook: `results_without_codebook_Adaptive = {true|false}.xlsx`
- With codebook: `results_{chunk_size}d_{k}k_Adaptive = {true|false}.xlsx`

### Hamming index decoding (k=512)

When Hamming-encoded indices are received, the receiver first tries a direct codeword lookup. If the received value does not match any known codeword (due to bit errors), it falls back to a minimum Hamming distance search against all 512 codewords to recover the most likely original index.

---

## Simulation (no physical channel)

`sim.py` runs the full transmit → channel → receive pipeline in software, useful for measuring performance across datasets without hardware.

```bash
python sim.py --type both --image_path Datasets/Kodak/kodim23.png --noise 10
```

### CLI arguments

| Argument | Default | Description |
|---|---|---|
| `--type` | required | `tx` (transmit only), `rx` (receive only), `both` (full pipeline) |
| `--received_file` | `./Binary/simulated.bin` | Path to binary for receive step |
| `--image_path` | none | Input/reference image |
| `--use_codebook` | off | Enable codebook quantization |
| `--k` | `512` | Codebook clusters |
| `--chunk_size` | `4` | Vector dimension |
| `--adaptive` | auto | Override adaptive mode: `true` / `false` |
| `--patch_size` | `28` | Base patch size |
| `--noise` | `10.0` | Channel noise level (Eb/N0 in dB) |
| `--low_th` | `100` | Canny edge low threshold |
| `--high_th` | `200` | Canny edge high threshold |
| `--v_val` | `100` | Quadtree edge-count threshold |
| `--kernel` | `1` | Gaussian blur kernel size (pre-processing) |
| `--depth` | auto | Quadtree depth: `4`, `5`, `6`, or `7` |

### Channel simulation

- **Codebook path**: AWGN noise is applied at the binary level. Bits are mapped to BPSK (+1/−1), Gaussian noise is added at `Eb/N0 = noise_db` dB (`σ = sqrt(1 / (2 × 10^(SNR/10)))`), then hard-decided back to bits.
- **Non-codebook path**: the neural channel model (`pass_through_channel`) is invoked at the specified SNR before int8 quantization.

Output image: `./recon/simulated_image.png`. Metrics are printed to stdout but not written to Excel.

The notebooks `swinjscc-full-simulation_normal.ipynb` and `swinjscc-full-simulation_exp.ipynb` provide interactive versions with per-image visualization.

---

## Raspberry Pi Transmitter

`transmitter_pi.py` is a Pi-optimized variant of `transmitter.py`:

### Differences from `transmitter.py`

| Feature | transmitter.py | transmitter_pi.py |
|---|---|---|
| Model file | `SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model` | `swinjscc_quantized.pt` (dynamic int8 quantization of all `nn.Linear` layers) |
| Pi Camera | No | Yes — `--use_camera` flag |
| Header | 5-byte full header | 1-byte adaptive flag only |
| Adaptive threshold | 0.8 × H × W | 0.7 × H × W |
| Fixed depth | No (auto) | Yes — depth=5 |
| Codebook combos | All 5 | (4,512), (2,256), (8,1024) only |

### CLI arguments

| Argument | Default | Description |
|---|---|---|
| `--image_path` | none | Path to input image (use this or `--use_camera`) |
| `--use_camera` | off | Capture from Pi Camera (`libcamera-still`) |
| `--use_codebook` | off | Enable codebook quantization |
| `--adaptive` | auto | Override adaptive mode |
| `--k` | `512` | Codebook clusters |
| `--chunk_size` | `4` | Vector dimension |

### Generating the quantized model

The quantized model is not included — you must generate it from the standard `.model` weights:

```python
import torch
from swin_functions import SwinJSCC  # configure net as in transmitter.py

model_fp32 = net  # your loaded SwinJSCC model
quantized = torch.quantization.quantize_dynamic(
    model_fp32, {torch.nn.Linear}, dtype=torch.qint8
)
torch.save(quantized, "swinjscc_quantized.pt")
```

### Pi Camera testing

```bash
python camera_testing.py
```

Runs a single `libcamera-still` capture and saves the result to `image_{timestamp}.png`.

---

## MATLAB Integration

MATLAB scripts in `matlab/` launch `sim.py` via `system()`. **Run MATLAB with its working directory set to the project root** (not inside `matlab/`), so relative paths to `Datasets/`, `Weights/`, etc. resolve correctly.

### Local execution (`simulation.m`)

Edit the variable block at the top of `simulation.m` to set `imagePath`, `useCodebook`, `k`, `chunk_size`, `noise`, etc., then run:

```matlab
run('matlab/simulation.m')
```

All `sim.py` CLI arguments are supported. The Python executable path is set near the top of the file — update `pythonExe` if needed (default: `C:\Python311\cv\Scripts\python.exe`).

### Remote execution (`simulation_remote.m`)

`simulation_remote.m` uploads the image to a remote server via SCP, runs `sim.py` remotely via SSH, then downloads the results:

- For `tx`/`both`: downloads `output/patch_boundaries.png` and `Binary/simulated.bin`, displays patch boundaries in a MATLAB figure.
- For `rx`/`both`: downloads `recon/simulated_image.png`, displays the reconstructed image.

Edit these variables at the top of the script:

```matlab
remoteUser      = 'your_username';
remoteHost      = '192.168.x.x';
pythonExe       = '/path/to/python3';
remoteScriptDir = '/path/to/swin-semantic-communication';
```

---

## Model Architecture

### Variants

| Model name | SA (SNR Adaption) | RA (Rate Adaption) |
|---|---|---|
| `SwinJSCC_w/o_SAandRA` | No | No |
| `SwinJSCC_w/_SA` | Yes | No |
| `SwinJSCC_w/_RA` | No | Yes |
| `SwinJSCC_w/_SAandRA` | Yes | Yes |

### Size configurations

| `model_size` | Encoder depths | Decoder depths |
|---|---|---|
| `small` | [2,2,2,2] | [2,2,2,2] |
| `base` | [2,2,6,2] | [2,6,2,2] |
| `large` | [2,2,18,2] | [2,18,2,2] |

All sizes use `embed_dims=[128,192,256,320]`, `num_heads=[4,6,8,10]`, `window_size=8`.

### Channel Bandwidth Ratio (CBR)

| `C` (bottleneck) | CBR |
|---|---|
| `32` | 1/48 |
| `64` | 1/24 |
| `96` | 1/16 |
| `128` | 1/12 |

### Model weight filename convention

```
SwinJSCC_{model}_{channel}_HRimage_snr{snr}_psnr_C{C}.model
```

Example: `SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model`

### Other model configuration

| Parameter | Default | Options |
|---|---|---|
| `channel_type` | `rayleigh` | `rayleigh`, `awgn` |
| `multiple_snr` | `3` | Any integer (dB) |

---

## Directory Layout (auto-created at runtime)

```
output/                       # Intermediate files produced by the transmitter
│   ├── patches_grid.png      # Adaptive patch grid image
│   ├── patch_coords.bin      # Patch coordinates / resolution metadata
│   ├── patch_boundaries.png  # Quadtree boundaries on original image
│   └── combined_binary.bin   # Final binary ready to transmit

Binary/
├── Transmitted_Binary/       # Labelled copies of combined_binary.bin (per image/mode)
├── Received_Binary/          # .bin files after channel
└── Received_Text/            # Text-format received data

recon/                        # Reconstructed images
Weights/                      # Model weight files (.model, .pt)
Datasets/
├── Kodak/                    # kodim01.png … kodim24.png
├── Clic2021/                 # CLIC 2021 test images
└── DIV2K/                    # DIV2K training set
```

---

## Output Metrics

The receiver prints and saves to Excel:

| Metric | Description |
|---|---|
| PSNR | Peak Signal-to-Noise Ratio (dB), higher is better |
| MS-SSIM | Multi-Scale Structural Similarity, 0–1, higher is better |
| LPIPS | Perceptual similarity, lower is better |
| Compression Ratio | Original image size / transmitted binary size |

---

## Getting Model Weights

### Option A — Download pretrained weights (recommended)

The SwinJSCC model was published with pretrained weights. Download from the official repository:

```
https://github.com/semcomm/SwinJSCC
```

Look for a `Weights/` folder or a release attachment. Download the file named:

```
SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model
```

Place it at `Weights/` in the project root.

---

### Option B — Train from scratch

Use this if you cannot get the pretrained weights, or want to train on different settings (different SNR, channel type, bottleneck size).

#### Step 1 — Download the DIV2K training dataset

```bash
mkdir -p Datasets/DIV2K
```

Download from [https://data.vision.ee.ethz.ch/cvl/DIV2K/](https://data.vision.ee.ethz.ch/cvl/DIV2K/):
- `DIV2K_train_HR.zip` (800 images, ~3.5 GB)
- `DIV2K_valid_HR.zip` (100 images, ~430 MB)

Extract so the folder layout matches:

```
Datasets/DIV2K/
├── DIV2K_train_HR/DIV2K_train_HR/   ← 0001.png … 0800.png
└── DIV2K_valid_HR/DIV2K_valid_HR/   ← 0801.png … 0900.png
```

#### Step 2 — Download the Kodak test dataset

```bash
python download_kodek.py
```

Or manually download the 24 PNG images from [http://r0k.us/graphics/kodak/](http://r0k.us/graphics/kodak/) and place them in `Datasets/Kodak/`.

#### Step 3 — Fix the training script for training from scratch

`Swin_Training.py` has a `load_weights()` call at the top of `__main__` that tries to load an existing `.model` file before training begins. Comment it out so training starts from random initialization.

Open `Swin_Training.py` and find these two lines (around line 1973):

```python
model_path = "./Weights/SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model"
load_weights(model_path)
```

Comment them out:

```python
# model_path = "./Weights/SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model"
# load_weights(model_path)
```

#### Step 4 — Configure training settings

Edit the `Args` class in `Swin_Training.py` (around line 1836):

```python
class Args:
    def __init__(self):
        self.training = True
        self.trainset = 'DIV2K'          # dataset
        self.testset = 'kodak'           # validation set
        self.distortion_metric = 'MSE'   # 'MSE' or 'MS-SSIM'
        self.model = 'SwinJSCC_w/o_SAandRA'
        self.channel_type = 'rayleigh'   # 'rayleigh' or 'awgn'
        self.C = '32'                    # bottleneck: 32/64/96/128
        self.multiple_snr = '3'          # training SNR in dB
        self.model_size = 'base'         # 'small', 'base', or 'large'
```

Also check `total_epochs` and `save_freq` at the bottom of the file:

```python
total_epochs = 100    # increase for better convergence (paper uses ~1000)
save_freq = 5         # save a checkpoint every N epochs
```

#### Step 5 — Create the Weights directory and run

```bash
mkdir -p Weights history/models
python Swin_Training.py
```

Training prints a log line every 100 steps:

```
Epoch 1 | Step [100/50=2.00%] | Loss 0.042 | CBR 0.0208 | SNR 3.0 | PSNR 28.3 | MSSSIM 0.912 | Lr 0.0001
```

Checkpoints are saved to `history/models/` every `save_freq` epochs, named:

```
history/models/YYYY-MM-DD-HH_MM_SS_EP5.model
history/models/YYYY-MM-DD-HH_MM_SS_EP10.model
```

#### Step 6 — Install the trained weights

After training finishes (or at any checkpoint you want to use), copy the best checkpoint to the expected path:

```bash
mkdir -p Weights
cp history/models/<your_best_checkpoint>.model \
   Weights/SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model
```

#### Step 7 — (Optional) Resume from a checkpoint

To resume interrupted training or fine-tune from a checkpoint, update the `load_weights` call in `Swin_Training.py`:

```python
model_path = "history/models/<your_checkpoint>.model"
load_weights(model_path)
```

---

### Training tips

| Setting | Recommendation |
|---|---|
| GPU | Required. Training on CPU is too slow. A single RTX 3080 / A100 takes ~10–20 hours for 100 epochs on DIV2K. |
| Batch size | Default is 16 for 256×256 crops. Reduce to 8 if you run out of VRAM. |
| SNR | Start with `multiple_snr = '3'` (low SNR, harder task). Train separate models per SNR value. |
| Convergence | 100 epochs gives a reasonable model. The original paper trains for ~1000 epochs for best PSNR. |
| Loss | `MSE` converges faster. `MS-SSIM` gives better perceptual quality but is slower to optimize. |

---

## Training Codebooks

Codebooks (used by `--use_codebook`) are pre-trained and already in `Codebook/`. To retrain them (e.g. for a new model or different patch size), use `swinjscc-codebook-training.ipynb`. You need a trained `.model` file first.

The `Codebook/` directory contains three naming variants per dimension/cluster combination:

| Suffix | Description |
|---|---|
| `_mst` | Trained with minimum spanning tree initialization (used by default) |
| `_rayleigh` | Trained on Rayleigh channel features |
| `_rayleigh_gray_mapped` | Rayleigh features with gray-code index mapping |
