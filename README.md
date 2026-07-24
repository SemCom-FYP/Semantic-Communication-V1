# SwinJSCC Semantic Communication

End-to-end image transmission system over wireless channels using a Swin Transformer-based Joint Source-Channel Coding (JSCC) model. Images are encoded directly into channel symbols, transmitted as a compact binary file, and reconstructed at the receiver — no separate source and channel coding steps.

Key features:
- **Adaptive patching** — quadtree edge-detection selects informative patches, reducing transmitted data for smooth/uniform images
- **Codebook quantization** — vector quantization maps encoded features to discrete codewords (2d/4d/8d, 256–1024 clusters)
- **Hamming error correction** — redundant bit encoding on the 5-byte control header and codeword indices
- **Channel support** — Rayleigh fading and AWGN
- **Raspberry Pi transmitter** — `transmitter_pi.py` supports Pi Camera capture
- **Remote execution** — MATLAB launcher scripts run Python over SSH on a remote GPU server

---

## Quick Start

### 1. Install dependencies

```bash
pip install torch torchvision timm numpy pillow opencv-python matplotlib \
            pytorch-msssim lpips pandas openpyxl
```

### 2. Place model weights

Download the pretrained SwinJSCC weight file and place it at:

```
Weights/SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model
```

### 3. Transmit an image

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

### 4. Receive and reconstruct

```bash
# Basic receive (settings auto-detected from binary header)
python receiver.py --received_file output/combined_binary_received.bin --image_path Datasets/Kodak/kodim23.png

# Override codebook setting manually
python receiver.py --received_file output/oucombined_binary_received.bin \
                   --image_path Datasets/Kodak/kodim23.png \
                   --use_codebook true

# Override resolution if auto-detection fails
python receiver.py --received_file output/combined_binary_received.bin --res_h 512 --res_w 768
```

Reconstructed image is saved under `recon/` and quality metrics (PSNR, MS-SSIM, LPIPS) are printed and appended to an Excel file.

---

## Project Structure

```
swin-semantic-communication/
├── Codebook/                        # Pre-trained vector quantization codebooks (.npy)
│   ├── codebook_{D}d_{K}clusters_{type}.npy
│   ├── adaptive_patching_codebook_{D}d_{K}clusters_{type}.npy
│   └── index_to_codeword.pkl        # Codeword lookup table for Hamming encoding
│
├── matlab/                          # MATLAB launcher scripts
│   ├── matlab_transmitter.m         # Run transmitter.py locally
│   ├── matlab_receiver.m            # Run receiver.py locally
│   ├── remote_transmit.m            # Run transmitter.py on remote server via SSH
│   ├── remote_receive.m             # Run receiver.py on remote server via SSH
│   ├── simulation.m                 # Local simulation launcher
│   └── simulation_remote.m          # Remote simulation launcher
│
├── Testing/                         # Test notebooks
│   ├── ber.ipynb                    # BER analysis
│   └── error correction/
│       └── error-correction-testing.ipynb
│
├── transmitter.py                   # Transmitter (adaptive patching, codebook, Hamming encoding)
├── transmitter_pi.py                # Transmitter for Raspberry Pi (Pi Camera support)
├── receiver.py                      # Receiver (auto-detects settings from binary header)
├── sim.py                           # Full simulated pipeline (no physical channel)
│
├── swin_functions.py                # SwinJSCC model definition and encode/decode helpers
├── codebook_functions.py            # Codebook encoding/decoding functions
├── adaptive_functions.py            # Adaptive patching (quadtree, edge detection)
├── Swin_Training.py                 # Training script
├── camera_testing.py                # Pi Camera utility
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
| `--image_path` | required | Path to input image (JPEG/DNG auto-converted to PNG) |
| `--use_codebook` | off | Enable codebook quantization |
| `--adaptive` | auto | `true` / `false` to override auto-detection |
| `--k` | `512` | Codebook size (clusters): `256`, `512`, `1024` |
| `--chunk_size` | `4` | Vector dimension: `2`, `4`, `8` |
| `--patch_size` | auto | Quadtree base patch size: `28` or `60` |
| `--depth` | auto | Quadtree depth: `4`, `5`, `6`, or `7` |

### Codebook combinations

| `--chunk_size` | `--k` | Codebook dimension |
|---|---|---|
| `2` | `256` | 2d, 256 clusters |
| `2` | `512` | 2d, 512 clusters |
| `4` | `512` | 4d, 512 clusters *(default)* |
| `4` | `1024` | 4d, 1024 clusters |
| `8` | `1024` | 8d, 1024 clusters |

### Binary header format

The transmitter writes a 5-byte control header before the payload. Each byte uses redundant bit encoding (majority voting) so the receiver can recover settings even under bit errors:

| Byte | Content |
|---|---|
| 1 | Adaptive patching flag (7-bit redundant) |
| 2 | Codebook enabled flag (7-bit redundant) |
| 3 | Chunk size (2-bit × 3 repetitions: `01`=2, `10`=4, `11`=8) |
| 4 | Codebook k size (2-bit × 3 repetitions: `01`=256, `10`=512, `11`=1024) |
| 5 | Patch size flag (7-bit redundant: 0=28, 1=60) |

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

---

## Simulation (no physical channel)

`sim.py` runs the full transmit → channel → receive pipeline in software, useful for measuring performance metrics across datasets without hardware.

```bash
python sim.py
```

Configure dataset paths and SNR values inside the script. Results are saved to `recon/` and logged to Excel.

The notebooks `swinjscc-full-simulation_normal.ipynb` and `swinjscc-full-simulation_exp.ipynb` provide interactive versions with per-image visualization.

---

## MATLAB Integration

MATLAB scripts in `matlab/` launch the Python scripts via `system()`. **Run MATLAB with its working directory set to the project root** (not inside `matlab/`), so relative paths to `Datasets/`, `Weights/`, etc. resolve correctly.

### Local execution

```matlab
% In MATLAB, cd to project root first, then:
run('matlab/matlab_transmitter.m')
run('matlab/matlab_receiver.m')
```

Edit the variable block at the top of each script to set `imagePath`, `useCodebook`, `k`, `chunk`, etc.

### Remote execution (SSH)

`remote_transmit.m` / `remote_receive.m` upload the image to a remote server via SCP, run the Python script remotely via SSH, then download the result back. `remote_receive.m` also parses the Python output to auto-detect used parameters and logs results to `results_summary.xlsx`.

Edit the top of each script to set `remoteUser`, `remoteHost`, `remotePython`, `remoteScriptDir`.

---

## Model Configuration

The model is configured in the `Args` and `config` classes inside each script:

| Parameter | Default | Options |
|---|---|---|
| `model` | `SwinJSCC_w/o_SAandRA` | `SwinJSCC_w/o_SAandRA`, `SwinJSCC_w/_SA`, `SwinJSCC_w/_RA`, `SwinJSCC_w/_SAandRA` |
| `channel_type` | `rayleigh` | `rayleigh`, `awgn` |
| `C` (bottleneck) | `32` | `32` (1/48 CBR), `64` (1/24), `96` (1/16), `128` (1/12) |
| `multiple_snr` | `3` | Any integer (dB) |
| `model_size` | `base` | `small`, `base`, `large` |

Model weight filename convention:
```
SwinJSCC_{model}_{channel}_HRimage_snr{snr}_psnr_C{C}.model
```

---

## Directory Layout (auto-created at runtime)

```
output/                    # Intermediate files produced by the transmitter
│   ├── patches_grid.png   # Adaptive patch grid image
│   ├── patch_coords.bin   # Patch coordinates / resolution metadata
│   └── combined_binary.bin  # Final binary ready to transmit

