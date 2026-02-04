# ComfyUI Custom Node — H.264 High 4:4:4 Predictive Encoder (libx264)

This node encodes a ComfyUI `IMAGE` batch into **H.264 High 4:4:4 Predictive** using FFmpeg + libx264.

It **forces**:
- `-profile:v high444`
- `-pix_fmt yuv444p` (or `yuv444p10le`)

And writes explicit color metadata to reduce colorspace/range surprises.

## Install
1) Copy this folder into:
`ComfyUI/custom_nodes/comfyui-h264-high444/`

2) Restart ComfyUI.

## Node
**Video Encode (H.264 High444 4:4:4)**

### Key parameters
- `pix_fmt`: `yuv444p` (8-bit) or `yuv444p10le` (10-bit)
- `colorspace`: `bt709` (default), `bt601`, `bt2020nc`
- `color_range`: `pc` (full) or `tv` (limited)
- `tune`: optional x264 tune (animation/film/grain/...)
- `x264_params`: raw `-x264-params` string (advanced)
- `video_bitrate_kbps`: optional bitrate cap (0 disables)
- `ffmpeg_path`: leave blank to auto-find, or set full path
- `verify_with_ffprobe`: best-effort verification if ffprobe is available

## Verify output manually
```bash
ffprobe -v error -select_streams v:0 \
-show_entries stream=codec_name,profile,pix_fmt \
-of default=nk=1:nw=1 output/high444.mp4
```

You should see:
- `High 4:4:4 Predictive`
- `yuv444p` (or `yuv444p10le`)
