# ComfyUI-ShellAgent-Plugin

This repository provides utility nodes for defining inputs and outputs in ComfyUI workflows. These nodes are essential for running [ShellAgent](https://github.com/myshell-ai/ShellAgent) apps with ComfyUI, but they can also be used independently to specify input/output variables and their requirements explicitly.

## Installation

To install, either:

1. Download or clone this repository into the ComfyUI/custom_nodes/ directory.
2. Use the ComfyUI-Manager.

## Features

### Input Nodes

- Input Text
- Input Image
- Input Float
- Input Integer
- Input Video

Each input node supports setting a default value and additional configuration options.

### Output Nodes

- Save Image
- Save Images
- **Save Video - VHS** (视频组合与加密节点)
- Output Text
- Output Float
- Output Integer

---

## 🎬 视频输出功能详解

### Video Combine Encrypt 节点

这个节点将图像序列合成视频,支持多种格式和高级编码选项。

#### 🎯 快速开始 (推荐新手)

**基本配置**:
1. 连接图像序列到 `images` 输入
2. 设置 `frame_rate` (默认24fps)
3. 选择 `format`: **`video/h264-mp4`** (推荐,Mac/iOS兼容)
4. 点击执行

**结果**: 生成Mac兼容的高质量MP4视频

---

#### 📋 支持的视频格式

| 格式 | 描述 | Mac兼容 | 适用场景 |
|------|------|---------|---------|
| **video/h264-mp4** ✅ | H.264 标准格式 | ✅ 完美 | 日常使用,社交媒体,网页 |
| **video/h265-mp4** | H.265 高压缩 | ✅ 支持 | 节省空间,4K视频 |
| **video/vp9-webm** | VP9 网页格式 | ✅ 支持 | 网页嵌入,流媒体 |
| **video/mov** | QuickTime格式 | ✅ 完美 | Mac原生格式 |
| **video/avi** | AVI旧格式 | ✅ 支持 | 兼容性需求 |
| **video/h264-advanced** ⚙️ | H.264 高级模式 | ⚠️ 取决于配置 | 自定义参数 |
| **video/h264-high444** 🎥 | H.264 High 4:4:4 | ❌ 不兼容 | 专业后期制作 |
| **video/ffmpeg-manual** 🔧 | 完全手动模式 | ⚠️ 取决于配置 | 专家级自定义 |

---

#### ⚙️ 高级参数说明

当选择 `h264-advanced` 或 `ffmpeg-manual` 格式时,可以使用以下可选参数:

**编码参数**:
- `advanced_preset`: 编码速度 (ultrafast → veryslow)
  - `medium` (推荐): 速度与质量平衡
  - `slow`: 更好的质量,编码更慢
  - `fast`: 更快的编码,质量略低

- `advanced_crf`: 质量控制 (0-51)
  - `0`: 无损 (文件巨大)
  - `18-20`: 视觉无损 (推荐)
  - `23-28`: 高质量,适中文件大小
  - `51`: 最差质量

- `advanced_pix_fmt`: 像素格式
  - **`yuv420p`** ✅: Mac/iOS兼容 (推荐)
  - `yuv444p` ⚠️: 最高质量,但Mac不兼容
  - `yuv444p10le`: 10位高质量,Mac不兼容

- `advanced_tune`: 优化类型
  - `none` (默认): 通用优化
  - `film`: 适合电影内容
  - `animation`: 适合动画
  - `grain`: 保留胶片颗粒
  - `stillimage`: 适合静态图片序列

**色彩参数**:
- `advanced_colorspace`: 色彩空间 (bt709/bt601/bt2020nc)
- `advanced_color_range`: 色彩范围 (tv=16-235 / pc=0-255)

**专家参数**:
- `advanced_x264_params`: x264高级参数字符串
  - 例如: `aq-mode=3:aq-strength=0.8:deblock=-1,-1`

---

#### 🎓 使用场景示例

##### 场景1: 日常视频发布到社交媒体

```yaml
format: video/h264-mp4
quality: 85
# 自动使用 yuv420p, Mac/手机完美播放
```

**适用**: YouTube, Bilibili, 抖音, 朋友圈

---

##### 场景2: 高质量视频存档

```yaml
format: video/h264-mp4
quality: 95
# 或使用高级模式:
format: video/h264-advanced
advanced_crf: 18
advanced_preset: slow
advanced_pix_fmt: yuv420p  # 保持兼容性
```

**适用**: 珍贵视频保存,原始素材备份

---

##### 场景3: 专业后期制作 (仅Windows/Linux)

```yaml
format: video/h264-high444
# 或使用高级模式:
format: video/h264-advanced
advanced_pix_fmt: yuv444p  # 最高色彩保真度
advanced_crf: 16
advanced_preset: slow
```

**注意**:
- ⚠️ 生成的视频Mac无法播放
- 适合作为后期制作的中间格式
- 最终发布前需转换为yuv420p

---

##### 场景4: 绿幕抠像视频

```yaml
format: video/h264-advanced
advanced_pix_fmt: yuv444p  # 色度边缘更锐利
advanced_tune: film
advanced_crf: 16
```

**适用**: 绿幕/蓝幕特效制作,色键抠像

---

#### 🔍 YUV420p vs YUV444p 对比

| 特性 | YUV420p (推荐) | YUV444p (专业) |
|------|---------------|---------------|
| **Mac兼容性** | ✅ 完美支持 | ❌ 不支持 |
| **iOS兼容性** | ✅ 完美支持 | ❌ 不支持 |
| **文件大小** | 📉 小 | 📈 大50% |
| **色彩精度** | ⭐⭐⭐⭐ (95%) | ⭐⭐⭐⭐⭐ (100%) |
| **适用场景** | 日常使用 | 专业后期 |

**详细说明**: 查看 `VIDEO_FORMATS_GUIDE.md`

---

#### 💡 最佳实践建议

1. **默认配置**: 90%的情况使用 `video/h264-mp4` 即可
2. **质量优先**: 如需更高质量,调整 `quality` 参数到 95
3. **Mac兼容**: 永远选择 `yuv420p` 像素格式
4. **专业制作**: 仅在Windows/Linux上使用 `yuv444p`
5. **发布前转换**: yuv444p视频发布前转换为yuv420p

---

#### ⚠️ 常见问题

**Q: 视频在Mac上显示黑屏?**
A: 使用了yuv444p格式。解决:选择 `video/h264-mp4` 重新生成

**Q: 如何获得最佳质量且Mac兼容?**
A: 使用 `video/h264-advanced` + `yuv420p` + `crf=18` + `preset=slow`

**Q: 专业后期用什么格式?**
A: 使用 `video/h264-high444` 或 `advanced_pix_fmt=yuv444p`

---

### 其他功能

#### 加密功能

- `encrypt`: 启用后,输出文件将被XOR加密
- 加密文件无法直接播放或查看
- 使用相同密钥可解密

#### 音频混流

- 连接 `audio` 输入可自动将音频混流到视频中
- 支持MP4, WebM, AVI格式
- 自动选择合适的音频编解码器

#### VAE解码

- 连接 `vae` 输入可自动解码latent图像
- 适用于Stable Diffusion等生成式模型的输出

---

## 📖 更多文档

- **VIDEO_FORMATS_GUIDE.md**: YUV格式详细解释和使用指南
- **comfyui-h264-high444/**: 独立的H.264 High 4:4:4编码节点

---

### Convert Widgets to ShellAgent Inputs

A widget can be easily converted into a ShellAgent Input node of the appropriate type by right-clicking on the widget and selecting the option from the menu.
