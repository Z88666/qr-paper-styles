#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载纸艺二维码 B 方案要用的模型（安装时远程下载，安装包本身不含模型）。
模型来源（2026-11-15 核实）：
  - SD 1.5：stable-diffusion-v1-5/stable-diffusion-v1-5，不用授权、不用 token
  - ControlNet QR：DionTimmer/controlnet_qrcode-control_v1p_sd15，公开
只下 fp16，约 3GB。需要联网；下载可断点续传（huggingface_hub 自带）。
用法：
  python download_models.py            # 下载到 ./models/
  python download_models.py --check    # 只核查，不下载
  python download_models.py --models-dir D:\\qr-models
"""
import argparse
import json
import os
import shutil
import sys
import urllib.request

SD_REPO = "stable-diffusion-v1-5/stable-diffusion-v1-5"
CN_REPO = "DionTimmer/controlnet_qrcode-control_v1p_sd15"

# SD 1.5 只下 fp16 + 配置，省一半流量；safety_checker 不要（省 1GB+）。
# 注意：不用 "*.json" 通配——它会把 safety_checker/config.json 也拉下来，
# 但权重不下，pipeline 加载时会在有 config 无权重的情况下报错；
# 所以 JSON 文件全部显式列出，safety_checker 整个跳过（加载时传 safety_checker=None）。
SD_PATTERNS = [
    "model_index.json",
    "tokenizer/*.json", "tokenizer/*.txt",
    "scheduler/*",
    "feature_extractor/*",
    "unet/diffusion_pytorch_model.fp16.safetensors",
    "unet/config.json",
    "text_encoder/model.fp16.safetensors",
    "text_encoder/config.json",
    "vae/diffusion_pytorch_model.fp16.safetensors",
    "vae/config.json",
]
CN_PATTERNS = [
    "config.json",
    "diffusion_pytorch_model.fp16.safetensors",
]


def tree_sizes(repo):
    """用 HuggingFace tree API（recursive）查文件大小（不下载），返回 {path: size}。"""
    url = "https://huggingface.co/api/models/%s/tree/main?recursive=true" % repo
    req = urllib.request.Request(url, headers={"User-Agent": "qr-paper-installer"})
    with urllib.request.urlopen(req, timeout=60) as r:
        items = json.load(r)
    return {it["path"]: it.get("size", 0) for it in items if it.get("type") == "file"}


def check_only():
    import fnmatch
    print("核查模型（不下载）...")
    total = 0
    for repo, patterns in ((SD_REPO, SD_PATTERNS), (CN_REPO, CN_PATTERNS)):
        sizes = tree_sizes(repo)
        print("\n%s" % repo)
        matched = {}
        for path, size in sorted(sizes.items()):
            for pat in patterns:
                if fnmatch.fnmatch(path, pat):
                    matched[path] = size
                    break
        sub = 0
        for path, size in sorted(matched.items()):
            if size >= 100 * 1024 * 1024:  # 只打印 100MB 以上的大文件
                print("  %-55s %6.2f GB" % (path, size / 1e9))
            sub += size
        print("  小计约 %.2f GB（%d 个文件）" % (sub / 1e9, len(matched)))
        total += sub
    print("\n模型合计约 %.2f GB（fp16），另需运行库约 2.5GB，硬盘至少留 12GB。" % (total / 1e9))
    print("核查通过：两个仓库都能访问。")


def main():
    ap = argparse.ArgumentParser(description="下载 SD1.5 + ControlNet QR 模型")
    ap.add_argument("--models-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"))
    ap.add_argument("--check", action="store_true", help="只核查，不下载")
    args = ap.parse_args()

    if args.check:
        check_only()
        return 0

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("缺 huggingface_hub，先跑：pip install -r requirements.txt")
        return 1

    free_gb = shutil.disk_usage(args.models_dir if os.path.exists(args.models_dir) else ".").free / 1e9
    print("硬盘剩余 %.1f GB（建议至少 12GB）" % free_gb)
    if free_gb < 12:
        print("警告：剩余空间不足 12GB，下载可能中途失败，先清点空间再继续。")
        ans = input("还要继续吗？(y/N) ").strip().lower()
        if ans != "y":
            return 2

    print("\n[1/2] 下载 SD 1.5（fp16，约 2.2GB）...")
    snapshot_download(repo_id=SD_REPO, local_dir=os.path.join(args.models_dir, "sd15"),
                      allow_patterns=SD_PATTERNS)
    print("[1/2] SD 1.5 下好了。")

    print("\n[2/2] 下载 ControlNet QR（fp16，约 0.7GB）...")
    snapshot_download(repo_id=CN_REPO, local_dir=os.path.join(args.models_dir, "controlnet_qr"),
                      allow_patterns=CN_PATTERNS)
    print("[2/2] ControlNet QR 下好了。")

    print("\n模型全部就绪：%s" % args.models_dir)
    print("下一步：python generate_qr.py --text \"https://example.com\" --style paperflower")
    return 0


if __name__ == "__main__":
    sys.exit(main())
