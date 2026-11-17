#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B 方案：SD 1.5 + ControlNet QR，生成图码一体的纸艺二维码。
模型在安装时已由 download_models.py 下载到 ./models/，这里不再下载。
用法（先激活虚拟环境，见 README-installer.md）：
  python generate_qr.py --text "https://example.com" --style paperflower
  python generate_qr.py --text "你好" --style bridal --steps 30 --seed 42
  python generate_qr.py --text "https://example.com" --style bridal --control-only  # 只做控制图并验扫，不加载模型
风格：papercut（银白纸雕）/ paperflower（蓝金纸花）/ bridal（黑白花嫁）
出图后自动用 OpenCV 验扫，通过才算数；没通过就换个种子再跑一张。
注意：纯 CPU 很慢（20-60 分钟/张），有 GPU（CUDA）才推荐。
"""
import argparse
import os
import random
import sys
import time

STYLES = {
    "papercut": {
        "name": "银白纸雕",
        "prompt": ("intricate white paper-cut art, elegant silver-haired girl made of "
                   "white paper strips, swirling paper ribbons, dark charcoal background, "
                   "delicate papercraft, layered paper sculpture, high detail"),
    },
    "paperflower": {
        "name": "蓝金纸花",
        "prompt": ("ornate paper flower art, royal blue and gold quilling, red roses, "
                   "baroque floral paper sculpture, elegant woman in a layered paper dress, "
                   "gold filigree, luxurious, highly detailed"),
    },
    "bridal": {
        "name": "黑白花嫁",
        "prompt": ("elegant bridal lace, black floral lace on white silk, white bridal veil, "
                   "red rose petals on the floor, black and white floral pattern, "
                   "high fashion photography, highly detailed"),
    },
}
NEGATIVE = "blurry, low quality, distorted, deformed, watermark, text, letters, lowres, bad anatomy"


def make_control_qr(text, size=768):
    """生成 ControlNet 用的标准黑白二维码图（纠错 H，纯黑白方块，最容易被模型还原）。"""
    import qrcode
    from PIL import Image
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,
                       box_size=10, border=4)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.NEAREST)


def snap_modules(img, control, text, strength=0.7):
    """把生成图的每个二维码方块往控制图的黑/白推（只动亮度，保住颜色和画面）。
    原图直接扫经常失败：画把方块染成红色、盖住定位点，扫码器找不到码。
    2026-11-15 Colab 实测：原图 0/7 能扫，推 0.7 后 3 张 1.3 强度的全能扫（ZXing；其中 2 张 OpenCV 也能扫）。"""
    import numpy as np
    import qrcode
    ctrl = np.array(control.convert("L"))
    h, w = ctrl.shape
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,
                      box_size=10, border=4)
    q.add_data(text)
    q.make(fit=True)
    n = q.modules_count + 8
    b = [round(i * w / n) for i in range(n + 1)]
    black = np.zeros((n, n), dtype=bool)
    for r in range(n):
        for c in range(n):
            black[r, c] = ctrl[(b[r] + b[r + 1]) // 2, (b[c] + b[c + 1]) // 2] < 128
    out = np.array(img).astype(np.float32)
    for r in range(n):
        for c in range(n):
            cell = out[b[r]:b[r + 1], b[c]:b[c + 1]]
            if black[r, c]:
                cell *= (1.0 - strength)
            else:
                cell += (255.0 - cell) * strength
    from PIL import Image
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def verify(path, want):
    """用 OpenCV 解码刚生成的图，返回 (是否通过, 解出的内容)。"""
    try:
        import cv2
    except ImportError:
        return None, "没装 opencv-python-headless，无法自动验扫，请用手机扫一下"
    img = cv2.imread(path)
    if img is None:
        return False, "读不到图片"
    det = cv2.QRCodeDetector()
    data, _, _ = det.detectAndDecode(img)
    if data == want:
        return True, data
    return False, (data if data else "解不出来")


def main():
    ap = argparse.ArgumentParser(description="SD1.5 + ControlNet QR 生成纸艺二维码")
    ap.add_argument("--text", required=True, help="二维码内容（链接或文字）")
    ap.add_argument("--style", default="paperflower", choices=list(STYLES),
                    help="风格：papercut / paperflower / bridal")
    ap.add_argument("--out", default="outputs", help="输出文件夹")
    ap.add_argument("--steps", type=int, default=25, help="采样步数，默认 25")
    ap.add_argument("--scale", type=float, default=0.9,
                    help="ControlNet 强度 0-1，默认 0.9；扫不出来就调高，图太像码就调低")
    ap.add_argument("--seed", type=int, default=-1, help="随机种子，-1 为随机")
    ap.add_argument("--size", type=int, default=768, help="出图边长，默认 768")
    ap.add_argument("--control-only", action="store_true",
                    help="只做控制图并验扫，不加载模型（不花 GPU 时间，先确认控制图本身能扫）")
    ap.add_argument("--no-verify", action="store_true", help="跳过自动验扫")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    sd_path = os.path.join(here, "models", "sd15")
    cn_path = os.path.join(here, "models", "controlnet_qr")
    if args.control_only:
        # 只做控制图：不碰模型，适合在没 GPU 的机器上先验控制图
        print("只做控制图（--control-only），不加载模型。")
        control = make_control_qr(args.text, args.size)
        os.makedirs(args.out, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        control_path = os.path.join(args.out, "qr-%s-%s-control.png" % (args.style, stamp))
        control.save(control_path)
        print("控制图：%s" % control_path)
        ok, got = verify(control_path, args.text)
        if ok is None:
            print("验扫提示：%s" % got)
            return 0
        if ok:
            print("验扫通过：扫出来就是 %r" % got)
            return 0
        print("验扫没通过（解出 %r）——控制图本身有问题，先别上 GPU。" % got)
        return 2
    if not os.path.isdir(sd_path) or not os.path.isdir(cn_path):
        print("模型还没下载，先跑：python download_models.py")
        return 1
    if args.seed < 0:
        args.seed = random.randint(0, 2 ** 31 - 1)

    print("风格：%s（%s），种子 %d" % (args.style, STYLES[args.style]["name"], args.seed))
    print("先做 ControlNet 控制图（标准二维码）...")
    control = make_control_qr(args.text, args.size)
    os.makedirs(args.out, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = "qr-%s-%s" % (args.style, stamp)
    control_path = os.path.join(args.out, base + "-control.png")
    control.save(control_path)

    print("加载模型（第一次要几十秒）...")
    import torch
    from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("警告：没检测到 GPU，纯 CPU 一张要 20-60 分钟，建议用 Kaggle/Colab 的免费 T4 跑。")
    dtype = torch.float16 if device == "cuda" else torch.float32
    controlnet = ControlNetModel.from_pretrained(cn_path, torch_dtype=dtype, variant="fp16")
    # 只下了 fp16 文件，所以 variant 固定 fp16（CPU 也一样，读进来再转 fp32）
    # safety_checker=None：我们没下 safety_checker，传 None 跳过它（作者示例同款写法），
    # 否则 diffusers 会在有 config 无权重时报错；DDIM 是作者示例用的调度器，确定性好、种子可复现
    from diffusers import DDIMScheduler
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        sd_path, controlnet=controlnet, torch_dtype=dtype, variant="fp16",
        safety_checker=None)
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
    pipe.to(device)
    try:
        pipe.enable_attention_slicing()
    except Exception:
        pass
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass

    print("生成中（T4 约 2-5 分钟，CPU 很慢，别关窗口）...")
    gen = torch.Generator(device=device).manual_seed(args.seed)
    out = pipe(prompt=STYLES[args.style]["prompt"], negative_prompt=NEGATIVE,
               image=control, num_inference_steps=args.steps,
               controlnet_conditioning_scale=args.scale,
               guidance_scale=7.5, generator=gen).images[0]
    art_path = os.path.join(args.out, base + ".png")
    out.save(art_path)
    print("出图：%s" % art_path)
    print("控制图（对照用）：%s" % control_path)
    # 原图直接扫经常失败，先按控制图推一遍亮度（0.7）再验扫，推过的是成品
    snapped = snap_modules(out, control, args.text)
    snap_path = art_path.replace(".png", "-snap0.7.png")
    snapped.save(snap_path)
    print("推亮度后的图（成品，验扫用）：%s" % snap_path)

    if args.no_verify:
        print("已跳过验扫，请用手机扫一下确认。")
        return 0
    ok, got = verify(snap_path, args.text)
    if ok is None:
        print("验扫提示：%s" % got)
    elif ok:
        print("验扫通过：扫出来就是 %r" % got)
    else:
        print("验扫没通过（解出 %r）。换个种子再跑：--seed %d，或把 --scale 调到 1.0。"
              % (got, args.seed + 1))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
