"""
NTSilk - 媒体文件转 Silk 格式。
优先使用原生二进制（lib/NTSilk），无匹配平台时 fallback 到 pilk。
"""
import os
import subprocess
import sys

from src.core.constants import Constants

_lib_path = Constants.modules_conf.get_lib_path("NTSilk")


def _get_ntsilk_binary() -> str | None:
    """获取当前平台对应的 NTSilk 二进制路径，无匹配则返回 None。"""

    if sys.platform == "win32":
        binary_name = "ntsilk-win32-x64.exe"
    elif sys.platform == "linux":
        binary_name = "ntsilk-linux-x64"
    else:
        return None

    binary_path = os.path.join(_lib_path, binary_name)
    if os.path.isfile(binary_path):
        return binary_path
    return None


def convert_to_silk(media_path: str, output_path: str | None = None) -> str:
    """
    将任意媒体文件转换为 Silk 格式。
    优先使用 NTSilk 原生二进制，无匹配平台时 fallback 到 pilk。

    Args:
        media_path: 输入媒体文件路径
        output_path: 输出 silk 文件路径，不指定则自动替换扩展名为 .silk

    Returns:
        输出 silk 文件路径
    """
    if output_path is None:
        output_path = os.path.splitext(media_path)[0] + '.ntsilk'

    binary = _get_ntsilk_binary()
    if binary is not None:
        Constants.log.debug(f"[ntsilk] 使用 ntsilk 转换: {binary}")
        try:
            subprocess.run(
                [binary, "-i", media_path, output_path],
                check=True,
                capture_output=True,
                text=True,
            )
            Constants.log.debug(f"[ntsilk] 转换完成: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            Constants.log.warning(f"[ntsilk] ntsilk 转换失败，fallback 到 pilk: {e.stderr.strip()}")
        except Exception as e:
            Constants.log.warning(f"[ntsilk] ntsilk 调用异常，fallback 到 pilk: {e}")

    # Fallback: 使用 pilk 转换
    Constants.log.debug(f"[ntsilk] 使用 pilk fallback 转换: {media_path}")
    return _fallback_pilk(media_path, output_path)


def _fallback_pilk(media_path: str, output_path: str) -> str:
    """使用 av + pilk 的 fallback 转换方案"""
    import av
    import pilk

    # 第一步：媒体文件 → PCM
    pcm_path = os.path.splitext(media_path)[0] + '.pcm'
    try:
        with av.open(media_path) as in_container:
            in_stream = in_container.streams.audio[0]
            sample_rate = in_stream.codec_context.sample_rate
            with av.open(pcm_path, 'w', 's16le') as out_container:
                out_stream = out_container.add_stream(
                    'pcm_s16le',
                    rate=sample_rate,
                    layout='mono',
                )
                for frame in in_container.decode(in_stream):
                    frame.pts = None
                    for packet in out_stream.encode(frame):
                        out_container.mux(packet)
    except Exception as e:
        Constants.log.warning("[ntsilk] fallback PCM 转换失败")
        Constants.log.exception(e)
        return output_path

    # 第二步：PCM → Silk
    pilk.encode(pcm_path, output_path, pcm_rate=sample_rate, tencent=True)
    os.remove(pcm_path)

    Constants.log.debug(f"[ntsilk] pilk fallback 转换完成: {output_path}")
    return output_path
