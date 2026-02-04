# 🎬 视频格式快速参考卡片

## 1️⃣ 我应该选择哪个格式?

```
┌─────────────────────────────────────────────────┐
│  需要在Mac/iPhone上播放?                        │
│  需要分享给他人?                                │
│  发布到社交媒体?                                │
│  ├─ 是 → 选择 video/h264-mp4✅                 │
│  └─ 否 → 继续下一步                            │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  需要最高色彩保真度?                            │
│  进行专业后期制作?                              │
│  制作绿幕特效?                                  │
│  ├─ 是 → 选择 video/h264-high444 ⚠️            │
│  │       (Mac不兼容,仅Windows/Linux)           │
│  └─ 否 → 选择 video/h264-mp4 ✅                │
└─────────────────────────────────────────────────┘
```

---

## 2️⃣ 格式速查表

| 我想... | 选择这个格式 | Mac兼容 |
|---------|-------------|---------|
| 日常使用,发社交媒体 | `video/h264-mp4` ✅ | ✅ 完美 |
| 节省空间,4K视频 | `video/h265-mp4` | ✅ 支持 |
| 网页嵌入播放 | `video/vp9-webm` | ✅ 支持 |
| Mac原生格式 | `video/mov` | ✅ 完美 |
| 自定义编码参数 | `video/h264-advanced` ⚙️ | ⚠️ 看配置 |
| 专业后期,最高质量 | `video/h264-high444` 🎥 | ❌ 不兼容 |
| 完全手动控制 | `video/ffmpeg-manual` 🔧 | ⚠️ 看配置 |

---

## 3️⃣ 质量参数速查

### 简单模式 (quality参数)

```
quality: 95-100  → 接近无损,文件很大
quality: 85-90   → 高质量,推荐日常使用 ✅
quality: 70-80   → 好质量,文件适中
quality: 50-60   → 可接受,文件较小
quality: <50     → 质量明显下降
```

### 高级模式 (CRF参数)

```
CRF 0-17   → 视觉无损,文件巨大
CRF 18-20  → 极高质量,推荐存档 ✅
CRF 21-23  → 高质量,推荐日常 ✅
CRF 24-28  → 好质量,文件适中
CRF 29+    → 质量下降
```

---

## 4️⃣ 像素格式选择

```
┌──────────────────────────────────────────┐
│  yuv420p                                 │
│  ✅ Mac/iOS/Android全兼容                │
│  ✅ 所有播放器支持                        │
│  ✅ 文件大小小                           │
│  ⭐⭐⭐⭐ 95%色彩精度                     │
│  → 日常使用推荐                          │
└──────────────────────────────────────────┘
┌──────────────────────────────────────────┐
│  yuv444p                                 │
│  ❌ Mac/iOS不兼容                        │
│  ⚠️ 部分Android设备支持                  │
│  ✅ Windows/Linux支持                    │
│  📈 文件大50%                            │
│  ⭐⭐⭐⭐⭐ 100%色彩精度                  │
│  → 专业后期推荐                          │
└──────────────────────────────────────────┘
```

---

## 5️⃣ 常见场景配置

### 🎯 场景: 发布到YouTube/Bilibili

```yaml
format: video/h264-mp4
quality: 85
frame_rate: 30 或 60
```

**为什么?**
- H.264最广泛支持
- yuv420p确保兼容性
- quality 85平衡质量和文件大小

---

### 🎯 场景: 分享给Mac用户

```yaml
format: video/h264-mp4
quality: 85-90
```

**或使用QuickTime原生格式:**

```yaml
format: video/mov
quality: 85-90
```

**为什么?**
- 确保Mac/iPhone完美播放
- MOV是Mac原生格式

---

### 🎯 场景: 高质量视频存档

```yaml
format: video/h264-advanced
advanced_crf: 18
advanced_preset: slow
advanced_pix_fmt: yuv420p  # 保持兼容性!
```

**为什么?**
- CRF 18接近无损
- preset=slow获得最佳压缩
- 仍然使用yuv420p保证兼容

