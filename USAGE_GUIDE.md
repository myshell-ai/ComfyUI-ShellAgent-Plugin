# 📖 Video Combine Encrypt 节点使用指南

## 🎯 快速开始 (30秒上手)

### 最简单的方式

1. 在ComfyUI中添加 **Video Combine Encrypt** 节点
2. 连接图像序列到 `images` 输入
3. 设置 `format` 为 **`video/h264-mp4`**
4. 点击 Queue Prompt

**结果**: 生成Mac兼容的高质量MP4视频 ✅

---

## 📋 节点参数说明

### 基础参数 (所有格式)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `images` | IMAGE | - | 图像序列输入 |
| `frame_rate` | FLOAT | 24 | 帧率 (fps) |
| `loop_count` | INT | 0 | 循环次数 (0=无限,仅GIF/WebP) |
| `filename_prefix` | STRING | ShellAgent_Encrypted | 输出文件名前缀 |
| `format` | DROPDOWN | - | 视频格式选择 ⭐ |
| `quality` | INT | 85 | 质量 (1-100,仅标准格式) |
| `pingpong` | BOOLEAN | False | 反转循环 |
| `encrypt` | BOOLEAN | True | 是否加密输出 |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `audio` | AUDIO | - | 音频输入 (自动混流) |
| `vae` | VAE | - | VAE解码器 (处理latent) |

---

## 🎬 格式选择详解

### 标准格式 (推荐日常使用)

#### 1. `video/h264-mp4` ⭐ 推荐

**特点**:
- ✅ Mac/iOS/Android全兼容
- ✅ 质量优秀
- ✅ 文件大小适中
- ✅ 所有播放器支持

**适用场景**:
- 日常视频制作
- 社交媒体发布
- 网页嵌入
- 分享给他人

**配置示例**:
```
format: video/h264-mp4
quality: 85
```

---

#### 2. `video/h265-mp4`

**特点**:
- ✅ 更好的压缩率 (文件小30-50%)
- ✅ Mac/iOS支持
- ⚠️ 部分老设备可能不支持

**适用场景**:
- 4K视频
- 需要节省空间
- 现代设备播放

**配置示例**:
```
format: video/h265-mp4
quality: 85
```

---

#### 3. `video/vp9-webm`

**特点**:
- ✅ 开源格式
- ✅ 网页友好
- ✅ Chrome/Firefox完美支持

**适用场景**:
- 网页嵌入
- 开源项目
- 流媒体

**配置示例**:
```
format: video/vp9-webm
quality: 85
```

---

#### 4. `video/mov`

**特点**:
- ✅ Mac原生格式
- ✅ QuickTime完美支持
- ✅ iMovie/Final Cut Pro兼容

**适用场景**:
- Mac用户专用
- 后期编辑素材
- QuickTime播放

**配置示例**:
```
format: video/mov
quality: 85
```

---

### 高级格式 (专业用户)

#### 5. `video/h264-advanced` ⚙️

**特点**:
- 可自定义所有编码参数
- 灵活性最高
- 需要了解编码知识

**适用场景**:
- 需要精确控制质量
- 特殊编码需求
- 专业视频制作

**必需的高级参数**:
```
format: video/h264-advanced

# 必须设置以下参数:
advanced_preset: medium     # 编码速度
advanced_crf: 20            # 质量控制
advanced_pix_fmt: yuv420p   # ⚠️ Mac兼容必须用yuv420p
```

**完整配置示例**:
```
format: video/h264-advanced
advanced_preset: slow       # 更好的质量
advanced_crf: 18            # 更高的质量
advanced_pix_fmt: yuv420p   # Mac兼容
advanced_tune: film         # 电影优化
advanced_colorspace: bt709  # HD色彩空间
advanced_color_range: pc    # 全范围色彩
```

---

#### 6. `video/h264-high444` 🎥

**特点**:
- ❌ **Mac/iOS不兼容**
- ✅ 最高色彩保真度 (yuv444p)
- ✅ 专业后期制作标准
- 📈 文件大50%

**适用场景**:
- 专业后期制作
- 绿幕抠像
- 色彩调色
- 仅Windows/Linux播放

**配置示例**:
```
format: video/h264-high444
# 自动使用 yuv444p + High444 profile
```

**⚠️ 重要提醒**:
- 生成的视频Mac无法播放
- 适合作为中间格式
- 最终发布前需转换为yuv420p

---

#### 7. `video/ffmpeg-manual` 🔧

**特点**:
- 完全手动控制
- 可以使用任何编解码器
- 需要深入的ffmpeg知识