Binary/
├── Transmitted_Binary/    # Labelled copies of combined_binary.bin (per image/mode)
└── Received_Binary/       # .bin files after channel

recon/                     # Reconstructed images
Weights/                   # Model weight files (.model)
Datasets/
├── Kodak/                 # kodim01.png … kodim24.png
├── Clic2021/              # CLIC 2021 test images
└── DIV2K/                 # DIV2K training set
```

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

Place it at `Weights/` in the project root:

```bash
mkdir -p Weights
# then move the downloaded file here
```

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
mkdir -p Datasets/Kodak
```

Download 24 PNG images from [http://r0k.us/graphics/kodak/](http://r0k.us/graphics/kodak/) (`kodim01.png` … `kodim24.png`) and place them in `Datasets/Kodak/`.

#### Step 3 — Fix the training script for training from scratch

`Swin_Training.py` has a `load_weights()` call at the top of `__main__` that tries to load an existing `.model` file before training begins. Comment it out so training starts from random initialization:

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
...
```

#### Step 6 — Install the trained weights

After training finishes (or at any checkpoint you want to use), copy the best checkpoint to the expected path:

```bash
mkdir -p Weights
cp history/models/<your_best_checkpoint>.model \
   Weights/SwinJSCC_wo_SAandRA_Rayleigh_HRimage_snr3_psnr_C32.model
```

The transmitter and receiver scripts load weights from that fixed path, so naming it correctly is important.

#### Step 7 — (Optional) Resume from a checkpoint

To resume interrupted training or fine-tune from a checkpoint, un-comment (or update) the `load_weights` call in `Swin_Training.py`:

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

---

## Output Metrics

The receiver prints and saves to Excel:

| Metric | Description |
|---|---|
| PSNR | Peak Signal-to-Noise Ratio (dB), higher is better |
| MS-SSIM | Multi-Scale Structural Similarity, 0–1, higher is better |
| LPIPS | Perceptual similarity, lower is better |
| Compression Ratio | Original image size / transmitted binary size |
