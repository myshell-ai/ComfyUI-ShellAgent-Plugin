#!/usr/bin/env python3
"""
视频格式集成验证脚本

用途:
1. 验证output_video_encrypt.py的语法正确性
2. 检查VIDEO_FORMATS字典的完整性
3. 验证新增格式的配置
4. 生成格式配置报告
"""

import sys
import os

def check_file_exists():
    """检查文件是否存在"""
    file_path = "comfy-nodes/output_video_encrypt.py"
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    print(f"✅ 文件存在: {file_path}")
    return True

def check_syntax():
    """检查Python语法"""
    import py_compile
    try:
        py_compile.compile("comfy-nodes/output_video_encrypt.py", doraise=True)
        print("✅ Python语法检查通过")
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ 语法错误: {e}")
        return False

def check_video_formats():
    """检查VIDEO_FORMATS字典"""
    # 临时导入模块
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        # 动态导入
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "output_video_encrypt",
            "comfy-nodes/output_video_encrypt.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        VIDEO_FORMATS = module.VIDEO_FORMATS

        print(f"\n✅ VIDEO_FORMATS加载成功,共 {len(VIDEO_FORMATS)} 个格式:\n")

        # 预期的格式
        expected_formats = [
            "h264-mp4",
            "h265-mp4",
            "vp9-webm",
            "avi",
            "mov",
            "h264-advanced",
            "h264-high444",
            "ffmpeg-manual"
        ]

        # 检查每个格式
        for fmt_name in expected_formats:
            if fmt_name in VIDEO_FORMATS:
                fmt_config = VIDEO_FORMATS[fmt_name]
                compat = fmt_config.get("compatible", "unknown")
                desc = fmt_config.get("description", "无描述")

                compat_icon = {
                    True: "✅",
                    False: "❌",
                    "depends": "⚠️",
                    "unknown": "❓"
                }.get(compat, "❓")

                print(f"  {compat_icon} {fmt_name}: {desc}")

                # 检查关键字段
                required_fields = ["extension", "main_pass", "dim_alignment"]
                missing = [f for f in required_fields if f not in fmt_config]
                if missing:
                    print(f"    ⚠️  缺少字段: {', '.join(missing)}")
            else:
                print(f"  ❌ 缺少格式: {fmt_name}")

        return True

    except Exception as e:
        print(f"❌ 加载VIDEO_FORMATS失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_advanced_parameters():
    """检查高级参数"""
    print("\n检查高级参数定义:")

    expected_params = [
        "advanced_preset",
        "advanced_tune",
        "advanced_crf",
        "advanced_pix_fmt",
        "advanced_colorspace",
        "advanced_color_range",
        "advanced_x264_params",
        "manual_videocodec",
        "manual_audio_codec"
    ]

    # 读取文件内容检查
    with open("comfy-nodes/output_video_encrypt.py", 'r', encoding='utf-8') as f:
        content = f.read()

    found_params = []
    missing_params = []

    for param in expected_params:
        if f'"{param}"' in content or f"'{param}'" in content:
            found_params.append(param)
            print(f"  ✅ {param}")
        else:
            missing_params.append(param)
            print(f"  ❌ {param} (未找到)")

    if missing_params:
        print(f"\n⚠️  缺少参数: {', '.join(missing_params)}")
        return False
    else:
        print(f"\n✅ 所有 {len(expected_params)} 个高级参数都已定义")
        return True

def generate_format_report():
    """生成格式配置报告"""
    print("\n" + "="*60)
    print("视频格式配置报告")
    print("="*60)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "output_video_encrypt",
            "comfy-nodes/output_video_encrypt.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        VIDEO_FORMATS = module.VIDEO_FORMATS

        # 按兼容性分类
        compatible = []
        incompatible = []
        depends = []

        for fmt_name, fmt_config in VIDEO_FORMATS.items():
            compat = fmt_config.get("compatible", "unknown")
            if compat is True:
                compatible.append(fmt_name)
            elif compat is False:
                incompatible.append(fmt_name)
            else:
                depends.append(fmt_name)

        print(f"\n📊 格式统计:")
        print(f"  总计: {len(VIDEO_FORMATS)} 个格式")
        print(f"  Mac兼容: {len(compatible)} 个")
        print(f"  Mac不兼容: {len(incompatible)} 个")
        print(f"  取决于配置: {len(depends)} 个")

        print(f"\n✅ Mac兼容格式 ({len(compatible)}个):")
        for fmt in compatible:
            desc = VIDEO_FORMATS[fmt].get("description", "")
            print(f"  • {fmt}: {desc}")

        print(f"\n❌ Mac不兼容格式 ({len(incompatible)}个):")
        for fmt in incompatible:
            desc = VIDEO_FORMATS[fmt].get("description", "")
            print(f"  • {fmt}: {desc}")

        print(f"\n⚠️  配置依赖格式 ({len(depends)}个):")
        for fmt in depends:
            desc = VIDEO_FORMATS[fmt].get("description", "")
            print(f"  • {fmt}: {desc}")

        # 检查yuv420p和yuv444p的使用
        print(f"\n🎨 像素格式分析:")
        yuv420_count = 0
        yuv444_count = 0

        for fmt_name, fmt_config in VIDEO_FORMATS.items():
            main_pass = fmt_config.get("main_pass", [])
            if "-pix_fmt" in main_pass:
                idx = main_pass.index("-pix_fmt")
                if idx + 1 < len(main_pass):
                    pix_fmt = main_pass[idx + 1]
                    if "420" in pix_fmt:
                        yuv420_count += 1
                    elif "444" in pix_fmt:
                        yuv444_count += 1

        print(f"  yuv420p格式: {yuv420_count} 个")
        print(f"  yuv444p格式: {yuv444_count} 个")
        print(f"  可配置格式: {len(depends)} 个")

        print("\n" + "="*60)

        return True

    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        return False

def main():
    """主函数"""
    print("🔍 开始验证视频格式集成...\n")

    results = []

    # 1. 检查文件存在
    results.append(("文件存在", check_file_exists()))

    # 2. 检查语法
    results.append(("Python语法", check_syntax()))

    # 3. 检查VIDEO_FORMATS
    results.append(("VIDEO_FORMATS", check_video_formats()))

    # 4. 检查高级参数
    results.append(("高级参数", check_advanced_parameters()))

    # 5. 生成报告
    results.append(("格式报告", generate_format_report()))

    # 总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"  {icon} {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有检查通过!集成成功!")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个检查失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