**适用场景**:
- 专家级自定义
- 特殊编解码器需求
- 实验性配置

**必需的手动参数**:
```
format: video/ffmpeg-manual

# 必须设置:
manual_videocodec: libx264      # 视频编解码器
advanced_preset: medium
advanced_crf: 20
advanced_pix_fmt: yuv420p       # 像素格式
```

---

## ⚙️ 高级参数详解

### 编码速度 (advanced_preset)

| 值 | 编码速度 | 质量 | 文件大小 | 适用场景 |
|----|---------|------|---------|---------|
| `ultrafast` | 极快 ⚡ | 差 | 大 | 实时直播 |
| `superfast` | 很快 | 一般 | 较大 | 快速预览 |
| `veryfast` | 快 | 尚可 | 中等 | 快速制作 |
| `fast` | 较快 | 好 | 适中 | 日常快速 |
| **`medium`** ⭐ | **适中** | **优秀** | **适中** | **推荐日常** |
| **`slow`** ⭐ | **慢** | **极佳** | **小** | **推荐存档** |
| `slower` | 很慢 | 最佳 | 很小 | 高质量 |
| `veryslow` | 极慢 🐢 | 顶级 | 最小 | 电影制作 |

**建议**:
- 日常使用: `medium`
- 高质量存档: `slow`
- 快速预览: `fast`

---

### 质量控制 (advanced_crf)

CRF (Constant Rate Factor) - 数值越小质量越高

| CRF范围 | 质量 | 文件大小 | 适用场景 |
|---------|------|---------|---------|
| 0-17 | 视觉无损 | 巨大 | 专业存档 |
| **18-20** ⭐ | **极高质量** | **大** | **推荐存档** |
| **21-23** ⭐ | **高质量** | **适中** | **推荐日常** |
| 24-28 | 好质量 | 小 | 网络流畅 |
| 29+ | 可接受 | 很小 | 低质量需求 |

**建议**:
- 日常使用: `20-23`
- 高质量存档: `18-20`
- 网络流媒体: `23-25`

---

### 像素格式 (advanced_pix_fmt)

| 格式 | Mac兼容 | 色彩精度 | 文件大小 | 适用场景 |
|------|---------|---------|---------|---------|
| **`yuv420p`** ⭐ | ✅ **完美** | ⭐⭐⭐⭐ 95% | 标准 | **日常使用** |
| `yuv444p` | ❌ **不兼容** | ⭐⭐⭐⭐⭐ 100% | +50% | 专业后期 |
| `yuv444p10le` | ❌ 不兼容 | ⭐⭐⭐⭐⭐ 10位 | +60% | 高端制作 |

**⚠️ 重要**:
- 需要Mac兼容: 必须选择 `yuv420p`
- 专业后期(仅Windows/Linux): 可选 `yuv444p`
- 发布前转换: `yuv444p` → `yuv420p`

---

### 优化类型 (advanced_tune)

| 值 | 说明 | 适用场景 |
|----|------|---------|
| `none` | 通用优化 (默认) | 大多数场景 |
| `film` | 电影内容优化 | 真人视频 |
| `animation` | 动画优化 | 卡通/动画 |
| `grain` | 保留胶片颗粒 | 复古风格 |
| `stillimage` | 静态图片序列 | 幻灯片 |
| `fastdecode` | 快速解码 | 低端设备 |
| `zerolatency` | 零延迟 | 直播/实时 |

---

### 色彩空间 (advanced_colorspace)

| 值 | 说明 | 适用场景 |
|----|------|---------|
| **`bt709`** ⭐ | **HD标准 (推荐)** | **1080p及以上** |
| `bt601` | SD标准 | 480p/576p |
| `bt2020nc` | UHD标准 | 4K/8K HDR |

---

### 色彩范围 (advanced_color_range)

| 值 | 范围 | 说明 | 适用场景 |
|----|------|------|---------|
| **`pc`** ⭐ | **0-255 (全范围)** | **推荐** | **电脑播放** |
| `tv` | 16-235 (有限) | 传统 | 电视播放 |

---

## 🎓 使用场景示例

### 场景1: 发布到YouTube

**目标**: 高质量,Mac兼容,文件适中

```yaml
format: video/h264-mp4
quality: 85
frame_rate: 30 (或 60)
```

**结果**: 适合上传,兼容性好,质量优秀

---

### 场景2: 分享给Mac用户

**目标**: 确保在Mac上完美播放

```yaml
# 方案A: 使用H.264
format: video/h264-mp4
quality: 90

# 方案B: 使用QuickTime原生格式
format: video/mov
quality: 90
```

**结果**: QuickTime完美播放

---

