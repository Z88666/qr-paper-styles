# 纸艺二维码 B 方案 · 安装包

Stable Diffusion 1.5 + ControlNet QR，生成图码一体的纸艺二维码（图本身就是码）。

## 安装包里有什么（没有大模型）

| 文件 | 作用 |
|---|---|
| `setup.bat` / `setup.sh` | 一键安装：建虚拟环境 → 装 torch 和运行库 → 下载模型 |
| `download_models.py` | 下载模型：SD 1.5 + ControlNet QR（fp16，约 3GB） |
| `generate_qr.py` | 生成图片 + 自动验扫 |
| `requirements.txt` | 运行库清单 |
| `README-installer.md` | 本文件 |

**模型在安装时才从 HuggingFace 下载**，安装包本身只有几十 KB：
- SD 1.5：`stable-diffusion-v1-5/stable-diffusion-v1-5`（2026-11-15 核实：不用授权、不用 token）
- ControlNet QR：`DionTimmer/controlnet_qrcode-control_v1p_sd15`（公开）
- 只下 fp16，约 3GB；运行库（torch 等）约 2.5GB；硬盘至少留 12GB。

## 安装

需要：Python 3.10+、联网、硬盘 12GB 以上。有 NVIDIA 显卡会快很多。

**Windows**：解压后双击 `setup.bat`，按提示等它跑完。
**Mac / Linux**：解压后在文件夹里跑 `bash setup.sh`。

只想先核查模型能不能下（不下载）：
```
python download_models.py --check
```

## 生成

```bash
# 先激活虚拟环境（Windows：.venv\Scripts\activate.bat；Mac/Linux：source .venv/bin/activate）
python generate_qr.py --text "https://example.com" --style paperflower
python generate_qr.py --text "你好" --style bridal --steps 30 --seed 42
python generate_qr.py --text "https://example.com" --style papercut --scale 1.0
```

风格：`papercut`（银白纸雕）/ `paperflower`（蓝金纸花）/ `bridal`（黑白花嫁）。

出图在 `outputs/` 里，每张同时存一张 `-control.png`（标准黑白码，对照用）。
生成完自动验扫：**通过才算数**。没通过就换个种子再跑，或把 `--scale` 调到 1.0。

## 要多久

| 设备 | 一张 |
|---|---|
| T4 显卡（Kaggle/Colab 免费） | 约 2–5 分钟 |
| 好一点的 NVIDIA 显卡 | 约 1–2 分钟 |
| 纯 CPU | 20–60 分钟，不推荐 |

## 没显卡？用免费 GPU 跑同一套

Miller 已有 Kaggle 双 T4（每周 30 小时）和 Colab T4，都验证过。
Kaggle 上已备好现成笔记本 `../b-run/bridal-notebook.ipynb`（黑白花嫁），上传即跑。
不用笔记本、想手动跑同一套时，把这个文件夹传到 Kaggle/Colab 里，跑下面几行就行（不用 setup 脚本）：

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"  # Kaggle/Colab 自带 torch+CUDA，显示 True 就跳过下一行
pip install torch --index-url https://download.pytorch.org/whl/cu121  # 只有上面显示 False（没装 torch 或没显卡）时才跑
pip install -r requirements.txt
python download_models.py
python generate_qr.py --text "https://example.com" --style paperflower
```

注意：Kaggle/Colab 自带的 torch 别重装——重装要十几分钟，还可能把环境搞坏；先查 `torch.cuda.is_available()`，是 True 就直接用。

## 常见问题

- **下载中断**：重新跑 `setup.bat` / `setup.sh` 或 `python download_models.py`，会断点续传。
- **硬盘不够**：先清出 12GB 再装。
- **torch 装不上**：检查 Python 是不是 3.10+，以及网络能不能上 pypi.org 和 huggingface.co。
- **显存不够（CUDA out of memory）**：把 `--size` 改小，如 `--size 512`，或 `--steps` 改成 20。
- **每张都扫不出来**：把 `--scale` 调到 1.0 再试；还不行就换 `--seed` 多抽几张，ControlNet QR 本来就要抽卡。
- **银白纸雕扫不出**：那款是反色码（白码深底），微信和安卓能扫，iPhone 自带相机可能扫不出，用微信扫。
