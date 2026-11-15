# 纸艺二维码 · Paper QR Styles

qrbtf（latentcat/qrbtf）参数化思路的离线实现，风格按 Miller 给的 3 张图做的。

## 风格

| 风格 | 来源 | 码的样子 |
|---|---|---|
| 银白纸雕 Silver Papercut | 白纸条、银发少女，深底白花 | 白圆点模块，深底（反色码） |
| 蓝金纸花 Blue-Gold Paper Flower | 宝蓝描金、红玫瑰纸花层叠 | 宝蓝菱形模块，金边框 |
| 黑白花嫁 Black Lace Bridal | 黑花蕾丝白纱、红花瓣 | 黑圆点模块，白底 |

参考原图在 `styles/` 里。

## 用法（离线）

打开 `index.html` 就能用，不用联网、不用注册、不用装东西：

1. 输入链接或文字
2. 选一种风格
3. 下载 PNG / SVG（手机上长按图片也能保存）

## 做法来源

qrbtf 分两部分：AI 生成（G1）要联网跑它家的训练模型，离线做不了；
**参数化（A1/A2/C2）是开源、无后端的**——先编码出二维码矩阵，再按定位点 /
校正点 / 数据点分别画成不同形状、颜色、大小。本项目抄的是这个参数化思路，
编码器用 MIT 的 Nayuki QR-Code-generator（中文自动加 ECI 26 标记），渲染代码新写，
没有照搬 qrbtf 的源码。

## 为什么能扫（实测）

- 定位角是标准 7×7（实心外框＋5×5 留白＋3×3 实心），装饰不许碰
- 数据点填满到 0.94 格以上，默认 H 级纠错（坏 30% 还能读），留白 4 格以上
- 装饰只放在外圈边框和三个外角
- ZXing 实测：3 种风格 × 3 种内容（链接、中文、长链接）**9/9 能扫**
- 教训：第一版在定位角上加了描金环和花瓣，三个风格全扫不出来，已改掉

注意：银白纸雕是反色码（白码深底），微信和安卓能扫，iPhone 自带相机可能扫不出，
用微信扫最稳。

## 两种做法（A / B）

见 `ai-qr-two-ways.html`，两种方案，**点一张卡就能选**：

- **A · 风格原图打底**：用你上传的 3 张风格原图做底，参数化二维码画上去，离线 1 秒/张，保底能扫
- **B · 本地慢速生成**：Stable Diffusion + ControlNet QR，在 Kaggle 双 T4 / Colab T4 免费 GPU 上跑，图本身就是码，2–5 分钟/张，效果最好

B 的安装包在 `installer/` 里：`qr-art-installer.zip`，解压后双击 `setup.bat`（Windows）或跑 `bash setup.sh`（Mac/Linux）。**安装包不含大模型**，模型在安装时从 HuggingFace 下载（SD 1.5 + ControlNet QR，fp16 约 3GB，2026-11-15 核实不用授权、不用 token），先跑 `python download_models.py --check` 可以只核查不下载。

## 文件

- `index.html` — 离线单文件工具（编码器 + 3 种风格 + 样式缩略图全在里面）
- `ai-qr-two-ways.html` — 两种 AI 生图方案的可视化对比
- `styles/ref-*.jpg` — 3 张风格参考图
- `index.template.html` / `ai-qr-two-ways.template.html` — 源码模板（构建时把编码器和缩略图嵌进去）

## License

代码 MIT（Nayuki QR-Code-generator 同为 MIT）。qrbtf 本身是 GPL-3.0，
本项目没有复制它的源码，只是借鉴了参数化渲染的思路。