### 场景3: 高质量视频存档

**目标**: 最高质量,仍然Mac兼容

```yaml
format: video/h264-advanced
advanced_preset: slow
advanced_crf: 18
advanced_pix_fmt: yuv420p  # ⚠️ 保持兼容性
advanced_colorspace: bt709
```

**结果**: 接近无损,文件较大,Mac兼容

---

### 场景4: 专业后期制作素材

**目标**: 最高色彩保真度,仅Windows使用

```yaml
format: video/h264-high444
# 自动使用 yuv444p

# 或使用高级模式:
format: video/h264-advanced
advanced_pix_fmt: yuv444p
advanced_crf: 16
advanced_preset: slow
advanced_tune: film
```

**注意**: ⚠️ Mac不能播放,用作中间格式

---

### 场景5: 绿幕抠像视频

**目标**: 色度边缘锐利,便于抠像

```yaml
format: video/h264-advanced
advanced_pix_fmt: yuv444p  # 完整色度信息
advanced_crf: 16
advanced_tune: film
```

**工作流程**:
1. 用yuv444p生成高质量素材
2. 在专业软件中抠像
3. 导出时转换为yuv420p发布

---

### 场景6: 网络流媒体

**目标**: 流畅播放,文件小

```yaml
format: video/h264-mp4
quality: 75
# 或
format: video/h264-advanced
advanced_crf: 25
advanced_preset: fast
```

**结果**: 快速加载,流畅播放

---

### 场景7: 4K高分辨率视频

**目标**: 保持质量,文件不要太大

```yaml
format: video/h265-mp4  # 更好的压缩
quality: 85
# 或
format: video/h264-advanced
advanced_preset: slow
advanced_crf: 20
```

**结果**: 文件大小可控,质量优秀

---

## 🔧 故障排查

### 问题1: Mac上视频显示黑屏

**原因**: 使用了yuv444p格式

**解决**:
1. 重新生成,选择 `video/h264-mp4`
2. 或在高级模式中设置 `advanced_pix_fmt: yuv420p`

---

### 问题2: 文件太大

**解决方案**:

**方案1**: 降低quality参数
```yaml
quality: 70-80  # 从85降低
```

**方案2**: 使用H.265
```yaml
format: video/h265-mp4
```

**方案3**: 提高CRF (降低质量)
```yaml
advanced_crf: 23-25  # 从20提高
```

---

### 问题3: 编码太慢

**解决方案**:

**方案1**: 使用更快的preset
```yaml
advanced_preset: fast  # 从medium改为fast
```

**方案2**: 在生成图像时降低分辨率

---

### 问题4: 颜色看起来不对

**解决方案**:

**方案1**: 调整色彩空间
```yaml
advanced_colorspace: bt709  # HD视频
```

**方案2**: 调整色彩范围
```yaml
advanced_color_range: pc  # 全范围 0-255
```

---

## 🔍 验证视频格式

### 使用ffprobe检查

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,pix_fmt,profile \
  -of default=nw=1 video.mp4
```

### Mac兼容的输出应该是:

```
h264
yuv420p
High
```

### 如果是High444 (Mac不兼容):

```
h264
yuv444p
High 4:4:4 Predictive
```

---

## 💡 最佳实践

### DO's (推荐做法)

✅ 默认使用 `video/h264-mp4`
✅ Mac兼容必须使用 `yuv420p`
✅ 日常使用 quality 85 或 CRF 20-23
✅ 高质量存档使用 CRF 18-20
✅ 专业后期可以用 yuv444p,但最终发布前转换
✅ 阅读文档了解每个参数的含义

### DON'Ts (避免做法)

❌ 不要盲目追求最低CRF (文件会非常大)
❌ 不要用yuv444p格式分享给Mac用户
❌ 不要过度使用veryslow preset (时间成本高)
❌ 不要忽略兼容性标注
❌ 不要在不理解的情况下修改x264-params

---

## 📚 相关文档

- **VIDEO_FORMATS_GUIDE.md**: YUV格式完整教程
- **QUICK_REFERENCE.md**: 快速参考卡片
- **README.md**: 项目总览
- **INTEGRATION_SUMMARY.md**: 集成完成总结

---

## 🎉 总结

### 记住这3点

1. **默认选择**: `video/h264-mp4` + `quality: 85`
2. **Mac兼容**: 必须用 `yuv420p`
3. **专业用途**: yuv444p仅用于后期,最终要转换

### 一句话建议

```
如果不确定,永远选择 video/h264-mp4
这是质量、兼容性和文件大小的最佳平衡!
```

---

**祝你创作顺利!** 🎬✨