---

### 🎯 场景: 专业后期制作素材

```yaml
format: video/h264-high444
# 或
format: video/h264-advanced
advanced_pix_fmt: yuv444p
advanced_crf: 16
advanced_preset: slow
```

**注意:**
- ⚠️ Mac不能播放
- 仅用作中间格式
- 最终导出前转换为yuv420p

---

### 🎯 场景: 绿幕抠像视频

```yaml
format: video/h264-advanced
advanced_pix_fmt: yuv444p  # 色度边缘更锐利
advanced_tune: film
advanced_crf: 16
```

**为什么?**
- yuv444p保留完整色度信息
- 色键抠像更精确
- tune=film优化电影感

---

## 6️⃣ Preset参数说明

```
ultrafast  →  极快,质量差      (实时直播)
superfast  →  很快,质量一般
veryfast   →  快,质量尚可
faster     →  较快,质量好
fast       →  快,质量很好
medium     →  适中,质量优秀    ← 推荐日常 ✅
slow       →  慢,质量极佳      ← 推荐存档 ✅
slower     →  很慢,质量最佳
veryslow   →  极慢,质量顶级    (电影制作)
```

---

## 7️⃣ Tune参数说明

```
none         →  通用优化 (默认)
film         →  电影内容
animation    →  动画内容
grain        →  保留胶片颗粒
stillimage   →  静态图片序列
fastdecode   →  快速解码
zerolatency  →  低延迟 (直播)
```

---

## 8️⃣ 故障排查

### ❌ 问题: Mac上视频显示黑屏

**原因**: 使用了yuv444p格式

**解决**:
1. 重新生成,选择 `video/h264-mp4`
2. 或转换现有视频:
   ```bash
   ffmpeg -i input.mp4 -c:v libx264 -pix_fmt yuv420p output.mp4
   ```

---

### ❌ 问题: 文件太大

**解决方案**:

**方案1: 调整quality参数**
```yaml
quality: 70-80  # 从85降低
```

**方案2: 使用H.265压缩**
```yaml
format: video/h265-mp4
```

**方案3: 调整CRF (高级模式)**
```yaml
advanced_crf: 23-25  # 从18-20提高
```

---

### ❌ 问题: 编码太慢

**解决方案**:

**方案1: 使用更快的preset**
```yaml
advanced_preset: fast 或 veryfast
```

**方案2: 降低分辨率**
- 在生成图像时就使用更小的分辨率

---

### ❌ 问题: 颜色看起来不对

**解决方案**:

**方案1: 调整色彩空间**
```yaml
advanced_colorspace: bt709  # HD视频
advanced_colorspace: bt601  # SD视频
```

**方案2: 调整色彩范围**
```yaml
advanced_color_range: pc   # 0-255全范围
advanced_color_range: tv   # 16-235有限范围
```

---

## 9️⃣ 命令行验证视频格式

```bash
# 检查视频编码信息
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,pix_fmt,profile \
  -of default=nw=1 video.mp4

# 期望输出 (Mac兼容):
h264
yuv420p
High

# 如果输出yuv444p,说明Mac不兼容!
```

---

## 🔟 一句话总结

```
┌────────────────────────────────────────────────────┐
│                                                    │
│   如果不确定,永远选择:                             │
│                                                    │
│   format: video/h264-mp4                           │
│   quality: 85                                      │
│                                                    │
│   这是质量、兼容性和文件大小的最佳平衡!             │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 📚 更多详细信息

- **VIDEO_FORMATS_GUIDE.md**: 完整的YUV格式教程
- **README.md**: 所有功能的详细说明
- **High444编码节点**: 查看 `comfyui-h264-high444/`

---

**最后提醒**:

🎯 **Mac/iOS用户**: 必须使用 `yuv420p`
🎥 **专业用户**: 可以用 `yuv444p`,但发布前要转换
💡 **不确定**: 就用默认的 `video/h264-mp4`
